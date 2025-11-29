from services.data_loader import StockDataLoader
import logging

logger = logging.getLogger(__name__)

class FinancialsLegacyService:
    """Service for legacy financials data (CSV)"""

    def __init__(self, ticker: str = "APP"):
        self.ticker = ticker

    def get_financials(self):
        """Get financial statements (legacy endpoint using data loader)"""
        try:
            logger.info(f"Fetching financials for {self.ticker}")
            loader = StockDataLoader(self.ticker.upper())
            data = loader.get_financials()
            return data
        except Exception as e:
            logger.error(f"Error fetching financials: {e}")
            raise
