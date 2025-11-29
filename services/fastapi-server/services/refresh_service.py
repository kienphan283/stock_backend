from services.data_loader import StockDataLoader
import logging

logger = logging.getLogger(__name__)

class RefreshService:
    """Service for refreshing data"""

    def __init__(self, ticker: str = "APP"):
        self.ticker = ticker

    def refresh_data(self):
        """Refresh data from Finnhub API"""
        try:
            logger.info("Refreshing data from Finnhub API...")
            loader = StockDataLoader(self.ticker.upper())
            success = loader.refresh_data()
            return success
        except Exception as e:
            logger.error(f"Error refreshing data: {e}")
            raise
