import psycopg2
from psycopg2.extras import RealDictCursor
from config.settings import settings
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)

class PriceHistoryService:
    """Service for stock price history data"""

    def get_price_history(self, ticker: str, period: str = "3m"):
        """Get price history for a given ticker and period with OHLC data"""
        try:
            logger.info(f"[PriceHistoryService] Fetching price history for {ticker}, period: {period}")

            DB_CONFIG = {
                "host": settings.DB_HOST,
                "port": settings.DB_PORT,
                "dbname": settings.DB_NAME,
                "user": settings.DB_USER,
                "password": settings.DB_PASSWORD
            }

            # Convert period to days (trading days, approximate)
            # Note: "1m" = 1 month (30 days), NOT 1 minute
            period_days_map = {
                "1d": 1,
                "5d": 5,
                "1m": 30,      # 1 month = 30 days
                "1mo": 30,    # Alias for 1 month
                "3m": 90,     # 3 months = 90 days
                "3mo": 90,    # Alias for 3 months
                "6m": 180,    # 6 months = 180 days
                "6mo": 180,   # Alias for 6 months
                "ytd": 365,   # Year to date (simplified)
                "1y": 365,    # 1 year = 365 days
                "5y": 1825,   # 5 years = 1825 days
                "max": 10000  # Large number to get all data
            }

            days = period_days_map.get(period.lower(), 90)
            logger.info(f"[PriceHistoryService] Period '{period}' mapped to {days} days")

            conn = psycopg2.connect(**DB_CONFIG)
            try:
                with conn.cursor(cursor_factory=RealDictCursor) as cur:
                    # Get stock_id from ticker
                    cur.execute("""
                        SELECT stock_id
                        FROM market_data_oltp.stocks
                        WHERE stock_ticker = %s
                    """, (ticker.upper(),))

                    stock_result = cur.fetchone()
                    if not stock_result:
                        logger.warning(f"[PriceHistoryService] Stock ticker {ticker} not found in database")
                        return []

                    stock_id = stock_result['stock_id'] if isinstance(stock_result, dict) else stock_result[0]
                    logger.info(f"[PriceHistoryService] Resolved {ticker} to stock_id={stock_id}")

                    # For short periods (1d, 5d), get last N records
                    # For longer periods, use date range from latest available date
                    if period.lower() in ["1d", "5d"]:
                        limit = days
                        query = """
                            SELECT
                                trading_date as date,
                                open_price as open,
                                high_price as high,
                                low_price as low,
                                close_price as close,
                                volume
                            FROM market_data_oltp.stock_eod_prices
                            WHERE stock_id = %s
                            ORDER BY trading_date DESC
                            LIMIT %s
                        """
                        logger.info(f"[PriceHistoryService] Executing LIMIT query: stock_id={stock_id}, limit={limit}")
                        cur.execute(query, (stock_id, limit))
                    else:
                        # For longer periods, calculate date range from latest available date
                        # First, get the latest trading date for this stock
                        cur.execute("""
                            SELECT MAX(trading_date) as latest_date
                            FROM market_data_oltp.stock_eod_prices
                            WHERE stock_id = %s
                        """, (stock_id,))
                        latest_result = cur.fetchone()
                        
                        # Fix: Check if result exists and has valid date (avoid KeyError)
                        if not latest_result:
                            logger.warning(f"[PriceHistoryService] No trading dates found for stock_id={stock_id}")
                            return []
                        
                        # Safely extract latest_date from dict or tuple
                        if isinstance(latest_result, dict):
                            latest_date = latest_result.get('latest_date')
                        else:
                            latest_date = latest_result[0] if len(latest_result) > 0 else None
                        
                        if not latest_date:
                            logger.warning(f"[PriceHistoryService] Latest date is None for stock_id={stock_id}")
                            return []
                        
                        start_date = latest_date - timedelta(days=days)
                        logger.info(f"[PriceHistoryService] Date range calculation: latest_date={latest_date}, days={days}, start_date={start_date}")

                        query = """
                            SELECT
                                trading_date as date,
                                open_price as open,
                                high_price as high,
                                low_price as low,
                                close_price as close,
                                volume
                            FROM market_data_oltp.stock_eod_prices
                            WHERE stock_id = %s
                                AND trading_date >= %s
                            ORDER BY trading_date ASC
                        """
                        logger.info(f"[PriceHistoryService] Executing date range query: stock_id={stock_id}, start_date={start_date}")
                        cur.execute(query, (stock_id, start_date))

                    rows = cur.fetchall()
                    row_count = len(rows) if rows else 0
                    logger.info(f"[PriceHistoryService] Query returned {row_count} rows for stock_id={stock_id}")

                    # If no rows found, return empty array (not an error)
                    if not rows:
                        logger.info(f"[PriceHistoryService] No EOD price data found for {ticker} (stock_id={stock_id}), period={period}")
                        return []

                    # Transform to array of OHLC objects
                    price_history = []
                    for row in rows:
                        # Handle both tuple and dict cursor results
                        if isinstance(row, dict):
                            date_val = row.get('date')
                            open_val = row.get('open')
                            high_val = row.get('high')
                            low_val = row.get('low')
                            close_val = row.get('close')
                            volume_val = row.get('volume')
                        else:
                            date_val = row[0] if len(row) > 0 else None
                            open_val = row[1] if len(row) > 1 else None
                            high_val = row[2] if len(row) > 2 else None
                            low_val = row[3] if len(row) > 3 else None
                            close_val = row[4] if len(row) > 4 else None
                            volume_val = row[5] if len(row) > 5 else None

                        price_history.append({
                            "date": date_val.isoformat() if date_val and hasattr(date_val, 'isoformat') else (str(date_val) if date_val else None),
                            "open": float(open_val) if open_val is not None else 0.0,
                            "high": float(high_val) if high_val is not None else 0.0,
                            "low": float(low_val) if low_val is not None else 0.0,
                            "close": float(close_val) if close_val is not None else 0.0,
                            "volume": int(volume_val) if volume_val is not None else 0
                        })

                    # For short periods, reverse to get chronological order
                    if period.lower() in ["1d", "5d"]:
                        price_history.reverse()

                    logger.info(f"[PriceHistoryService] Successfully retrieved {len(price_history)} price records for {ticker} (stock_id={stock_id})")
                    return price_history

            finally:
                conn.close()

        except Exception as e:
            logger.error(f"[PriceHistoryService] Error fetching price history for {ticker}, period={period}: {e}", exc_info=True)
            # Return empty array instead of raising exception
            # Only raise if it's a critical error (e.g., DB connection failure)
            return []
