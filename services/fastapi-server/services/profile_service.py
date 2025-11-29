from services.data_loader import StockDataLoader
import logging

logger = logging.getLogger(__name__)

class ProfileService:
    """Service for company profile data"""

    def get_profile(self, ticker: str):
        """Get company profile for a given ticker"""
        try:
            logger.info(f"Fetching profile for {ticker}")
            loader = StockDataLoader(ticker.upper())
            data = loader.get_company_profile()
            return data
        except Exception as e:
            logger.error(f"Error fetching profile: {e}")
            raise
