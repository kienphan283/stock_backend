import psycopg2
from psycopg2.extras import RealDictCursor
from config.settings import settings
import logging

logger = logging.getLogger(__name__)

class CompaniesService:
    """Service for companies data"""

    def get_companies(self):
        """Retrieve list of all companies available in the database"""
        try:
            logger.info("Fetching list of companies from database")

            DB_CONFIG = {
                "host": settings.DB_HOST,
                "port": settings.DB_PORT,
                "dbname": settings.DB_NAME,
                "user": settings.DB_USER,
                "password": settings.DB_PASSWORD
            }

            conn = psycopg2.connect(**DB_CONFIG)
            cursor = conn.cursor(cursor_factory=RealDictCursor)

            query = """
                SELECT DISTINCT
                    company_id as ticker,
                    company_name as name,
                    sector,
                    exchange
                FROM financial_oltp.company
                ORDER BY company_name
            """

            cursor.execute(query)
            companies = cursor.fetchall()

            cursor.close()
            conn.close()

            logger.info(f"Found {len(companies)} companies in database")

            return {
                "count": len(companies),
                "companies": companies
            }

        except Exception as e:
            logger.error(f"Error fetching companies: {e}")
            raise
