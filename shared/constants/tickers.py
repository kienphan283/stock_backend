"""
Default ticker symbols used across services.

NOTE: This module is used by ETL pipelines in `services/market-stream-service/etl`
to decide which companies/tickers to process by default. Changing this list only
affects batch ETL, not the runtime ingest/streaming pipeline.
"""

# Default US stock tickers for ETL pipelines
DEFAULT_TICKERS = [
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

# Default companies (same as tickers for US stocks)
DEFAULT_COMPANIES = DEFAULT_TICKERS.copy()

