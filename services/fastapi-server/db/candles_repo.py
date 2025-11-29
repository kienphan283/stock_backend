from .base_repo import BaseRepository
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)

class CandlesRepository(BaseRepository):
    """Repository for intraday candle/bar data (OHLCV)"""
    
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
    
    def get_candles(self, stock_id: int, timeframe: str, limit: int = 300) -> list:
        """
        Get intraday candles (OHLCV) from stock_bars or stock_bars_staging.
        
        For 1m timeframe, tries staging first (realtime), then falls back to stock_bars.
        For other timeframes, uses stock_bars (aggregated).
        
        Args:
            stock_id: Stock ID from market_data_oltp.stocks
            timeframe: Timeframe (1m, 5m, 15m, 1h, 1d) - 1m = 1 minute, NOT 1 month
            limit: Maximum number of candles to return
        
        Returns:
            List of dicts with {ts, open, high, low, close, volume}
        """
        logger.info(f"[CandlesRepository] get_candles: stock_id={stock_id}, timeframe={timeframe}, limit={limit}")
        
        # Validate timeframe
        valid_timeframes = ["1m", "5m", "15m", "1h", "1d"]
        if timeframe not in valid_timeframes:
            logger.warning(f"[CandlesRepository] Invalid timeframe: {timeframe}, using 1m")
            timeframe = "1m"
        
        # For 1m, try staging first (realtime data), then fallback to stock_bars
        if timeframe == "1m":
            # Try staging table first
            query_staging = """
                SELECT
                    ts,
                    open_price as open,
                    high_price as high,
                    low_price as low,
                    close_price as close,
                    volume
                FROM market_data_oltp.stock_bars_staging
                WHERE stock_id = %s
                    AND timeframe = '1m'
                ORDER BY ts DESC
                LIMIT %s
            """
            logger.info(f"[CandlesRepository] Trying staging table for 1m: stock_id={stock_id}, limit={limit}")
            rows = self.execute_query(query_staging, (stock_id, limit), fetch_all=True)
            
            if rows and len(rows) > 0:
                logger.info(f"[CandlesRepository] Found {len(rows)} rows in staging table")
            else:
                # Fallback to stock_bars
                logger.info(f"[CandlesRepository] Staging empty, falling back to stock_bars")
                query = """
                    SELECT
                        ts,
                        open_price as open,
                        high_price as high,
                        low_price as low,
                        close_price as close,
                        volume
                    FROM market_data_oltp.stock_bars
                    WHERE stock_id = %s
                        AND timeframe = '1m'
                    ORDER BY ts DESC
                    LIMIT %s
                """
                rows = self.execute_query(query, (stock_id, limit), fetch_all=True)
        else:
            # For other timeframes, use stock_bars (aggregated)
            query = """
                SELECT
                    ts,
                    open_price as open,
                    high_price as high,
                    low_price as low,
                    close_price as close,
                    volume
                FROM market_data_oltp.stock_bars
                WHERE stock_id = %s
                    AND timeframe = %s
                ORDER BY ts DESC
                LIMIT %s
            """
            logger.info(f"[CandlesRepository] Executing query: stock_id={stock_id}, timeframe={timeframe}, limit={limit}")
            rows = self.execute_query(query, (stock_id, timeframe, limit), fetch_all=True)
        
        # Reverse to get chronological order (oldest first)
        if rows:
            rows = list(reversed(rows))
        
        logger.info(f"[CandlesRepository] Query returned {len(rows) if rows else 0} rows")
        return rows or []

