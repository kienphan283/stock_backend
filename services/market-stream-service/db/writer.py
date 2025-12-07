# MODULE: Database writer for realtime trades and bars.
# PURPOSE: Persist Kafka messages into Postgres tables.

"""
Database Writer
Writes processed messages to PostgreSQL
"""

from psycopg2.extras import execute_values
from config.settings import settings
from datetime import datetime
from dateutil import parser as date_parser
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

    def _normalize_timestamp(self, ts_raw):
        """
        Normalize incoming Alpaca timestamp to Python datetime.

        Alpaca's websocket `t` field may be either:
        - An ISO8601 string (e.g. "2025-01-27T15:41:00.123456789Z")
        - An integer nanosecond epoch.

        We handle both to avoid DB write failures while keeping nanosecond
        precision when possible.
        """
        try:
            if isinstance(ts_raw, str):
                # Parse ISO8601 string
                return date_parser.isoparse(ts_raw)
            # Assume integer nanoseconds
            return datetime.fromtimestamp(ts_raw / 1e9)
        except Exception as exc:
            logger.error("Failed to normalize timestamp %r: %s", ts_raw, exc)
            # Fallback to "now" to avoid breaking the pipeline
            return datetime.utcnow()
    
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
        """
        Write trade to stock_trades_realtime table with accumulated volume.
        
        Volume được cộng dồn: lấy volume từ record mới nhất của stock đó,
        cộng với size của trade mới, rồi lưu vào cột volume.
        """
        conn = self._get_connection()
        if not conn:
            return
        try:
            def _write_trade() -> bool:
                with conn.cursor() as cursor:
                    stock_id = self._get_stock_id(symbol, cursor)
                    ts = self._normalize_timestamp(timestamp)
                    
                    # Lấy volume tích lũy từ record mới nhất của stock này
                    cursor.execute(
                        """
                        SELECT COALESCE(volume, 0) 
                        FROM market_data_oltp.stock_trades_realtime 
                        WHERE stock_id = %s 
                        ORDER BY ts DESC, trade_id DESC 
                        LIMIT 1
                        """,
                        (stock_id,)
                    )
                    result = cursor.fetchone()
                    previous_volume = float(result[0]) if result and result[0] is not None else 0.0
                    
                    # Cộng dồn: volume mới = volume cũ + size của trade mới
                    accumulated_volume = previous_volume + size
                    
                    # Log để debug
                    logger.info(
                        f"[DB Writer] Writing trade for {symbol}: "
                        f"size={size}, previous_volume={previous_volume}, "
                        f"accumulated_volume={accumulated_volume}"
                    )
                    
                    # Insert trade mới với volume tích lũy
                    cursor.execute(
                        """
                        INSERT INTO market_data_oltp.stock_trades_realtime 
                        (stock_id, ts, price, size, volume)
                        VALUES (%s, %s, %s, %s, %s)
                        ON CONFLICT (stock_id, ts) DO NOTHING
                        """,
                        (stock_id, ts, price, size, accumulated_volume),
                    )
                    
                    logger.info(
                        f"[DB Writer] ✅ Successfully inserted trade for {symbol} "
                        f"with accumulated_volume={accumulated_volume}"
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
                    ts = self._normalize_timestamp(timestamp)
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

