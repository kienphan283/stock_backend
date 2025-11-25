"""
BCTC Pipeline - Orchestrates Extract, Transform, Load
Main pipeline orchestrator for financial statements ETL
"""

import logging
import os
from typing import Dict, Any, Optional

from common.env_loader import load_root_env

load_root_env()

from .extract import extract_financial_statements, get_client
from .transform import transform_all_quarterly_reports
from .load import DatabaseLoader

logger = logging.getLogger(__name__)


class BCTCPipeline:
    """Pipeline for extracting, transforming, and loading financial statement data"""
    
    def __init__(self, db_config: Dict[str, Any], api_key: str):
        """
        Initialize pipeline
        
        Args:
            db_config: Database configuration dictionary
            api_key: AlphaVantage API key
        """
        self.db_config = db_config
        self.loader = DatabaseLoader(db_config)
        self.alpha_client = get_client(api_key)
    
    def run(self, symbol: str, statement_codes: Optional[list] = None) -> Dict[str, Any]:
        """
        Run the complete ETL pipeline for a symbol
        
        Args:
            symbol: Stock ticker symbol (e.g., "AAPL", "MSFT")
            statement_codes: List of statement codes to process (default: ["IS", "BS", "CF"])
            
        Returns:
            Dictionary with results for each statement code:
            {
                "IS": {"success": bool, "quarters_processed": int, "errors": [...]},
                "BS": {...},
                "CF": {...}
            }
        """
        if statement_codes is None:
            statement_codes = ["IS", "BS", "CF"]
        
        symbol = symbol.upper()
        logger.info(f"Starting BCTC pipeline for {symbol}")
        
        results = {}
        
        try:
            # Connect to database
            self.loader.connect()
            
            # Process each statement type
            for statement_code in statement_codes:
                logger.info(f"Processing {statement_code} for {symbol}")
                
                result = self._process_statement(symbol, statement_code)
                results[statement_code] = result
            
            logger.info(f"Completed BCTC pipeline for {symbol}")
            
        except Exception as e:
            logger.error(f"Pipeline failed for {symbol}: {e}", exc_info=True)
            raise
        finally:
            self.loader.close()
        
        return results
    
    def _process_statement(
        self,
        symbol: str,
        statement_code: str
    ) -> Dict[str, Any]:
        """
        Process a single statement type (Extract → Transform → Load)
        
        Args:
            symbol: Stock ticker symbol
            statement_code: Statement code ("IS", "BS", or "CF")
            
        Returns:
            Result dictionary with success status and statistics
        """
        result = {
            "success": False,
            "quarters_processed": 0,
            "line_items_loaded": 0,
            "errors": []
        }
        
        try:
            # EXTRACT: Get data from AlphaVantage API
            logger.info(f"Extracting {statement_code} data for {symbol}")
            api_response = extract_financial_statements(
                symbol, statement_code, self.alpha_client
            )
            
            if not api_response:
                result["errors"].append("No data returned from AlphaVantage API")
                return result
            
            # TRANSFORM: Convert API response to database format
            logger.info(f"Transforming {statement_code} data for {symbol}")
            transformed_reports = transform_all_quarterly_reports(api_response, statement_code)
            
            if not transformed_reports:
                result["errors"].append("No quarterly reports found in API response")
                return result
            
            # LOAD: Insert into database
            logger.info(f"Loading {statement_code} data for {symbol} into database")
            quarters_processed = 0
            total_line_items = 0
            
            for statement_metadata, line_items in transformed_reports:
                success = self.loader.load_quarterly_report(
                    company_id=symbol,
                    statement_code=statement_code,
                    statement_metadata=statement_metadata,
                    line_items=line_items
                )
                
                if success:
                    quarters_processed += 1
                    total_line_items += len(line_items)
                else:
                    result["errors"].append(
                        f"Failed to load {statement_metadata['fiscal_year']} "
                        f"{statement_metadata['fiscal_quarter']}"
                    )
            
            result["success"] = quarters_processed > 0
            result["quarters_processed"] = quarters_processed
            result["line_items_loaded"] = total_line_items
            
            logger.info(
                f"Completed {statement_code} for {symbol}: "
                f"{quarters_processed} quarters, {total_line_items} line items"
            )
            
        except Exception as e:
            error_msg = f"Error processing {statement_code} for {symbol}: {str(e)}"
            logger.error(error_msg, exc_info=True)
            result["errors"].append(error_msg)
        
        return result


def run(symbol: str, db_config: Optional[Dict[str, Any]] = None, api_key: Optional[str] = None) -> Dict[str, Any]:
    """
    Convenience function to run the pipeline
    
    Args:
        symbol: Stock ticker symbol
        db_config: Database configuration (if None, reads from environment)
        api_key: AlphaVantage API key (if None, reads from environment)
        
    Returns:
        Pipeline results dictionary
    """
    # Load configuration from environment if not provided
    if db_config is None:
        postgres_password = os.getenv("POSTGRES_PASSWORD")
        if not postgres_password:
            raise ValueError("POSTGRES_PASSWORD environment variable is required")
        db_config = {
            "host": os.getenv("POSTGRES_HOST", "localhost"),
            "port": int(os.getenv("POSTGRES_PORT", "5432")),
            "dbname": os.getenv("POSTGRES_DB", "Web_quan_li_danh_muc"),
            "user": os.getenv("POSTGRES_USER", "postgres"),
            "password": postgres_password
        }
    
    if api_key is None:
        api_key = os.getenv("ALPHA_VANTAGE_API_KEY")
        if not api_key:
            raise ValueError("ALPHA_VANTAGE_API_KEY environment variable is required")
    
    # Validate password
    if not db_config.get("password"):
            raise ValueError("POSTGRES_PASSWORD environment variable is required")
    
    # Create and run pipeline
    pipeline = BCTCPipeline(db_config, api_key)
    return pipeline.run(symbol)

