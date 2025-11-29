from .base_repo import BaseRepository
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)

class PriceHistoryRepository(BaseRepository):
    def get_price_history(self, stock_id, days=None, limit=None, start_date=None):
        """
        Get price history from stock_eod_prices table.
        
        Args:
            stock_id: Stock ID to query
            days: Number of days to look back (from latest available date)
            limit: Maximum number of records to return
            start_date: Specific start date (overrides days)
        """
        logger.info(f"[PriceHistoryRepository] get_price_history: stock_id={stock_id}, days={days}, limit={limit}, start_date={start_date}")
        
        # First, get the latest trading date for this stock to calculate proper date range
        latest_date_query = """
            SELECT MAX(trading_date) as latest_date
            FROM market_data_oltp.stock_eod_prices
            WHERE stock_id = %s
        """
        latest_result = self.execute_query(latest_date_query, (stock_id,), fetch_one=True)
        
        if not latest_result:
            logger.warning(f"[PriceHistoryRepository] No data found for stock_id={stock_id}")
            return []
        
        latest_date = latest_result['latest_date'] if isinstance(latest_result, dict) else latest_result[0]
        logger.info(f"[PriceHistoryRepository] Latest trading date for stock_id={stock_id}: {latest_date}")
        
        query = """
            SELECT
                trading_date as date,
                open_price as open,
                high_price as high,
                low_price as low,
                close_price as close,
                volume,
                pct_change
            FROM market_data_oltp.stock_eod_prices
            WHERE stock_id = %s
        """
        params = [stock_id]
        
        if start_date:
            query += " AND trading_date >= %s"
            params.append(start_date)
            logger.info(f"[PriceHistoryRepository] Filtering by start_date: {start_date}")
        elif days:
            # Calculate start date from latest available date
            calculated_start = latest_date - timedelta(days=days)
            query += " AND trading_date >= %s"
            params.append(calculated_start)
            logger.info(f"[PriceHistoryRepository] Filtering by {days} days from latest date: {calculated_start}")
        elif limit:
            # If only limit is provided, get last N records
            query += " ORDER BY trading_date DESC LIMIT %s"
            params.append(limit)
            logger.info(f"[PriceHistoryRepository] Limiting to {limit} most recent records")
            rows = self.execute_query(query, tuple(params), fetch_all=True)
            # Reverse to get chronological order
            return list(reversed(rows)) if rows else []
            
        query += " ORDER BY trading_date ASC"
        
        if limit:
            query += " LIMIT %s"
            params.append(limit)
        
        logger.info(f"[PriceHistoryRepository] Executing query: {query[:100]}... with params: {params}")
        rows = self.execute_query(query, tuple(params), fetch_all=True)
        logger.info(f"[PriceHistoryRepository] Query returned {len(rows) if rows else 0} rows")
        return rows
