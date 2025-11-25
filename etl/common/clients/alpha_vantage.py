"""
AlphaVantage API client shared across ETL pipelines.
"""
import logging
from typing import Dict, Optional, List

from etl.common.http import get_json

logger = logging.getLogger(__name__)


class AlphaVantageClient:
    STATEMENT_CODE_MAPPING = {
        "IS": "INCOME_STATEMENT",
        "BS": "BALANCE_SHEET",
        "CF": "CASH_FLOW",
    }

    def __init__(self, api_key: str):
        if not api_key:
            raise ValueError("AlphaVantage API key is required")
        self.api_key = api_key

    def _build_url(self, function: str, symbol: str) -> str:
        return (
            "https://www.alphavantage.co/query"
            f"?function={function}&symbol={symbol}&apikey={self.api_key}"
        )

    def fetch_statement(self, symbol: str, statement_code: str) -> Optional[Dict]:
        if statement_code not in self.STATEMENT_CODE_MAPPING:
            raise ValueError(
                f"Invalid statement_code: {statement_code}. Expected one of {list(self.STATEMENT_CODE_MAPPING)}"
            )

        function = self.STATEMENT_CODE_MAPPING[statement_code]
        url = self._build_url(function, symbol)
        logger.info("Fetching %s data for %s from AlphaVantage", statement_code, symbol)

        data = get_json(url)

        if "Error Message" in data:
            logger.error("AlphaVantage error for %s %s: %s", symbol, statement_code, data["Error Message"])
            return None

        if "Note" in data:
            logger.warning("AlphaVantage throttled request for %s %s: %s", symbol, statement_code, data["Note"])
            return None

        if "quarterlyReports" not in data:
            logger.warning("No quarterly reports for %s %s", symbol, statement_code)
            return None

        return data

    def fetch_statements(self, symbol: str, statement_codes: Optional[List[str]] = None) -> Dict[str, Optional[Dict]]:
        codes = statement_codes or list(self.STATEMENT_CODE_MAPPING.keys())
        results: Dict[str, Optional[Dict]] = {}

        for code in codes:
            try:
                results[code] = self.fetch_statement(symbol, code)
            except Exception as exc:
                logger.exception("Failed to fetch %s for %s: %s", code, symbol, exc)
                results[code] = None

        return results

