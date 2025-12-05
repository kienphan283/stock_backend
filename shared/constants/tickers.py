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
    "BRK-B",  # giữ đúng format đang dùng trong DB/ETL
    "JNJ",
    "JPM",
    "IBM",

    # Thêm 10–20 mã mới:
    "V",
    "WMT",
    "PG",
    "MA",
    "XOM",
    "UNH",
    "HD",
    "COST",
    "BAC",
    "KO",
    "PEP",
    "DIS",
    "CSCO",
    "ABT",
    "AVGO",
    "ORCL",
    "TSM",
    "CRM",
    "NFLX",
]

# Default companies (same as tickers for US stocks)
DEFAULT_COMPANIES = DEFAULT_TICKERS.copy()

