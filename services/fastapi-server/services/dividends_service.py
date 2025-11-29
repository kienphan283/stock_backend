from services.data_loader import StockDataLoader
import logging

logger = logging.getLogger(__name__)

class DividendsService:
    """Service for dividend history data"""

    def get_dividends(self, ticker: str):
        """Get dividend history for a given ticker"""
        try:
            logger.info(f"Fetching dividends for {ticker}")
            loader = StockDataLoader(ticker.upper())
            data = loader.get_dividends()
            return data
        except Exception as e:
            logger.error(f"Error fetching dividends: {e}")
            raise
