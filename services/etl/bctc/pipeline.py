"""
BCTC pipeline orchestrator.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import List, Optional

from dotenv import load_dotenv

from etl.bctc.extract.alphavantage_extractor import fetch_quarterly_reports
from etl.bctc.load.database_loader import BCTCDatabaseLoader
from etl.eod.pipeline import import_eod_prices_for_symbol


CURRENT_FILE_PATH = Path(__file__).resolve()
ENV_PATH = CURRENT_FILE_PATH.parents[3] / ".env"
if ENV_PATH.exists():
    load_dotenv(ENV_PATH)

API_KEY = os.getenv("ALPHA_VANTAGE_API_KEY")
DB_CONFIG = {
    "host": os.getenv("DB_HOST"),
    "port": os.getenv("DB_PORT"),
    "dbname": os.getenv("DB_NAME"),
    "user": os.getenv("DB_USER"),
    "password": os.getenv("DB_PASSWORD"),
}

DEFAULT_COMPANIES = [
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
]


def run(symbol: Optional[str] = None, limit: Optional[int] = None) -> None:
    if not API_KEY:
        raise ValueError("ALPHA_VANTAGE_API_KEY environment variable is required")
    if not DB_CONFIG["password"]:
        raise ValueError("DB_PASSWORD environment variable is required")

    companies = [symbol.upper()] if symbol else DEFAULT_COMPANIES
    if limit:
        companies = companies[:limit]

    loader = BCTCDatabaseLoader(DB_CONFIG)

    for ticker in companies:
        with loader._get_connection() as conn:
            loader.ensure_company(conn, ticker)
            for code in ["IS", "BS", "CF"]:
                reports = fetch_quarterly_reports(ticker, code, API_KEY)
                loader.load_statement(conn, ticker, code, reports)

            import_eod_prices_for_symbol(ticker, conn=conn)

