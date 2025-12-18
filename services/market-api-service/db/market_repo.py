from .base_repo import BaseRepository
import logging

logger = logging.getLogger(__name__)


class MarketMetadataRepository(BaseRepository):
    """Repository for market metadata (stocks list for heatmap, quotes, etc.)."""

    def get_all_active_stocks(self):
        """
        Fetch all non-delisted stocks from market_data_oltp.stocks.

        - symbol: stock_ticker
        - name: stock_name (fallback to financial_oltp.company.company_name)
        - exchange: exchange from stocks table
        - sector: sector from financial_oltp.company (may be NULL)
        """
        query = """
            SELECT
                s.stock_ticker AS symbol,
                COALESCE(s.stock_name, c.company_name) AS name,
                s.exchange,
                c.sector
            FROM market_data_oltp.stocks AS s
            LEFT JOIN financial_oltp.company AS c
                ON c.company_id = s.company_id
            WHERE s.delisted IS FALSE
            ORDER BY s.stock_ticker
        """
        logger.info("[MarketMetadataRepository] Fetching active stocks for market metadata")
        rows = self.execute_query(query, fetch_all=True)
        return rows or []

    def get_accumulated_volumes(self, symbols: list[str]) -> dict[str, float]:
        """
        Lấy volume tích lũy từ stock_trades_realtime cho nhiều symbols cùng lúc.
        
        Returns:
            Dict {symbol: volume} - volume tích lũy từ record mới nhất của mỗi symbol
        """
        if not symbols:
            return {}
        
        # Batch query: lấy volume mới nhất cho tất cả symbols trong 1 query
        # Sử dụng LATERAL JOIN để lấy record mới nhất cho mỗi stock
        placeholders = ','.join(['%s'] * len(symbols))
        query = f"""
            SELECT 
                s.stock_ticker AS symbol,
                COALESCE(t.size, 0) AS volume
            FROM market_data_oltp.stocks AS s
            LEFT JOIN LATERAL (
                SELECT size
                FROM market_data_oltp.stock_trades_realtime
                WHERE stock_id = s.stock_id
                ORDER BY ts DESC, trade_id DESC
                LIMIT 1
            ) AS t ON true
            WHERE s.stock_ticker IN ({placeholders})
                AND s.delisted IS FALSE

        """
        
        logger.info(f"[MarketMetadataRepository] Fetching accumulated volumes for {len(symbols)} symbols")
        rows = self.execute_query(query, [s.upper() for s in symbols], fetch_all=True)
        
        # Convert to dict {symbol: volume}
        result = {}
        for row in rows or []:
            symbol = row['symbol'] if isinstance(row, dict) else row[0]
            volume = float(row['volume'] if isinstance(row, dict) else row[1] or 0)
            result[symbol.upper()] = volume
        
        return result







    def check_stock_exists(self, ticker: str) -> bool:
        """
        Check if a stock ticker exists in the database (active or not).
        """
        query = "SELECT 1 FROM market_data_oltp.stocks WHERE stock_ticker = %s LIMIT 1"
        result = self.execute_query(query, (ticker.upper(),), fetch_one=True)
        return bool(result)

    def add_stock(self, ticker: str, name: str = None, exchange: str = 'NASDAQ') -> str:
        """
        Add a new stock to the database.
        """
        import uuid
        stock_id = str(uuid.uuid4())
        ticker = ticker.upper()
        if not name:
            name = ticker  # Fallback to ticker as name
            
        query = """
            INSERT INTO market_data_oltp.stocks (stock_id, stock_ticker, stock_name, exchange, is_etf, delisted)
            VALUES (%s, %s, %s, %s, FALSE, FALSE)
            ON CONFLICT (stock_ticker) DO UPDATE SET stock_name = EXCLUDED.stock_name
            RETURNING stock_id
        """
        result = self.execute_query(query, (stock_id, ticker, name, exchange), fetch_one=True)
        # If result is None (because of conflict where we didn't return?), try fetching
        if result:
            return result['stock_id'] if isinstance(result, dict) else result[0]
            
        # Fallback fetch if upsert returned nothing (though RETURNING should work)
        return self.check_stock_exists(ticker) # Return info or True-ish

