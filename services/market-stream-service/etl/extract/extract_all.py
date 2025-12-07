"""
Unified extract helpers for financial data (overview + financial statements + EOD).

This module consolidates the existing extract logic so that a single function can
pull all relevant data for a given symbol.
"""

from __future__ import annotations

from typing import Dict, List

from etl.bctc.extract.alphavantage_extractor import (
    fetch_quarterly_reports,
    fetch_company_overview,
)
from etl.eod.extract.yahoo_extractor import download_price_history


def extract_all_financial_data(symbol: str, api_key: str) -> Dict:
    """
    Extract all relevant financial data for a given symbol from external APIs.

    Returns a dict of the form:
    {
        "symbol": "...",
        "overview": {...},
        "IS": [...],
        "BS": [...],
        "CF": [...],
        "eod": [...]
    }
    """
    symbol = symbol.upper()

    overview: Dict = fetch_company_overview(symbol, api_key)

    statements: Dict[str, List[Dict]] = {}
    for code in ["IS", "BS", "CF"]:
        reports = fetch_quarterly_reports(symbol, code, api_key)
        statements[code] = reports

    # EOD prices from Yahoo-based extractor.
    # This does NOT write to the database; it only returns raw price history.
    try:
        df = download_price_history(symbol, years=5)
        eod_prices = df.to_dict(orient="records")
    except Exception:
        eod_prices = []

    return {
        "symbol": symbol,
        "overview": overview,
        "IS": statements.get("IS", []),
        "BS": statements.get("BS", []),
        "CF": statements.get("CF", []),
        "eod": eod_prices or [],
    }


