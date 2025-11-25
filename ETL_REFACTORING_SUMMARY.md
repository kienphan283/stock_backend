# ETL Architecture Refactoring Summary

## Overview

The ETL system has been refactored into a clean, domain-based architecture. The financial statements (BCTC) domain has been extracted from FastAPI and organized into a modular pipeline structure.

## New Folder Structure

```
etl/
├── bctc/                          # Financial Statements Domain
│   ├── __init__.py
│   ├── README.md
│   ├── extract/                   # AlphaVantage API Integration
│   │   ├── __init__.py
│   │   └── alphavantage_extractor.py
│   ├── transform/                 # Data Normalization
│   │   ├── __init__.py
│   │   └── financial_transformer.py
│   ├── load/                      # Database Operations
│   │   ├── __init__.py
│   │   └── database_loader.py
│   └── pipeline.py               # Pipeline Orchestrator
├── runner.py                      # CLI Entry Point
├── requirements.txt               # Updated with 'requests'
└── kafka/                         # Existing Kafka code (unchanged)
```

## Key Components

### 1. Extract Module (`bctc/extract/`)

**Purpose:** Handles AlphaVantage API calls

**Key Functions:**
- `extract_financial_statements(symbol, statement_code, api_key)`: Fetches raw data from AlphaVantage
- `extract_all_statements(symbol, api_key)`: Fetches all statement types (IS, BS, CF)

**Features:**
- Error handling for API failures
- Rate limiting awareness
- Returns raw JSON/dict responses

### 2. Transform Module (`bctc/transform/`)

**Purpose:** Normalizes and maps AlphaVantage data to database schema

**Key Functions:**
- `normalize_item_name(name)`: Converts camelCase to Title Case
- `parse_fiscal_date(fiscal_date)`: Extracts year and quarter
- `transform_quarterly_report(report, statement_code)`: Transforms single report
- `transform_all_quarterly_reports(api_response, statement_code)`: Processes all quarters

**Features:**
- Field name normalization
- Date parsing and quarter calculation
- Filters out non-numeric values
- Handles up to 20 most recent quarters

### 3. Load Module (`bctc/load/`)

**Purpose:** Database operations and batch inserts

**Key Class:** `DatabaseLoader`

**Key Methods:**
- `ensure_company(symbol)`: Creates company record if needed
- `get_statement_type_id(statement_code)`: Gets statement type ID
- `upsert_financial_statement(...)`: Inserts/updates statement record
- `batch_insert_financial_line_items(...)`: Batch inserts line items
- `load_quarterly_report(...)`: Complete load operation for one quarter

**Features:**
- Connection management
- UPSERT logic (ON CONFLICT DO NOTHING/UPDATE)
- Batch inserts for performance
- Transaction management

### 4. Pipeline (`bctc/pipeline.py`)

**Purpose:** Orchestrates Extract → Transform → Load

**Key Class:** `BCTCPipeline`

**Key Method:** `run(symbol, statement_codes)`

**Flow:**
1. Extract data from AlphaVantage API
2. Transform to database format
3. Load into PostgreSQL
4. Return results with statistics

### 5. Runner (`etl/runner.py`)

**Purpose:** CLI entry point for running pipelines

**Usage:**
```bash
python etl/runner.py bctc --symbol MSFT
python etl/runner.py bctc --symbol AAPL --statements IS BS
```

## Migration from FastAPI

### Code Reused

The following logic was extracted and refactored from `fastapi-server/services/data.py`:

1. **AlphaVantage API calls** → `bctc/extract/alphavantage_extractor.py`
2. **Field name normalization** → `bctc/transform/financial_transformer.py`
3. **Database operations** → `bctc/load/database_loader.py`
4. **Quarter calculation** → `bctc/transform/financial_transformer.py`

### Improvements

1. **Separation of Concerns:** Extract, Transform, Load are now isolated modules
2. **Error Handling:** Better error handling and logging at each stage
3. **Testability:** Each module can be tested independently
4. **Reusability:** Pipeline can be used from CLI or imported as a library
5. **Documentation:** Clear module structure with README

## Database Schema (Unchanged)

The refactoring maintains compatibility with existing PostgreSQL schema:

- `financial_oltp.company`
- `financial_oltp.statement_type`
- `financial_oltp.financial_statement`
- `financial_oltp.financial_line_item`
- `financial_oltp.line_item_dictionary`

## Environment Variables

Canonical environment variables:

- `ALPHA_VANTAGE_API_KEY` (required)
- `POSTGRES_HOST` (default: localhost)
- `POSTGRES_PORT` (default: 5432)
- `POSTGRES_DB` (default: Web_quan_li_danh_muc)
- `POSTGRES_USER` (default: postgres)
- `POSTGRES_PASSWORD` (required)

## Usage Examples

### Command Line

```bash
# Run for MSFT (all statements)
python etl/runner.py bctc --symbol MSFT

# Run for AAPL (only Income Statement)
python etl/runner.py bctc --symbol AAPL --statements IS

# Run for GOOGL (Income Statement and Balance Sheet)
python etl/runner.py bctc --symbol GOOGL --statements IS BS
```

### Python API

```python
from etl.bctc.pipeline import run

# Simple usage (reads from environment)
results = run("MSFT")

# Advanced usage
from etl.bctc.pipeline import BCTCPipeline
import os

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

## Output Format

Pipeline returns a dictionary with results for each statement type:

```python
{
    "IS": {
        "success": True,
        "quarters_processed": 8,
        "line_items_loaded": 120,
        "errors": []
    },
    "BS": {
        "success": True,
        "quarters_processed": 8,
        "line_items_loaded": 95,
        "errors": []
    },
    "CF": {
        "success": True,
        "quarters_processed": 8,
        "line_items_loaded": 80,
        "errors": []
    }
}
```

## Next Steps

1. **Add More Domains:**
   - `candles/` - OHLC bar data
   - `company/` - Company profile data

2. **Scheduling:**
   - Integrate with `etl/schedulers/` for automated runs

3. **Monitoring:**
   - Add metrics and logging for pipeline execution

4. **Testing:**
   - Unit tests for each module
   - Integration tests for full pipeline

## Notes

- Kafka code previously in `etl/kafka/` has been merged into `etl/streaming/`
- FastAPI endpoints continue to work (they read from database)
- No breaking changes to database schema
- Environment variables are centralized in the root `.env` / `.env.example`

