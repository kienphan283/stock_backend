## Shared Constants

This package contains cross-service constants that are used by multiple Python
services.

### Tickers (`tickers.py`)

- Defines:
  - `DEFAULT_TICKERS`
  - `DEFAULT_COMPANIES`
- Used primarily by ETL pipelines under `services/market-stream-service/etl`
  to decide which tickers/companies to process by default.
- Changing these values affects batch ETL behaviour but does not change the
runtime ingest pipeline.


