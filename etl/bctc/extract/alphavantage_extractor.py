"""
AlphaVantage Extractor
Calls AlphaVantage API to fetch financial statement data
Returns raw JSON/dict responses
"""

import logging
from typing import Dict, Any, Optional, List

from etl.common.clients.alpha_vantage import AlphaVantageClient

logger = logging.getLogger(__name__)


def get_client(api_key: str) -> AlphaVantageClient:
    return AlphaVantageClient(api_key)


def extract_financial_statements(
    symbol: str,
    statement_code: str,
    client: AlphaVantageClient,
) -> Optional[Dict[str, Any]]:
    return client.fetch_statement(symbol, statement_code)


def extract_all_statements(
    symbol: str,
    client: AlphaVantageClient,
    statement_codes: Optional[List[str]] = None,
) -> Dict[str, Optional[Dict[str, Any]]]:
    return client.fetch_statements(symbol, statement_codes)

