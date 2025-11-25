"""
Database Client - Infrastructure layer
Handles PostgreSQL connection and batch operations
"""
import logging
from typing import Dict, Any, List, Tuple, Optional

from psycopg2.extras import execute_batch

from etl.common.db import PostgresConnector

logger = logging.getLogger(__name__)


class DatabaseClient(PostgresConnector):
    """PostgreSQL client for batch inserts"""
    
    def __init__(self, db_config: Dict[str, Any]):
        """
        Initialize database connection
        
        Args:
            db_config: Database configuration dict with host, port, database, user, password
        """
        super().__init__(db_config)
        self.cursor: Optional["psycopg2.extensions.cursor"] = None
        self._connect()

    def _connect(self):
        try:
            self.conn = self.connect()
            self.conn.autocommit = False
            self.cursor = self.conn.cursor()
            logger.info("✓ Connected to PostgreSQL: %s", self.db_config.get("database"))
        except Exception:
            logger.exception("Failed to connect to PostgreSQL")
            raise
    
    def get_or_create_stock_id(self, symbol: str) -> Optional[int]:
        """
        Get stock_id from symbol, create if not exists
        
        Args:
            symbol: Stock ticker symbol
            
        Returns:
            int: stock_id or None if error
        """
        if not self.cursor:
            logger.error("Database cursor not initialized")
            return None
        
        try:
            # Check if symbol exists
            self.cursor.execute(
                "SELECT stock_id FROM market_data_oltp.stocks WHERE ticker = %s",
                (symbol,)
            )
            result = self.cursor.fetchone()
            
            if result:
                return result[0]
            
            # Create new stock
            self.cursor.execute(
                """
                INSERT INTO market_data_oltp.stocks (ticker, company_name, status)
                VALUES (%s, %s, 'active')
                ON CONFLICT (ticker) DO UPDATE SET ticker = EXCLUDED.ticker
                RETURNING stock_id
                """,
                (symbol, symbol)
            )
            self.conn.commit()
            stock_id = self.cursor.fetchone()[0]
            logger.debug(f"Created stock_id {stock_id} for symbol {symbol}")
            return stock_id
            
        except Exception as e:
            self.conn.rollback()
            logger.error(f"Error getting stock_id for {symbol}: {e}")
            return None
    
    def batch_insert_trades(self, trades: List[Tuple]) -> bool:
        """
        Batch insert trades into database
        
        Args:
            trades: List of tuples (stock_id, ts, price, size)
            
        Returns:
            bool: True if successful
        """
        if not trades or not self.cursor:
            return False
        
        try:
            execute_batch(
                self.cursor,
                """
                INSERT INTO market_data_oltp.stock_trades_realtime 
                (stock_id, ts, price, size)
                VALUES (%s, %s, %s, %s)
                ON CONFLICT DO NOTHING
                """,
                trades
            )
            self.conn.commit()
            logger.info(f"✓ Inserted {len(trades)} trades into database")
            return True
        except Exception as e:
            self.conn.rollback()
            logger.error(f"Error batch inserting trades: {e}")
            return False
    
    def batch_insert_bars(self, bars: List[Tuple]) -> bool:
        """
        Batch insert bars into database
        
        Args:
            bars: List of tuples (stock_id, timeframe, ts, open, high, low, close, volume, trade_count, vwap)
            
        Returns:
            bool: True if successful
        """
        if not bars or not self.cursor:
            return False
        
        try:
            execute_batch(
                self.cursor,
                """
                INSERT INTO market_data_oltp.stock_bars_staging 
                (stock_id, timeframe, ts, open_price, high_price, low_price, 
                 close_price, volume, trade_count, vwap)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (stock_id, ts, timeframe) DO NOTHING
                """,
                bars
            )
            self.conn.commit()
            logger.info(f"✓ Inserted {len(bars)} bars into database")
            return True
        except Exception as e:
            self.conn.rollback()
            logger.error(f"Error batch inserting bars: {e}")
            return False
    
    def close(self):
        """Close database connection"""
        if self.cursor:
            self.cursor.close()
        if self.conn:
            self.conn.close()
        logger.info("Database connection closed")

