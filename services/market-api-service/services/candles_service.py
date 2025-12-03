from db.candles_repo import CandlesRepository
from core.redis_client import RedisClient
import logging

logger = logging.getLogger(__name__)

class CandlesService:
    """Service for intraday candle/bar data (OHLCV for candlestick charts)"""
    
    def __init__(self):
        self.repo = CandlesRepository()
        self.redis = RedisClient()
    
    def get_candles(self, ticker: str, timeframe: str = "5m", limit: int = 300) -> list:
        """
        Get intraday candles (OHLCV) for candlestick charts.
        
        First checks Redis cache, then falls back to PostgreSQL.
        
        Args:
            ticker: Stock ticker symbol
            timeframe: Timeframe (1m, 5m, 15m, 1h, 1d)
            limit: Maximum number of candles to return
        
        Returns:
            List of dicts: [{"ts": "2025-10-29T10:00:00Z", "open": 308.0, "high": 310.0, "low": 307.0, "close": 309.0, "volume": 1000000}, ...]
        """
        logger.info(f"[CandlesService] get_candles: ticker={ticker}, timeframe={timeframe}, limit={limit}")
        
        # Check Redis cache first
        cache_key = f"candles:{ticker.upper()}:{timeframe}"
        cached = self.redis.get(cache_key)
        if cached:
            logger.info(f"[CandlesService] Cache hit for {cache_key}")
            # Limit cached results if needed
            if limit and len(cached) > limit:
                return cached[-limit:]
            return cached
        
        # Resolve ticker to stock_id
        stock_id = self.repo.get_stock_id(ticker)
        if not stock_id:
            logger.warning(f"[CandlesService] Stock ticker {ticker} not found")
            return []
        
        logger.info(f"[CandlesService] Resolved {ticker} to stock_id={stock_id}")
        
        # Get candles from PostgreSQL
        rows = self.repo.get_candles(stock_id, timeframe, limit)
        
        # Transform to response format
        candles = []
        for row in rows:
            if isinstance(row, dict):
                ts_val = row['ts']
                open_val = row['open']
                high_val = row['high']
                low_val = row['low']
                close_val = row['close']
                volume_val = row['volume']
            else:
                ts_val = row[0]
                open_val = row[1]
                high_val = row[2]
                low_val = row[3]
                close_val = row[4]
                volume_val = row[5]
            
            candles.append({
                "ts": ts_val.isoformat() if ts_val else None,
                "open": float(open_val) if open_val else 0.0,
                "high": float(high_val) if high_val else 0.0,
                "low": float(low_val) if low_val else 0.0,
                "close": float(close_val) if close_val else 0.0,
                "volume": int(volume_val) if volume_val else 0
            })
        
        # Cache the result
        if candles:
            self.redis.set(cache_key, candles, ttl=300)  # 5 minute cache
        
        logger.info(f"[CandlesService] Returning {len(candles)} candles for {ticker}")
        return candles

