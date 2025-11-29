"""
End-of-day price pipeline.
"""

from __future__ import annotations

import argparse
import logging
import os
from pathlib import Path
from typing import Iterable, List, Optional, Sequence, Tuple

from dotenv import load_dotenv

from etl.common.db import PostgresConnector
from etl.eod.extract.yahoo_extractor import download_price_history
from etl.eod.load.db_loader import EODLoader
from etl.eod.transform.price_transformer import filter_by_start_date, prepare_records

logger = logging.getLogger(__name__)

CURRENT_FILE_PATH = Path(__file__).resolve()
ENV_PATH = CURRENT_FILE_PATH.parents[3] / ".env"
if ENV_PATH.exists():
    load_dotenv(ENV_PATH)

DB_CONFIG = {
    "host": os.getenv("DB_HOST", "localhost"),
    "port": os.getenv("DB_PORT", "5432"),
    "dbname": os.getenv("DB_NAME", "Web_quan_li_danh_muc"),
    "user": os.getenv("DB_USER", "postgres"),
    "password": os.getenv("DB_PASSWORD"),
}

if not DB_CONFIG["password"]:
    raise ValueError("DB_PASSWORD environment variable is required")

DEFAULT_TICKERS: Sequence[str] = (
    "AAPL",
    "MSFT",
    "GOOGL",
    "AMZN",
    "NVDA",
    "META",
    "TSLA",
    "BRK-B",
    "JNJ",
    "JPM",
    "IBM",
)


connector = PostgresConnector(DB_CONFIG)
loader = EODLoader(connector)


def import_eod_prices_for_symbol(
    ticker: str,
    *,
    years: int = 5,
    start_date: Optional[str] = None,
    conn=None,
) -> int:
    ticker = ticker.upper()
    managed_connection = False
    if conn is None:
        conn = connector.get_connection()
        managed_connection = True

    try:
        with conn.cursor() as cursor:
            loader.ensure_company(cursor, ticker)
            stock_id = loader.ensure_stock(cursor, ticker)
            df = download_price_history(ticker, years)
            df = filter_by_start_date(df, start_date)
            records = prepare_records(stock_id, df)
            inserted = loader.upsert_eod_prices(cursor, records)
            conn.commit()
            logger.info(
                "Imported %s EOD records for %s (stock_id=%s)",
                inserted,
                ticker,
                stock_id,
            )
            return inserted
    except Exception:
        conn.rollback()
        logger.exception("Failed to import EOD prices for %s", ticker)
        raise
    finally:
        if managed_connection:
            conn.close()


def import_eod_prices_for_companies(
    tickers: Iterable[str],
    *,
    years: int = 5,
    start_date: Optional[str] = None,
) -> int:
    tickers = [ticker.upper() for ticker in tickers]
    if not tickers:
        return 0

    total_inserted = 0
    conn = connector.get_connection()

    try:
        for ticker in tickers:
            inserted = import_eod_prices_for_symbol(
                ticker,
                years=years,
                start_date=start_date,
                conn=conn,
            )
            total_inserted += inserted
    finally:
        conn.close()

    return total_inserted


def import_prices_for_all_companies(
    *,
    years: int = 5,
    fallback_tickers: Optional[Sequence[str]] = None,
    limit: Optional[int] = None,
    start_date: Optional[str] = None,
) -> Tuple[List[str], int]:
    fallback_list = [ticker.upper() for ticker in (fallback_tickers or DEFAULT_TICKERS)]

    conn = connector.get_connection()

    try:
        with conn.cursor() as cursor:
            tickers = loader.fetch_all_company_tickers(cursor)
            if not tickers:
                tickers = list(fallback_list)
                logger.info(
                    "No tickers found in financial_oltp.company; using fallback list: %s",
                    ", ".join(tickers),
                )

        if limit:
            tickers = tickers[:limit]

        processed: List[str] = []
        total_inserted = 0
        for ticker in tickers:
            try:
                inserted = import_eod_prices_for_symbol(
                    ticker,
                    years=years,
                    start_date=start_date,
                    conn=conn,
                )
                total_inserted += inserted
                processed.append(ticker)
            except Exception as exc:
                logger.error("Skipping %s due to error: %s", ticker, exc)

        return processed, total_inserted
    finally:
        conn.close()


def run(symbol: Optional[str] = None, date: Optional[str] = None, limit: Optional[int] = None) -> None:
    """Entry point used by the unified runner."""
    if symbol:
        import_eod_prices_for_symbol(symbol.upper(), start_date=date)
    else:
        import_prices_for_all_companies(start_date=date, limit=limit)


def main(argv: Optional[List[str]] = None) -> None:
    parser = argparse.ArgumentParser(description="Import EOD stock prices")
    parser.add_argument(
        "--tickers",
        nargs="*",
        help="List of ticker symbols. If omitted, all companies in the database are used.",
    )
    parser.add_argument(
        "--years",
        type=int,
        default=5,
        help="Number of years of historical data to download (default: 5)",
    )
    parser.add_argument(
        "--start-date",
        type=str,
        help="ISO date to filter price history (inclusive).",
    )
    parser.add_argument(
        "--limit",
        type=int,
        help="Limit number of tickers when importing all companies.",
    )

    args = parser.parse_args(argv)

    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

    if args.tickers:
        tickers = [ticker.upper() for ticker in args.tickers]
        total = import_eod_prices_for_companies(
            tickers,
            years=args.years,
            start_date=args.start_date,
        )
        logger.info(
            "Completed EOD import for provided tickers (%s). Total records processed: %s",
            ", ".join(tickers),
            total,
        )
    else:
        processed, total = import_prices_for_all_companies(
            years=args.years,
            fallback_tickers=DEFAULT_TICKERS,
             limit=args.limit,
             start_date=args.start_date,
        )
        logger.info(
            "Completed EOD import for %s tickers. Total records processed: %s",
            len(processed),
            total,
        )


if __name__ == "__main__":
    main()

