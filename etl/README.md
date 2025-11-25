# ETL Pipelines

Unified Extract → Transform → Load stack for batch (BCTC/EOD) and streaming data.

## Folder Structure

```
etl/
├── common/        # Shared clients, env/config helpers, logging, db utilities
├── bctc/          # Financial statement (AlphaVantage) pipeline: extract/transform/load
├── eod/           # Placeholder for end-of-day price pipeline
├── streaming/     # Real-time Alpaca → Kafka/Redis producers & consumers
├── runner.py      # Modular CLI entrypoint (python etl/runner.py <pipeline>)
└── README.md
```

## Modular Pipelines

| Command | Description |
| --- | --- |
| `python etl/runner.py bctc --symbol MSFT` | Runs the financial statements pipeline using `bctc/pipeline.py` |
| (planned) `python etl/runner.py eod ...` | EOD placeholder for future implementation |

All pipelines share the same helpers in `etl/common/`:

- `common/env_loader.py` – loads the root `.env`
- `common/config.py` – validated DB/API configs
- `common/clients/` – AlphaVantage, Alpaca, Kafka, Redis wrappers
- `common/db.py` – reusable PostgreSQL connector
- `common/logging.py` – single logging configuration

## Streaming Stack

`etl/streaming` hosts the Alpaca WebSocket producer plus Kafka consumers for trades/bars.  
Docker Compose builds these services via the `etl/streaming/Dockerfile.*` files.

## Running BCTC Pipeline

```bash
python etl/runner.py bctc --symbol AAPL --statements IS BS CF
```

Environment requirements (root `.env`):

```
ALPHA_VANTAGE_API_KEY=...
POSTGRES_HOST=...
POSTGRES_PORT=...
POSTGRES_DB=...
POSTGRES_USER=...
POSTGRES_PASSWORD=...
```
