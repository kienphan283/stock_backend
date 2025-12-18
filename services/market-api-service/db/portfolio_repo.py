from datetime import datetime
from typing import List, Optional, Dict
from psycopg2.extras import RealDictCursor
from .base_repo import BaseRepository
import uuid
import logging

logger = logging.getLogger(__name__)

class PortfolioRepo(BaseRepository):
    # --- Portfolios ---
    def get_user_portfolios(self, user_id: str) -> List[Dict]:
        query = """
            SELECT portfolio_id, name, currency, created_at
            FROM portfolio_oltp.portfolios
            WHERE user_id = %s
            ORDER BY created_at DESC
        """
        return self.fetch_all(query, (user_id,))

    def create_portfolio(self, user_id: str, name: str, currency: str = 'USD', 
                        goal_type: str = 'VALUE', target_amount: float = None, note: str = None) -> str:
        portfolio_id = str(uuid.uuid4())
        query = """
            INSERT INTO portfolio_oltp.portfolios (portfolio_id, user_id, name, currency, goal_type, target_amount, note)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            RETURNING portfolio_id
        """
        self.execute_query(query, (portfolio_id, user_id, name, currency, goal_type, target_amount, note))
        return portfolio_id

    # --- Transactions ---
    def add_transaction(self, portfolio_id: str, ticker: str, 
                       transaction_type: str, quantity: float, price: float,
                       fee: float = 0, tax: float = 0, 
                       transaction_date: datetime = None, note: str = None) -> str:
        transaction_id = str(uuid.uuid4())
        if transaction_date is None:
            transaction_date = datetime.now()
            
        insert_query = """
            INSERT INTO portfolio_oltp.portfolio_transactions 
            (transaction_id, portfolio_id, stock_ticker, transaction_type, quantity, price, fee, tax, transaction_date, note)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING transaction_id
        """
        
        conn = self.get_connection()
        try:
            # Use RealDictCursor to ensure consistency with remainder of the code
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                # 1. Insert Transaction
                cur.execute(insert_query, (
                    transaction_id, portfolio_id, ticker, transaction_type, 
                    quantity, price, fee, tax, transaction_date, note
                ))
                
                # 2. Update Holdings Cache (Pass cursor to reuse transaction)
                self._update_holding_cache(portfolio_id, ticker, cur)
                
            conn.commit()
        except Exception as e:
            conn.rollback()
            logger.error(f"Error adding transaction (atomic rollback): {e}")
            raise e
        finally:
            conn.close()
            
        return transaction_id

    def get_transactions(self, portfolio_id: str, ticker: str = None) -> List[Dict]:
        query = """
            SELECT transaction_id, stock_ticker, transaction_type, quantity, price, fee, tax, transaction_date, note
            FROM portfolio_oltp.portfolio_transactions
            WHERE portfolio_id = %s
        """
        params = [portfolio_id]
        if ticker:
            query += " AND stock_ticker = %s"
            params.append(ticker)
            
        query += " ORDER BY transaction_date DESC"
        return self.fetch_all(query, tuple(params))

    # --- Holdings ---
    def get_holdings(self, portfolio_id: str, include_sold: bool = False) -> List[Dict]:
        query = """
            SELECT holding_id, stock_ticker, total_shares, avg_cost_basis, first_buy_date
            FROM portfolio_oltp.portfolio_holdings
            WHERE portfolio_id = %s
        """
        if not include_sold:
            query += " AND total_shares > 0"
            
        query += " ORDER BY stock_ticker"
        return self.fetch_all(query, (portfolio_id,))

    def _update_holding_cache(self, portfolio_id: str, ticker: str, cur=None):
        """
        Recalculate and update the cached holding state for a specific stock
        based on transaction history (Single Average Cost Method).
        Accepts an optional cursor to run within an existing transaction.
        """
        # Fetch all transactions for this stock in chronological order
        query = """
            SELECT transaction_type, quantity, price, fee, transaction_date
            FROM portfolio_oltp.portfolio_transactions
            WHERE portfolio_id = %s AND stock_ticker = %s
            ORDER BY transaction_date ASC
        """
        
        txs = []
        if cur:
            # Included in external transaction
            cur.execute(query, (portfolio_id, ticker))
            txs = cur.fetchall()
        else:
             # Standalone mode
             txs = self.fetch_all(query, (portfolio_id, ticker))
        
        total_shares = 0.0
        total_cost = 0.0
        first_buy_date = None
        
        for tx in txs:
            t_type = tx['transaction_type']
            qty = float(tx['quantity'])
            price = float(tx['price'])
            
            if t_type == 'BUY':
                if total_shares == 0:
                    first_buy_date = tx['transaction_date']
                total_cost += (qty * price) # Standard calculation: add to total cost
                total_shares += qty
            elif t_type == 'SELL':
                if total_shares > 0:
                    # Reduce cost proportionally
                    avg_cost = total_cost / total_shares
                    total_cost -= (qty * avg_cost)
                    total_shares -= qty
            
            # Reset if shares go to 0 (or negative, though shouldn't happen)
            if total_shares <= 0.000001:
                total_shares = 0
                total_cost = 0
                first_buy_date = None

        if total_shares <= 0.000001:
            # Instead of deleting, we now update to 0 shares to keep history if needed (Show Sold feature)
            # But we should only keep it if there WAS transaction history. 
            # If txs is empty (e.g. all transactions deleted), then we should delete the holding.
            if not txs:
                delete_query = """
                    DELETE FROM portfolio_oltp.portfolio_holdings
                    WHERE portfolio_id = %s AND stock_ticker = %s
                """
                params = (portfolio_id, ticker)
                if cur:
                    cur.execute(delete_query, params)
                else:
                    self.execute_query(delete_query, params)
            else:
                # Update to 0
                update_zero_query = """
                    UPDATE portfolio_oltp.portfolio_holdings
                    SET total_shares = 0, avg_cost_basis = 0, updated_at = CURRENT_TIMESTAMP
                    WHERE portfolio_id = %s AND stock_ticker = %s
                """
                params = (portfolio_id, ticker)
                if cur:
                    cur.execute(update_zero_query, params)
                else:
                    self.execute_query(update_zero_query, params)
        else:
            avg_cost_basis = total_cost / total_shares
            
            # Upsert into holdings table
            upsert_query = """
                INSERT INTO portfolio_oltp.portfolio_holdings 
                (holding_id, portfolio_id, stock_ticker, total_shares, avg_cost_basis, first_buy_date)
                VALUES (%s, %s, %s, %s, %s, %s)
                ON CONFLICT (portfolio_id, stock_ticker) 
                DO UPDATE SET 
                    total_shares = EXCLUDED.total_shares,
                    avg_cost_basis = EXCLUDED.avg_cost_basis,
                    first_buy_date = EXCLUDED.first_buy_date,
                    updated_at = CURRENT_TIMESTAMP
            """
            # Generate ID only if insert needed (simplified logic here)
            holding_id = str(uuid.uuid4()) 
            
            params = (holding_id, portfolio_id, ticker, total_shares, avg_cost_basis, first_buy_date)

            if cur:
                cur.execute(upsert_query, params)
            else:
                self.execute_query(upsert_query, params)

    def update_transaction(self, transaction_id: str, portfolio_id: str,
                          ticker: str, transaction_type: str, quantity: float, price: float,
                          fee: float = 0, tax: float = 0, date: datetime = None, note: str = None) -> bool:
        """
        Update a transaction and recalculate holdings for both old and new ticker (if changed).
        """
        conn = self.get_connection()
        try:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                # 1. Get old transaction info
                cur.execute("SELECT stock_ticker FROM portfolio_oltp.portfolio_transactions WHERE transaction_id = %s", (transaction_id,))
                row = cur.fetchone()
                if not row:
                    return False
                old_ticker = row['stock_ticker']

                # 2. Update transaction
                update_query = """
                    UPDATE portfolio_oltp.portfolio_transactions
                    SET stock_ticker = %s, transaction_type = %s, quantity = %s, price = %s, 
                        fee = %s, tax = %s, transaction_date = %s, note = %s
                    WHERE transaction_id = %s AND portfolio_id = %s
                """
                cur.execute(update_query, (
                    ticker, transaction_type, quantity, price, fee, tax, date, note,
                    transaction_id, portfolio_id
                ))

                # 3. Update cache for OLD ticker (if different)
                if old_ticker != ticker:
                     self._update_holding_cache(portfolio_id, old_ticker, cur)
                
                # 4. Update cache for NEW ticker
                self._update_holding_cache(portfolio_id, ticker, cur)
            
            conn.commit()
            return True
        except Exception as e:
            conn.rollback()
            logger.error(f"Error updating transaction: {e}")
            raise e
        finally:
            conn.close()
    def delete_transaction(self, transaction_id: str, portfolio_id: str) -> bool:
        """
        Delete a specific transaction and update the holdings cache.
        """
        conn = self.get_connection()
        try:
             with conn.cursor(cursor_factory=RealDictCursor) as cur:
                # 1. Get ticker info before delete to update cache later
                cur.execute("SELECT stock_ticker FROM portfolio_oltp.portfolio_transactions WHERE transaction_id = %s", (transaction_id,))
                row = cur.fetchone()
                if not row:
                    return False
                ticker = row['stock_ticker']

                # 2. Delete transaction
                cur.execute("DELETE FROM portfolio_oltp.portfolio_transactions WHERE transaction_id = %s", (transaction_id,))
                
                # 3. Update cache
                self._update_holding_cache(portfolio_id, ticker, cur)
             conn.commit()
             return True
        except Exception as e:
            conn.rollback()
            logger.error(f"Error deleting transaction: {e}")
            raise e
        finally:
            conn.close()

    def delete_holding(self, portfolio_id: str, ticker: str) -> bool:
        """
        Delete a holding, implying deletion of ALL transactions for this ticker in this portfolio.
        """
        conn = self.get_connection()
        try:
            with conn.cursor() as cur:
                # 1. Delete all transactions for this ticker
                cur.execute("DELETE FROM portfolio_oltp.portfolio_transactions WHERE portfolio_id = %s AND stock_ticker = %s", (portfolio_id, ticker))
                
                # 2. Delete the holding record explicitly (cache update would likely result in 0/empty anyway, but explicit is cleaner)
                cur.execute("DELETE FROM portfolio_oltp.portfolio_holdings WHERE portfolio_id = %s AND stock_ticker = %s", (portfolio_id, ticker))
            conn.commit()
            return True
        except Exception as e:
            conn.rollback()
            logger.error(f"Error deleting holding: {e}")
            raise e
        finally:
            conn.close()

    def delete_portfolio(self, portfolio_id: str, user_id: str) -> bool:
        """
        Delete a portfolio and all related data (transactions, holdings).
        Verifies ownership via user_id.
        """
        check_query = "SELECT 1 FROM portfolio_oltp.portfolios WHERE portfolio_id = %s AND user_id = %s"
        rows = self.fetch_all(check_query, (portfolio_id, user_id))
        if not rows:
            return False

        # Delete dependent data first (holdings, transactions) then portfolio
        # Using a transaction block
        conn = self.get_connection()
        try:
            with conn.cursor() as cur:
                # 1. Delete Holdings
                cur.execute("DELETE FROM portfolio_oltp.portfolio_holdings WHERE portfolio_id = %s", (portfolio_id,))
                # 2. Delete Transactions
                cur.execute("DELETE FROM portfolio_oltp.portfolio_transactions WHERE portfolio_id = %s", (portfolio_id,))
                # 3. Delete Portfolio
                cur.execute("DELETE FROM portfolio_oltp.portfolios WHERE portfolio_id = %s", (portfolio_id,))
            conn.commit()
            return True
        except Exception as e:
            conn.rollback()
            logger.error(f"Error deleting portfolio: {e}")
            raise e
        finally:
            conn.close()
