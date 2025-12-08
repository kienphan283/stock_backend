import psycopg2
from psycopg2.extras import RealDictCursor
from config.settings import settings
import logging

logger = logging.getLogger(__name__)

class BaseRepository:
    def __init__(self):
        self.db_config = {
            "host": settings.DB_HOST,
            "port": settings.DB_PORT,
            "dbname": settings.DB_NAME,
            "user": settings.DB_USER,
            "password": settings.DB_PASSWORD,
            "sslmode": "require"
        }

    def get_connection(self):
        return psycopg2.connect(**self.db_config)

    def execute_query(self, query, params=None, fetch_one=False, fetch_all=False):
        conn = self.get_connection()
        try:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(query, params)
                if fetch_one:
                    return cur.fetchone()
                if fetch_all:
                    return cur.fetchall()
                conn.commit()
        except Exception as e:
            logger.error(f"Database error: {e}")
            raise
        finally:
            conn.close()
