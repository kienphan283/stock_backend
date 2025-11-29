from services.data_loader import StockDataLoader
import logging

logger = logging.getLogger(__name__)

class NewsService:
    """Service for company news data"""

    def get_news(self, ticker: str, limit: int = 16):
        """Get company news for a given ticker"""
        try:
            logger.info(f"Fetching news for {ticker}, limit: {limit}")
            loader = StockDataLoader(ticker.upper())
            data = loader.get_news(limit)
            return data
        except Exception as e:
            logger.error(f"Error fetching news: {e}")
            raise
