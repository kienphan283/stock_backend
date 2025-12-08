import logging
from db.market_repo import MarketMetadataRepository
from core.redis_client import RedisClient
from typing import List
import json

logger = logging.getLogger(__name__)


class MarketMetadataService:
  """Service layer for market-level metadata exposed to the frontend."""

  def __init__(self) -> None:
      self.repo = MarketMetadataRepository()
      self.redis_client = RedisClient()

  def get_stocks_for_heatmap(self) -> dict:
      """
      Return list of active stocks for the heatmap:
      [
        { symbol, name, exchange, sector | null }
      ]
      """
      logger.info("[MarketMetadataService] Fetching stocks for heatmap")
      stocks = self.repo.get_all_active_stocks()
      # Filter out indices (e.g. ^GSPC) from heatmap
      stocks = [s for s in stocks if not s['symbol'].startswith('^')]
      return {
          "count": len(stocks),
          "stocks": stocks,
      }

  def get_accumulated_volumes(self, symbols: List[str]) -> dict:
      """
      Lấy volume tích lũy từ DB cho nhiều symbols, với Redis caching để tăng tốc.
      
      Args:
          symbols: List of ticker symbols (e.g., ["AAPL", "MSFT", "GOOGL"])
      
      Returns:
          Dict {symbol: volume} - volume tích lũy từ record mới nhất
      """
      if not symbols:
          return {}
      
      # Normalize symbols to uppercase
      normalized_symbols = [s.upper() for s in symbols]
      cache_key = f"heatmap:volumes:{':'.join(sorted(normalized_symbols))}"
      
      # Try Redis cache first (TTL: 2 seconds để balance giữa realtime và performance)
      try:
          cached = self.redis_client.get(cache_key)
          if cached:
              logger.info(f"[MarketMetadataService] Cache hit for volumes: {len(normalized_symbols)} symbols")
              # get() already returns parsed JSON (dict), no need to json.loads
              return cached if isinstance(cached, dict) else json.loads(cached)
      except Exception as e:
          logger.warning(f"[MarketMetadataService] Redis cache read error: {e}")
      
      # Cache miss: query from DB
      logger.info(f"[MarketMetadataService] Fetching volumes from DB for {len(normalized_symbols)} symbols")
      volumes = self.repo.get_accumulated_volumes(normalized_symbols)
      
      # Cache result (TTL: 2 seconds)
      try:
          self.redis_client.setex(cache_key, 2, volumes)
      except Exception as e:
          logger.warning(f"[MarketMetadataService] Redis cache write error: {e}")
      
      return volumes







