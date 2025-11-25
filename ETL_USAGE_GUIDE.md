# ETL Usage Guide

## Quick Start

### Prerequisites

1. **Environment Variables:** Set in `.env` using the canonical names:
   ```bash
   ALPHA_VANTAGE_API_KEY=your_api_key_here
   POSTGRES_HOST=localhost
   POSTGRES_PORT=5432
   POSTGRES_DB=Web_quan_li_danh_muc
   POSTGRES_USER=postgres
   POSTGRES_PASSWORD=your_password
   ```

2. **Dependencies:** Install required packages:
   ```bash
   pip install -r etl/requirements.txt
   ```

### Running the ETL

#### Basic Usage

```bash
# Run BCTC pipeline for MSFT (all statements: IS, BS, CF)
python etl/runner.py bctc --symbol MSFT
```

#### Advanced Usage

```bash
# Run only Income Statement for AAPL
python etl/runner.py bctc --symbol AAPL --statements IS

# Run Income Statement and Balance Sheet for GOOGL
python etl/runner.py bctc --symbol GOOGL --statements IS BS

# Run all statements for multiple symbols (run separately)
python etl/runner.py bctc --symbol MSFT
python etl/runner.py bctc --symbol AAPL
python etl/runner.py bctc --symbol GOOGL
```

## Expected Output

```
2025-01-15 10:30:00 - bctc.pipeline - INFO - Starting BCTC pipeline for MSFT
2025-01-15 10:30:01 - bctc.extract - INFO - Extracting IS data for MSFT from AlphaVantage
2025-01-15 10:30:02 - bctc.extract - INFO - Successfully extracted IS data for MSFT
2025-01-15 10:30:02 - bctc.transform - INFO - Transformed 8 quarterly reports for IS
2025-01-15 10:30:03 - bctc.load - INFO - Inserted 120 line items for statement_id=123
...

============================================================
ETL Pipeline Results for MSFT
============================================================

IS (✓ SUCCESS):
  Quarters processed: 8
  Line items loaded: 120
  Errors: []

BS (✓ SUCCESS):
  Quarters processed: 8
  Line items loaded: 95
  Errors: []

CF (✓ SUCCESS):
  Quarters processed: 8
  Line items loaded: 80
  Errors: []

============================================================
```

## Python API Usage

### Simple Usage

```python
from etl.bctc.pipeline import run

# Run pipeline (reads config from environment)
results = run("MSFT")

# Check results
for statement_code, result in results.items():
    if result["success"]:
        print(f"{statement_code}: {result['quarters_processed']} quarters processed")
    else:
        print(f"{statement_code}: Failed - {result['errors']}")
```

### Advanced Usage

```python
from etl.bctc.pipeline import BCTCPipeline
import os

# Configure database
postgres_password = os.getenv("POSTGRES_PASSWORD")
if not postgres_password:
    raise RuntimeError("POSTGRES_PASSWORD environment variable is required")
db_config = {
    "host": os.getenv("POSTGRES_HOST", "localhost"),
    "port": int(os.getenv("POSTGRES_PORT", "5432")),
    "dbname": os.getenv("POSTGRES_DB", "Web_quan_li_danh_muc"),
    "user": os.getenv("POSTGRES_USER", "postgres"),
    "password": postgres_password
}

# Configure API key
api_key = os.getenv("ALPHA_VANTAGE_API_KEY")

# Create pipeline
pipeline = BCTCPipeline(db_config, api_key)

# Run for specific statements
results = pipeline.run("MSFT", statement_codes=["IS", "BS"])

# Process results
for statement_code, result in results.items():
    print(f"{statement_code}:")
    print(f"  Success: {result['success']}")
    print(f"  Quarters: {result['quarters_processed']}")
    print(f"  Line Items: {result['line_items_loaded']}")
    if result['errors']:
        print(f"  Errors: {result['errors']}")
```

## Troubleshooting

### Common Issues

1. **"ALPHA_VANTAGE_API_KEY environment variable is required"**
   - Solution: Set `ALPHA_VANTAGE_API_KEY` in `.env` or environment

2. **"POSTGRES_PASSWORD environment variable is required"**
   - Solution: Set `POSTGRES_PASSWORD` in `.env` or environment

3. **"No quarterly reports found in API response"**
   - Solution: Check if symbol is valid and AlphaVantage has data for it
   - Some symbols may not have financial data available

4. **Database connection errors**
   - Solution: Verify database is running and credentials are correct
   - Check network connectivity to database host

5. **Import errors**
   - Solution: Ensure you're running from the project root directory
   - Verify all dependencies are installed: `pip install -r etl/requirements.txt`

### Debug Mode

Enable debug logging:

```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

Or set environment variable:

```bash
export PYTHONPATH=.
python etl/runner.py bctc --symbol MSFT
```

## Integration with FastAPI

The FastAPI server continues to work as before. It reads from the database tables that the ETL pipeline populates:

- `financial_oltp.company`
- `financial_oltp.financial_statement`
- `financial_oltp.financial_line_item`

The ETL pipeline and FastAPI are now decoupled:
- **ETL Pipeline:** Writes data to database (batch processing)
- **FastAPI:** Reads data from database (API serving)

## Next Domains

Future domains can be added following the same pattern:

```
etl/
├── candles/          # OHLC bar data
│   ├── extract/
│   ├── transform/
│   ├── load/
│   └── pipeline.py
├── company/          # Company profile data
│   ├── extract/
│   ├── transform/
│   ├── load/
│   └── pipeline.py
└── ...
```

Each domain follows the same Extract → Transform → Load pattern.

