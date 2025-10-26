# ETL Pipelines

Extract, Transform, Load pipelines for data processing.

## Structure
```
etl/
├── pipelines/          # ETL pipeline scripts
├── processors/         # Data processors
├── schedulers/         # Cron jobs & schedulers
├── tests/              # Tests
└── README.md
```

## Pipelines

### Stock Data Pipeline
- Fetches stock data from external APIs
- Transforms and validates data
- Loads into PostgreSQL

### Financial Data Pipeline
- Extracts financial statements
- Transforms to common format
- Loads into database

### Dividend Data Pipeline
- Fetches dividend information
- Processes and stores

## Running Pipelines

### Manual run
```bash
python pipelines/stock_data_pipeline.py
```

### Scheduled run
```bash
python schedulers/cron_jobs.py
```
