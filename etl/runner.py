#!/usr/bin/env python3
"""
ETL Runner - CLI Entry Point
Command-line interface for running ETL pipelines
"""

import argparse
import logging
import sys
from pathlib import Path

from common.config import get_alpha_vantage_key, get_db_config
from common.env_loader import load_root_env
from common.logging import configure_logging

# Add etl directory to Python path for imports
CURRENT_FILE_PATH = Path(__file__).resolve()
ETL_DIR = CURRENT_FILE_PATH.parent
if str(ETL_DIR) not in sys.path:
    sys.path.insert(0, str(ETL_DIR))

# Load environment variables from repository root
load_root_env()

configure_logging()
logger = logging.getLogger(__name__)


def pipeline_bctc(symbol: str, statement_codes: list | None = None):
    from bctc.pipeline import BCTCPipeline

    db_config = get_db_config()
    api_key = get_alpha_vantage_key()
    pipeline = BCTCPipeline(db_config, api_key)
    return pipeline.run(symbol, statement_codes)


def run_bctc_pipeline(symbol: str, statement_codes: list | None = None):
    """
    Run BCTC (financial statements) pipeline
    
    Args:
        symbol: Stock ticker symbol
        statement_codes: List of statement codes to process (default: ["IS", "BS", "CF"])
    """
    try:
        results = pipeline_bctc(symbol, statement_codes)
        
        # Print results
        print("\n" + "=" * 60)
        print(f"ETL Pipeline Results for {symbol}")
        print("=" * 60)
        
        for statement_code, result in results.items():
            status = "✓ SUCCESS" if result["success"] else "✗ FAILED"
            print(f"\n{statement_code} ({status}):")
            print(f"  Quarters processed: {result['quarters_processed']}")
            print(f"  Line items loaded: {result['line_items_loaded']}")
            
            if result["errors"]:
                print(f"  Errors ({len(result['errors'])}):")
                for error in result["errors"][:5]:  # Show first 5 errors
                    print(f"    - {error}")
                if len(result["errors"]) > 5:
                    print(f"    ... and {len(result['errors']) - 5} more errors")
        
        print("\n" + "=" * 60)
        
        # Exit with error code if any statement failed
        if any(not r["success"] for r in results.values()):
            sys.exit(1)
        
    except Exception as e:
        logger.error(f"Pipeline failed: {e}", exc_info=True)
        sys.exit(1)


def main():
    """Main CLI entry point"""
    parser = argparse.ArgumentParser(
        description="ETL Pipeline Runner",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Run BCTC pipeline for MSFT (all statements)
  python etl/runner.py bctc --symbol MSFT
  
  # Run BCTC pipeline for AAPL (only Income Statement)
  python etl/runner.py bctc --symbol AAPL --statements IS
  
  # Run BCTC pipeline for GOOGL (Income Statement and Balance Sheet)
  python etl/runner.py bctc --symbol GOOGL --statements IS BS
        """
    )
    
    subparsers = parser.add_subparsers(dest="domain", help="ETL domain to run")
    subparsers.required = True
    
    # BCTC subcommand
    bctc_parser = subparsers.add_parser(
        "bctc",
        help="Run BCTC (financial statements) pipeline"
    )
    bctc_parser.add_argument(
        "--symbol",
        type=str,
        required=True,
        help="Stock ticker symbol (e.g., MSFT, AAPL, GOOGL)"
    )
    bctc_parser.add_argument(
        "--statements",
        nargs="+",
        choices=["IS", "BS", "CF"],
        default=["IS", "BS", "CF"],
        help="Statement types to process (default: all)"
    )
    
    args = parser.parse_args()
    
    pipeline_registry = {
        "bctc": lambda args: run_bctc_pipeline(args.symbol, args.statements),
        # Future domains (eod, streaming) can be registered here
    }

    handler = pipeline_registry.get(args.domain)
    if not handler:
        parser.error(f"Unknown domain: {args.domain}")
    handler(args)


if __name__ == "__main__":
    main()

