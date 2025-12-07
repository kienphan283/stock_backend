"""
Unified ETL runner for on-demand batch jobs.

Usage examples:
    python etl/runner.py bctc
    python etl/runner.py eod
    python etl/runner.py financial
    python etl/runner.py all
"""

from __future__ import annotations

import argparse
import sys
import time
from typing import Callable, Dict, List, Optional

from etl.bctc.pipeline import run as run_bctc
from etl.eod.pipeline import run as run_eod
from shared.constants.tickers import DEFAULT_TICKERS


PipelineFunc = Callable[..., None]

SYMBOL_LIST: List[str] = DEFAULT_TICKERS


def parse_args(argv: Optional[List[str]]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run ETL batch pipelines on demand.",
    )
    parser.add_argument(
        "job",
        choices=["bctc", "financial", "eod", "all"],
        help="Pipeline to execute (use 'all' to run every pipeline sequentially).",
    )
    parser.add_argument("--symbol", type=str, help="Ticker symbol to process.")
    parser.add_argument("--date", type=str, help="ISO date (YYYY-MM-DD).")
    parser.add_argument("--limit", type=int, help="Record limit for batch operations.")
    return parser.parse_args(argv)


def execute_bctc(symbol: Optional[str], limit: Optional[int]) -> None:
    print(f"[runner] Running BCTC pipeline (symbol={symbol}, limit={limit})")
    run_bctc(symbol=symbol, limit=limit)


def execute_eod(symbol: Optional[str], date: Optional[str], limit: Optional[int]) -> None:
    print(f"[runner] Running EOD pipeline (symbol={symbol}, date={date}, limit={limit})")
    run_eod(symbol=symbol, date=date, limit=limit)


def main(argv: Optional[List[str]] = None) -> int:
    args = parse_args(argv or sys.argv[1:])

    if args.job == "bctc":
        # If a specific symbol is provided, run only that symbol.
        if args.symbol:
            execute_bctc(args.symbol, args.limit)
        else:
            total = len(SYMBOL_LIST)
            for idx, symbol in enumerate(SYMBOL_LIST, start=1):
                print(f"[runner] Running BCTC pipeline for {symbol} {idx}/{total}")
                execute_bctc(symbol, args.limit)
                # Avoid hitting Alpha Vantage free-tier rate limits
                if idx < total:
                    time.sleep(18)
    elif args.job == "eod":
        execute_eod(args.symbol, args.date, args.limit)
    elif args.job == "financial":
        # Unified financial ETL: overview + statements + EOD for a fixed universe of tickers.
        from shared.python.utils.env import load_env
        from shared.python.utils.logging_config import get_logger
        from shared.python.db.connector import PostgresConnector
        from etl.extract.extract_all import extract_all_financial_data
        from etl.load.load_all import load_company_and_statements
        from etl.bctc.load.database_loader import BCTCDatabaseLoader
        from etl.eod.pipeline import import_eod_prices_for_symbol

        logger = get_logger(__name__)

        api_key = load_env("ALPHA_VANTAGE_API_KEY")
        db_password = load_env("DB_PASSWORD")
        if not api_key or not db_password:
            raise SystemExit("ALPHA_VANTAGE_API_KEY and DB_PASSWORD are required for financial ETL")

        symbols = DEFAULT_TICKERS

        logger.info("[runner] Running unified FINANCIAL ETL for symbols: %s", symbols)

        db_config = {
            "host": load_env("DB_HOST"),
            "port": int(load_env("DB_PORT", "5432")),
            "dbname": load_env("DB_NAME"),
            "user": load_env("DB_USER"),
            "password": db_password,
        }

        connector = PostgresConnector(config=db_config)
        
        bctc_loader = BCTCDatabaseLoader(db_config)

        for symbol in symbols:
            logger.info("[runner] Extracting all financial data for %s", symbol)
            extracted = extract_all_financial_data(symbol, api_key)

            # Load company + statements
            with bctc_loader._get_connection() as conn:
                load_company_and_statements(
                    bctc_loader,
                    conn,
                    extracted.get("overview") or {},
                    symbol,
                    {
                        "IS": extracted.get("IS", []),
                        "BS": extracted.get("BS", []),
                        "CF": extracted.get("CF", []),
                    },
                )

            # EOD prices: delegate to existing EOD pipeline logic to keep behavior identical
            logger.info("[runner] Importing EOD prices via existing EOD pipeline for %s", symbol)
            import_eod_prices_for_symbol(symbol, conn=None)

            # Avoid hitting Alpha Vantage free-tier rate limits (5 req/min)
            # Each symbol takes ~4 requests (Overview, IS, BS, CF).
            # Sleeping 18s ensures we stay safe.
            time.sleep(18)
    elif args.job == "all":
        execute_bctc(args.symbol, args.limit)
        execute_eod(args.symbol, args.date, args.limit)
    else:
        print(f"[runner] Unknown job '{args.job}'")
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

