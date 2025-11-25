"""
Extract Module - AlphaVantage API Integration
Handles API calls to AlphaVantage for financial statement data
"""

from .alphavantage_extractor import (
    extract_financial_statements,
    extract_all_statements,
    get_client,
)

__all__ = ["extract_financial_statements", "extract_all_statements", "get_client"]

