"""
Database Loader
Handles database operations for financial statement data
"""

import psycopg2
from psycopg2.extras import execute_values, RealDictCursor
import logging
from typing import Dict, Any, List, Tuple, Optional

from etl.common.db import PostgresConnector

logger = logging.getLogger(__name__)


class DatabaseLoader(PostgresConnector):
    """Database client for loading financial statement data"""
    
    def __init__(self, db_config: Dict[str, Any]):
        """
        Initialize database loader
        
        Args:
            db_config: Database configuration dictionary with keys:
                - host: Database host
                - port: Database port
                - dbname: Database name
                - user: Database user
                - password: Database password
        """
        super().__init__(db_config)
    
    def ensure_company(self, symbol: str) -> None:
        """
        Ensure company exists in financial_oltp.company table
        
        Args:
            symbol: Company ticker symbol
        """
        if not self.conn or self.conn.closed:
            self.connect()
        
        company_name = f"{symbol} Corporation"
        exchange = "NYSE"
        
        with self.conn.cursor() as cur:
            cur.execute("""
                INSERT INTO financial_oltp.company (company_id, company_name, exchange)
                VALUES (%s, %s, %s)
                ON CONFLICT (company_id) DO NOTHING
            """, (symbol, company_name, exchange))
        
        self.conn.commit()
        logger.debug(f"Ensured company {symbol} exists")
        
        # Ensure stock record exists in market_data schema so FastAPI can resolve stock_id
        self.ensure_stock(symbol, company_name, exchange)
    
    def ensure_stock(self, symbol: str, company_name: str, exchange: str) -> None:
        """
        Ensure stock entry exists in market_data_oltp.stocks
        
        Args:
            symbol: Stock ticker symbol
            company_name: Descriptive company name
            exchange: Exchange code (fallback NYSE)
        """
        if not self.conn or self.conn.closed:
            self.connect()
        
        with self.conn.cursor() as cur:
            cur.execute("""
                INSERT INTO market_data_oltp.stocks (
                    company_id,
                    stock_ticker,
                    stock_name,
                    exchange,
                    delisted
                )
                VALUES (%s, %s, %s, %s, FALSE)
                ON CONFLICT (stock_ticker) DO UPDATE
                SET stock_name = EXCLUDED.stock_name,
                    exchange = EXCLUDED.exchange,
                    delisted = EXCLUDED.delisted
            """, (symbol, symbol, company_name, exchange))
        
        self.conn.commit()
        logger.debug(f"Ensured stock {symbol} exists in market_data_oltp.stocks")
    
    def get_statement_type_id(self, statement_code: str) -> int:
        """
        Get statement_type_id for a statement code
        
        Args:
            statement_code: Statement code ("IS", "BS", or "CF")
            
        Returns:
            statement_type_id from database
            
        Raises:
            ValueError: If statement_code not found
        """
        if not self.conn or self.conn.closed:
            self.connect()
        
        with self.conn.cursor() as cur:
            cur.execute("""
                SELECT statement_type_id 
                FROM financial_oltp.statement_type
                WHERE statement_code = %s
            """, (statement_code,))
            
            result = cur.fetchone()
            if not result:
                raise ValueError(f"Statement type '{statement_code}' not found in database")
            
            return result[0]
    
    def upsert_financial_statement(
        self,
        company_id: str,
        statement_type_id: int,
        fiscal_year: int,
        fiscal_quarter: str,
        report_date: str
    ) -> Optional[int]:
        """
        Insert or update financial statement record
        
        Args:
            company_id: Company ticker symbol
            statement_type_id: Statement type ID from database
            fiscal_year: Fiscal year
            fiscal_quarter: Fiscal quarter (e.g., "Q1", "Q2")
            report_date: Report date (YYYY-MM-DD)
            
        Returns:
            statement_id if inserted/updated, None if already exists
        """
        if not self.conn or self.conn.closed:
            self.connect()
        
        with self.conn.cursor() as cur:
            cur.execute("""
                INSERT INTO financial_oltp.financial_statement 
                (company_id, statement_type_id, fiscal_year, fiscal_quarter, report_date)
                VALUES (%s, %s, %s, %s, %s)
                ON CONFLICT (company_id, statement_type_id, fiscal_year, fiscal_quarter)
                DO NOTHING
                RETURNING statement_id
            """, (company_id, statement_type_id, fiscal_year, fiscal_quarter, report_date))
            
            result = cur.fetchone()
            if result:
                statement_id = result[0]
                logger.debug(
                    f"Inserted financial statement: {company_id} {fiscal_year} {fiscal_quarter} "
                    f"(statement_id={statement_id})"
                )
                return statement_id
            else:
                logger.debug(
                    f"Financial statement already exists: {company_id} {fiscal_year} {fiscal_quarter}"
                )
                return None
    
    def upsert_line_item_dictionary(self, item_code: str, item_name: str) -> None:
        """
        Insert or update line item dictionary entry
        
        Args:
            item_code: Item code (original AlphaVantage field name)
            item_name: Normalized item name
        """
        if not self.conn or self.conn.closed:
            self.connect()
        
        with self.conn.cursor() as cur:
            cur.execute("""
                INSERT INTO financial_oltp.line_item_dictionary (item_code, item_name)
                VALUES (%s, %s)
                ON CONFLICT (item_code) DO NOTHING
            """, (item_code, item_name))
        
        self.conn.commit()
        logger.debug(f"Ensured line item dictionary entry: {item_code} -> {item_name}")
    
    def batch_insert_financial_line_items(
        self,
        statement_id: int,
        line_items: List[Tuple[str, str, float, str]]
    ) -> int:
        """
        Batch insert financial line items for a statement
        
        Args:
            statement_id: Statement ID from financial_statement table
            line_items: List of tuples (item_code, item_name, item_value, unit)
            
        Returns:
            Number of items inserted
        """
        if not line_items:
            return 0
        
        if not self.conn or self.conn.closed:
            self.connect()
        
        # First, ensure all line item dictionary entries exist
        filtered_items: List[Tuple[str, str, float, str]] = []
        for item_code, item_name, item_value, unit in line_items:
            if not item_code:
                logger.warning("Skipping line item with empty item_code for statement_id=%s", statement_id)
                continue
            self.upsert_line_item_dictionary(item_code, item_name)
            filtered_items.append((item_code, item_name, item_value, unit))
        
        if not filtered_items:
            logger.info("No valid line items to insert for statement_id=%s", statement_id)
            return 0
        
        # Prepare data for batch insert
        # Format: (statement_id, item_code, item_name, item_value, unit)
        values = [
            (statement_id, item_code, item_name, item_value, unit)
            for item_code, item_name, item_value, unit in filtered_items
        ]
        
        with self.conn.cursor() as cur:
            # Use execute_values for efficient batch insert
            execute_values(
                cur,
                """
                INSERT INTO financial_oltp.financial_line_item
                (statement_id, item_code, item_name, item_value, unit)
                VALUES %s
                ON CONFLICT (statement_id, item_code) DO UPDATE
                SET item_name = EXCLUDED.item_name,
                    item_value = EXCLUDED.item_value,
                    unit = EXCLUDED.unit
                """,
                values,
                page_size=500
            )
        
        self.conn.commit()
        logger.info("Upserted %s line items for statement_id=%s", len(values), statement_id)
        
        return len(values)
    
    def load_quarterly_report(
        self,
        company_id: str,
        statement_code: str,
        statement_metadata: Dict[str, Any],
        line_items: List[Tuple[str, str, float, str]]
    ) -> bool:
        """
        Load a single quarterly report into database
        
        Args:
            company_id: Company ticker symbol
            statement_code: Statement code ("IS", "BS", or "CF")
            statement_metadata: Statement metadata dictionary
            line_items: List of line item tuples
            
        Returns:
            True if loaded successfully, False otherwise
        """
        try:
            # Ensure company exists
            self.ensure_company(company_id)
            
            # Get statement type ID
            statement_type_id = self.get_statement_type_id(statement_code)
            
            # Upsert financial statement
            statement_id = self.upsert_financial_statement(
                company_id=company_id,
                statement_type_id=statement_type_id,
                fiscal_year=statement_metadata["fiscal_year"],
                fiscal_quarter=statement_metadata["fiscal_quarter"],
                report_date=statement_metadata["report_date"]
            )
            
            # If statement already exists, we need to get its ID
            if statement_id is None:
                # Query for existing statement_id
                if not self.conn or self.conn.closed:
                    self.connect()
                
                with self.conn.cursor() as cur:
                    cur.execute("""
                        SELECT statement_id
                        FROM financial_oltp.financial_statement
                        WHERE company_id = %s
                          AND statement_type_id = %s
                          AND fiscal_year = %s
                          AND fiscal_quarter = %s
                    """, (
                        company_id,
                        statement_type_id,
                        statement_metadata["fiscal_year"],
                        statement_metadata["fiscal_quarter"]
                    ))
                    
                    result = cur.fetchone()
                    if result:
                        statement_id = result[0]
                    else:
                        logger.error(f"Failed to get statement_id for {company_id} {statement_code}")
                        return False
            
            # Batch insert line items
            if line_items:
                self.batch_insert_financial_line_items(statement_id, line_items)
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to load quarterly report: {e}", exc_info=True)
            if self.conn:
                self.conn.rollback()
            return False

