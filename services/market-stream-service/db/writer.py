# MODULE: Database writer for realtime trades and bars.
# PURPOSE: Persist Kafka messages into Postgres tables.

"""
Database Writer
Writes processed messages to PostgreSQL
"""

from psycopg2.extras import execute_values
from config.settings import settings
from datetime import datetime
import sys
from pathlib import Path

ROOT_PATH = Path(__file__).resolve().parent.parent
if str(ROOT_PATH) not in sys.path:
    sys.path.insert(0, str(ROOT_PATH))
from shared.python.db.connector import PostgresConnector
from shared.python.utils.error_handlers import safe_db_call
from shared.python.utils.logging_config import get_logger

logger = get_logger(__name__)


class DatabaseWriter:
    def __init__(self):
        self.db_config = {
            "host": settings.DB_HOST,
            "port": settings.DB_PORT,
            "dbname": settings.DB_NAME,
            "user": settings.DB_USER,
            "password": settings.DB_PASSWORD,
        }
        self._connector = PostgresConnector(self.db_config)
    
    def _get_connection(self):
        """Get database connection"""
        return safe_db_call(
            lambda: self._connector.get_connection(),
            context="get_connection",
            on_error=lambda exc: logger.error("Failed to obtain DB connection: %s", exc),
        )
    
    def _get_stock_id(self, ticker: str, cursor) -> int:
        """Get stock_id from ticker symbol"""
        cursor.execute(
            "SELECT stock_id FROM market_data_oltp.stocks WHERE stock_ticker = %s",
            (ticker.upper(),)
        )
        result = cursor.fetchone()
        if result:
            return result[0]
        # If not found, create stock entry (simplified - should use proper service)
        cursor.execute(
            "INSERT INTO market_data_oltp.stocks (stock_ticker) VALUES (%s) ON CONFLICT DO NOTHING RETURNING stock_id",
            (ticker.upper(),)
        )
        result = cursor.fetchone()
        if result:
            return result[0]
        # Try again
        cursor.execute(
            "SELECT stock_id FROM market_data_oltp.stocks WHERE stock_ticker = %s",
            (ticker.upper(),)
        )
        return cursor.fetchone()[0]
    
    def write_trade(self, symbol: str, price: float, size: float, timestamp: int):
        """Write trade to stock_trades_realtime table"""
        conn = self._get_connection()
        if not conn:
            return
        try:
            def _write_trade() -> bool:
                with conn.cursor() as cursor:
                    stock_id = self._get_stock_id(symbol, cursor)
                    ts = datetime.fromtimestamp(timestamp / 1e9)
                    cursor.execute(
                        """
                        INSERT INTO market_data_oltp.stock_trades_realtime 
                        (stock_id, ts, price, size)
                        VALUES (%s, %s, %s, %s)
                        """,
                        (stock_id, ts, price, size),
                    )
                return True

            result = safe_db_call(
                _write_trade,
                context="write_trade",
                on_error=lambda exc: logger.error(f"Error writing trade: {exc}"),
            )
            if result is None:
                conn.rollback()
                return
            conn.commit()
        finally:
            conn.close()
    
    def write_bar(self, symbol: str, open_price: float, high: float, 
                  low: float, close: float, volume: int, timestamp: int):
        """Write bar to stock_bars_staging table"""
        conn = self._get_connection()
        if not conn:
            return
        try:
            def _write_bar() -> bool:
                with conn.cursor() as cursor:
                    stock_id = self._get_stock_id(symbol, cursor)
                    ts = datetime.fromtimestamp(timestamp / 1e9)
                    cursor.execute(
                        """
                        INSERT INTO market_data_oltp.stock_bars_staging 
                        (stock_id, timeframe, ts, open_price, high_price, low_price, close_price, volume)
                        VALUES (%s, '1m', %s, %s, %s, %s, %s, %s)
                        ON CONFLICT (stock_id, ts, timeframe) DO UPDATE SET
                            open_price = EXCLUDED.open_price,
                            high_price = EXCLUDED.high_price,
                            low_price = EXCLUDED.low_price,
                            close_price = EXCLUDED.close_price,
                            volume = EXCLUDED.volume
                        """,
                        (stock_id, ts, open_price, high, low, close, volume),
                    )
                return True

            result = safe_db_call(
                _write_bar,
                context="write_bar",
                on_error=lambda exc: logger.error(f"Error writing bar: {exc}"),
            )
            if result is None:
                conn.rollback()
                return
            conn.commit()
        finally:
            conn.close()

