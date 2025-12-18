from typing import List, Dict, Optional
from db.portfolio_repo import PortfolioRepo
from services.quote_service import QuoteService
import logging

logger = logging.getLogger(__name__)

class PortfolioService:
    def __init__(self):
        self.repo = PortfolioRepo()
        self.quote_service = QuoteService()
        from db.market_repo import MarketMetadataRepository
        self.market_repo = MarketMetadataRepository()

    def get_portfolio_summary(self, user_id: str) -> Dict:
        """
        Get high-level summary of all portfolios for a user.
        """
        portfolios = self.repo.get_user_portfolios(user_id)
        # For now, just return the list. Later we can add total value across all portfolios.
        return {
            "portfolios": portfolios,
            "total_value": 0 # Placeholder
        }

    def create_portfolio(self, user_id: str, name: str, currency: str = 'USD', 
                        goal_type: str = 'VALUE', target_amount: float = None, note: str = None) -> str:
        return self.repo.create_portfolio(user_id, name, currency, goal_type, target_amount, note)

    def delete_portfolio(self, portfolio_id: str, user_id: str) -> bool:
        return self.repo.delete_portfolio(portfolio_id, user_id)

    def add_transaction(self, portfolio_id: str, ticker: str, 
                       transaction_type: str, quantity: float, price: float,
                       fee: float = 0, note: str = None) -> str:
        
        # 1. Validate Numeric Inputs
        if quantity <= 0:
            raise ValueError("Quantity must be greater than 0")
        if price < 0:
            raise ValueError("Price cannot be negative")
        if fee < 0:
            raise ValueError("Fee cannot be negative")

        # 2. Validate Ticker Existence
        # 2. Validate Ticker Existence
        # 2. Validate Ticker Existence
        if not self.market_repo.check_stock_exists(ticker):
             # Try to add the stock
             try:
                 self.market_repo.add_stock(ticker)
             except Exception as e:
                 logger.warning(f"Failed to auto-add ticker {ticker} during add_transaction: {e}")

             # Re-check
             if not self.market_repo.check_stock_exists(ticker):
                 raise ValueError(f"Ticker '{ticker}' not found. Please verify the symbol.")

        return self.repo.add_transaction(
            portfolio_id=portfolio_id,
            ticker=ticker,
            transaction_type=transaction_type,
            quantity=quantity,
            price=price,
            fee=fee,
            note=note
        )

    def update_transaction(self, transaction_id: str, portfolio_id: str, ticker: str,
                          transaction_type: str, quantity: float, price: float,
                          fee: float = 0, date: str = None, note: str = None) -> bool:
        
        # 1. Validate Numeric Inputs
        if quantity <= 0:
            raise ValueError("Quantity must be greater than 0")
        if price < 0:
            raise ValueError("Price cannot be negative")
        if fee < 0:
            raise ValueError("Fee cannot be negative")

        # 2. Validate Ticker Existence
        # 2. Validate Ticker Existence
        # 2. Validate Ticker Existence
        if not self.market_repo.check_stock_exists(ticker):
             # Try to add the stock
             try:
                 self.market_repo.add_stock(ticker)
             except Exception as e:
                 logger.warning(f"Failed to auto-add ticker {ticker} during update_transaction: {e}")

             # Re-check
             if not self.market_repo.check_stock_exists(ticker):
                 raise ValueError(f"Ticker '{ticker}' not found. Please verify the symbol.")

        return self.repo.update_transaction(
            transaction_id=transaction_id,
            portfolio_id=portfolio_id,
            ticker=ticker,
            transaction_type=transaction_type,
            quantity=quantity,
            price=price,
            fee=fee,
            date=date,
            note=note
        )

    def get_holdings_with_market_data(self, portfolio_id: str) -> List[Dict]:
        """
        Get holdings and enrich them with current market price and daily change.
        Optimized to use batch fetching for market data.
        """
        holdings = self.repo.get_holdings(portfolio_id)
        if not holdings:
            return []

        # Extract tickers to fetch batch quotes
        tickers = list(set([h['stock_ticker'] for h in holdings if h.get('stock_ticker')]))
        
        market_data_map = {}
        try:
            if tickers:
                # Use batch fetch (auto_fetch=True ensures we actally get data from API if missing)
                market_data_map = self.quote_service.get_latest_eod_batch(tickers, auto_fetch=True)
        except Exception as e:
            logger.error(f"Error fetching batch market data: {e}")

        # Enrich holdings
        enriched_holdings = []
        for h in holdings:
            ticker = h['stock_ticker']
            ticker_upper = ticker.upper()
            shares = float(h['total_shares'])
            cost_basis = float(h['avg_cost_basis'])
            
            # 1. Try to get from batch result
            quote_data = market_data_map.get(ticker_upper)
            
            # 2. Fallback to single fetch if missing (optional, but good safety net)
            if not quote_data:
                try:
                    quote_data = self.quote_service.get_quote(ticker)
                except Exception:
                    quote_data = None

            # Extract fields
            if quote_data:
                # quote_data from batch might have slightly different keys than get_quote result
                # get_latest_eod_batch returns: {price, volume, changePercent, previousClose, ...}
                # get_quote returns camelCase keys: {currentPrice, change, percentChange...}
                
                # Check format
                if 'currentPrice' in quote_data: 
                     # It's from get_quote (fallback)
                     current_price = float(quote_data.get('currentPrice', 0))
                     previous_close = float(quote_data.get('previousClose', current_price))
                     daily_change_percent = float(quote_data.get('percentChange', 0))
                else: 
                     # It's from get_latest_eod_batch (db record)
                     current_price = float(quote_data.get('price', 0))
                     previous_close = float(quote_data.get('previousClose', current_price))
                     daily_change_percent = float(quote_data.get('changePercent', 0))
            else:
                 current_price = cost_basis # Fallback
                 previous_close = current_price
                 daily_change_percent = 0

            market_value = shares * current_price
            total_cost = shares * cost_basis
            
            gain_loss = market_value - total_cost
            gain_loss_percent = (gain_loss / total_cost * 100) if total_cost > 0 else 0
            
            # Ensure mathematical consistency for Daily Change
            # If we have a percentage but 0 absolute change (common in mock data or floating point issues),
            # we recalculate the absolute change from the percentage.
            daily_change_abs = (current_price - previous_close) * shares
            
            if daily_change_percent != 0 and abs(daily_change_abs) < 0.01 and market_value > 0:
                 # Recalculate based on percent: New = Old * (1 + p) => Change = New - Old
                 # Change ~ MarketValue * (p / (1+p))
                 # Or simpler: if New = 100, p = 1% => Old = 100/1.01 = 99.01 => Change = 0.99
                 p_decimal = daily_change_percent / 100.0
                 inferred_prev_value = market_value / (1 + p_decimal)
                 daily_change_abs = market_value - inferred_prev_value

            enriched_holdings.append({
                **h,
                "current_price": current_price,
                "market_value": market_value,
                "total_cost": total_cost,
                "gain_loss": gain_loss,
                "gain_loss_percent": gain_loss_percent,
                "daily_change": daily_change_abs,
                "daily_change_percent": daily_change_percent,
                "allocation": 0 
            })

        # Calculate Allocation
        total_portfolio_value = sum(item['market_value'] for item in enriched_holdings)
        for item in enriched_holdings:
            if total_portfolio_value > 0:
                item['allocation'] = (item['market_value'] / total_portfolio_value) * 100
            else:
                item['allocation'] = 0

        return enriched_holdings

    def get_transactions(self, portfolio_id: str, ticker: str = None) -> List[Dict]:
        transactions = self.repo.get_transactions(portfolio_id, ticker)
        
        # Sort by date ascending to calculate profit correctly
        # But wait, the repo returns DESC. We need ASC for calculation, then DESC for display.
        # However, to be strictly correct with "Average Cost Basis", we need ALL transactions of that ticker 
        # from the beginning to calculate accurately.
        # If the user filters by ticker, we might get a subset? 
        # The repo currently filters by portfolio_id (and optionally ticker).
        
        # If we want accurate P/L, we really should rely on the repo to having done this. 
        # But since we can't change schema easily, let's do a "best effort" calculation here 
        # assuming the 'transactions' list contains the necessary history.
        # NOTE: If pagination is added later, this logic will break.
        
        # Logic: Replay history to track Avg Cost
        # We need to process by Ticker + Date
        
        # Group by ticker first
        from collections import defaultdict
        tx_by_ticker = defaultdict(list)
        for tx in transactions:
            tx_by_ticker[tx['stock_ticker']].append(tx)
            
        # For each ticker, sort ASC, calculate, then apply back
        for ticker, txs in tx_by_ticker.items():
            # Sort ASC for calculation
            # Secondary sort by transaction_type to ensure 'BUY' (B) comes before 'SELL' (S) 
            # if timestamps are identical (common in manual entry or testing)
            txs.sort(key=lambda x: (x['transaction_date'], x['transaction_type']))
            
            total_shares = 0.0
            total_cost = 0.0
            
            for tx in txs:
                t_type = tx['transaction_type']
                qty = float(tx['quantity'])
                price = float(tx['price'])
                
                # Initialize total_profit field
                tx['total_profit'] = 0.0
                
                if t_type == 'BUY':
                    total_cost += (qty * price)
                    total_shares += qty
                elif t_type == 'SELL':
                    if total_shares > 0:
                        # Avg Cost at this moment
                        avg_cost = total_cost / total_shares
                        
                        # Realized Profit for this specific sell
                        # Profit = (Sell Price - Avg Cost) * Qty
                        realized_profit = (price - avg_cost) * qty
                        tx['total_profit'] = realized_profit
                        
                        # Reduce pool
                        total_cost -= (qty * avg_cost)
                        total_shares -= qty
                    else:
                        # Selling short or error state - assume 0 cost basis -> full profit? 
                        # Or 0 profit to be safe.
                        tx['total_profit'] = 0.0
        
        # Re-sort DESC for display
        transactions.sort(key=lambda x: x['transaction_date'], reverse=True)
        return transactions

    def delete_transaction(self, transaction_id: str, portfolio_id: str) -> bool:
        return self.repo.delete_transaction(transaction_id, portfolio_id)

    def delete_holding(self, portfolio_id: str, ticker: str) -> bool:
        return self.repo.delete_holding(portfolio_id, ticker)
