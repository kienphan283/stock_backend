# BCTC Domain - Financial Statements ETL

Domain-based ETL pipeline for extracting, transforming, and loading financial statement data from AlphaVantage API into PostgreSQL.

## Architecture

```
bctc/
├── extract/          # AlphaVantage API integration
├── transform/        # Data normalization and mapping
├── load/            # Database operations
└── pipeline.py      # Pipeline orchestrator
```

## Usage

### Command Line

```bash
# Run pipeline for a single symbol (all statements)
python etl/runner.py bctc --symbol MSFT

# Run pipeline for specific statements only
python etl/runner.py bctc --symbol AAPL --statements IS BS

# Run only Income Statement
python etl/runner.py bctc --symbol GOOGL --statements IS
```

### Python API

```python
import os
from etl.bctc.pipeline import run

# Run pipeline (reads config from environment)
results = run("MSFT")

# Or with explicit configuration
from etl.bctc.pipeline import BCTCPipeline

db_config = {
    "host": os.getenv("POSTGRES_HOST", "localhost"),
    "port": int(os.getenv("POSTGRES_PORT", "5432")),
    "dbname": os.getenv("POSTGRES_DB", "Web_quan_li_danh_muc"),
    "user": os.getenv("POSTGRES_USER", "postgres"),
    "password": os.getenv("POSTGRES_PASSWORD")
}

pipeline = BCTCPipeline(db_config, api_key="your_api_key")
results = pipeline.run("MSFT", statement_codes=["IS", "BS", "CF"])
```

## Environment Variables

Required environment variables:

- `ALPHA_VANTAGE_API_KEY`: AlphaVantage API key
- `POSTGRES_HOST`: PostgreSQL host (default: localhost)
- `POSTGRES_PORT`: PostgreSQL port (default: 5432)
- `POSTGRES_DB`: Database name (default: Web_quan_li_danh_muc)
- `POSTGRES_USER`: Database user (default: postgres)
- `POSTGRES_PASSWORD`: Database password (required)

## Pipeline Flow

1. **Extract**: Calls AlphaVantage API to fetch financial statements
2. **Transform**: Normalizes field names and maps to database schema
3. **Load**: Upserts data into PostgreSQL tables:
   - `financial_oltp.company`
   - `financial_oltp.financial_statement`
   - `financial_oltp.financial_line_item`
   - `financial_oltp.line_item_dictionary`

## Statement Types

- **IS**: Income Statement
- **BS**: Balance Sheet
- **CF**: Cash Flow Statement

## Data Processing

- Processes up to 20 most recent quarterly reports
- Only inserts when `(statement_id, item_code)` combination doesn't exist
- Updates existing records if needed (UPSERT behavior)
- Normalizes AlphaVantage field names to human-readable format

## Output

Pipeline returns a dictionary with results for each statement type:

```python
{
    "IS": {
        "success": True,
        "quarters_processed": 8,
        "line_items_loaded": 120,
        "errors": []
    },
    "BS": {...},
    "CF": {...}
}
```

