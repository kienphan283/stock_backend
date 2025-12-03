from .base_repo import BaseRepository
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)

class EODPriceRepository(BaseRepository):
    """Repository for End-of-Day price data (price charts only)"""
    
    def get_stock_id(self, ticker: str) -> int | None:
        """Resolve ticker symbol to stock_id"""
        query = """
            SELECT stock_id
            FROM market_data_oltp.stocks
            WHERE stock_ticker = %s
        """
        result = self.execute_query(query, (ticker.upper(),), fetch_one=True)
        if result:
            return result['stock_id'] if isinstance(result, dict) else result[0]
        return None
    
    def get_latest_trading_date(self, stock_id: int) -> datetime | None:
        """Get the latest trading date for a stock"""
        query = """
            SELECT MAX(trading_date) as latest_date
            FROM market_data_oltp.stock_eod_prices
            WHERE stock_id = %s
        """
        result = self.execute_query(query, (stock_id,), fetch_one=True)
        if result:
            latest = result['latest_date'] if isinstance(result, dict) else result[0]
            return latest
        return None
    
    def get_price_history(self, stock_id: int, period: str) -> list:
        """
        Get EOD price history (full OHLCV) from stock_eod_prices table.
        
        Args:
            stock_id: Stock ID from market_data_oltp.stocks
            period: Period string (1d, 5d, 1mo, 3mo, 6mo, 1y, ytd, max)
                   Note: "1m" is NOT valid here (use "1mo" for 1 month)
        
        Returns:
            List of dicts with {date, open, high, low, close, volume}
        """
        logger.info(f"[EODPriceRepository] get_price_history: stock_id={stock_id}, period={period}")
        
        # Period to days mapping (EOD periods - months, not minutes)
        period_days_map = {
            "1d": 1,
            "5d": 5,
            "1mo": 30,      # 1 month = ~30 days
            "1m": 30,       # Alias for 1mo (handle common mistake)
            "3mo": 90,
            "3m": 90,       # Alias for 3mo
            "6mo": 180,
            "6m": 180,      # Alias for 6mo
            "ytd": 365,
            "1y": 365,
            "5y": 1825,
            "max": 10000
        }
        
        days = period_days_map.get(period.lower(), 90)
        logger.info(f"[EODPriceRepository] Period '{period}' mapped to {days} days")
        
        # Get latest trading date
        latest_date = self.get_latest_trading_date(stock_id)
        if not latest_date:
            logger.warning(f"[EODPriceRepository] No trading dates found for stock_id={stock_id}")
            return []
        
        logger.info(f"[EODPriceRepository] Latest trading date: {latest_date}")
        
        # For short periods, use LIMIT
        if period.lower() in ["1d", "5d"]:
            query = """
                SELECT
                    trading_date as date,
                    open_price as open,
                    high_price as high,
                    low_price as low,
                    close_price as close,
                    volume
                FROM market_data_oltp.stock_eod_prices
                WHERE stock_id = %s
                ORDER BY trading_date DESC
                LIMIT %s
            """
            logger.info(f"[EODPriceRepository] Executing LIMIT query: stock_id={stock_id}, limit={days}")
            rows = self.execute_query(query, (stock_id, days), fetch_all=True)
            # Reverse to get chronological order
            if rows:
                rows = list(reversed(rows))
        else:
            # For longer periods, use date range from latest date
            start_date = latest_date - timedelta(days=days)
            query = """
                SELECT
                    trading_date as date,
                    open_price as open,
                    high_price as high,
                    low_price as low,
                    close_price as close,
                    volume
                FROM market_data_oltp.stock_eod_prices
                WHERE stock_id = %s
                    AND trading_date >= %s
                ORDER BY trading_date ASC
            """
            logger.info(f"[EODPriceRepository] Executing date range query: stock_id={stock_id}, start_date={start_date}")
            rows = self.execute_query(query, (stock_id, start_date), fetch_all=True)
        
        logger.info(f"[EODPriceRepository] Query returned {len(rows) if rows else 0} rows")
        return rows or []

