from services.data_loader import StockDataLoader
import logging

logger = logging.getLogger(__name__)

class SummaryService:
    """Service for data summary"""

    def __init__(self, ticker: str = "APP"):
        self.ticker = ticker

    def get_summary(self):
        """Get data summary and status"""
        try:
            logger.info("Fetching data summary")
            loader = StockDataLoader(self.ticker.upper())
            data = loader.get_data_summary()
            return data
        except Exception as e:
            logger.error(f"Error fetching summary: {e}")
            raise
