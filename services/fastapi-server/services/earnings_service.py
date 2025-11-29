from services.data_loader import StockDataLoader
import logging

logger = logging.getLogger(__name__)

class EarningsService:
    """Service for earnings data"""

    def __init__(self, ticker: str = "APP"):
        self.ticker = ticker

    def get_earnings(self):
        """Get earnings data"""
        try:
            logger.info(f"Fetching earnings for {self.ticker}")
            loader = StockDataLoader(self.ticker.upper())
            data = loader.get_earnings()
            return data
        except Exception as e:
            logger.error(f"Error fetching earnings: {e}")
            raise
