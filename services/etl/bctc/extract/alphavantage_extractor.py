"""
Alpha Vantage extraction helpers for BCTC ETL.
"""

from __future__ import annotations

import logging
from typing import Dict, List

import requests

logger = logging.getLogger(__name__)


def fetch_quarterly_reports(symbol: str, statement_code: str, api_key: str) -> List[Dict]:
    """
    Fetch quarterly financial reports for a symbol/statement_code pair.

    Returns the 20 most recent quarterly reports (if available).
    """
    mapping = {
        "IS": "INCOME_STATEMENT",
        "BS": "BALANCE_SHEET",
        "CF": "CASH_FLOW",
    }
    if statement_code not in mapping:
        raise ValueError("statement_code must be 'IS', 'BS', or 'CF'")

    api_function = mapping[statement_code]
    url = (
        "https://www.alphavantage.co/query"
        f"?function={api_function}&symbol={symbol}&apikey={api_key}"
    )

    logger.info("Requesting %s data for %s", statement_code, symbol)
    response = requests.get(url, timeout=30)
    response.raise_for_status()
    data = response.json()

    reports = data.get("quarterlyReports", [])
    reports = sorted(
        reports,
        key=lambda item: item.get("fiscalDateEnding", "") or "",
        reverse=True,
    )
    return reports[:20]

