## Market API Service

### Purpose and Responsibilities

- **Role**: Core HTTP API that exposes market data, financial statements, EOD prices, and related analytics.
- **Responsibilities**:
  - Serve REST endpoints for quotes, profiles, price history, candles, dividends, earnings, financials, companies, refresh, and summary.
  - Orchestrate repository calls into Postgres and, where applicable, Redis-based caching.
  - Provide a stable API consumed by `gateway-service` and any other HTTP clients.

### Runtime Dependencies

- **Inbound**:
  - HTTP requests from `gateway-service` and other HTTP clients.
- **Outbound**:
  - Postgres database (via repository modules under `db/`).
  - Redis (via `core/redis_client.RedisClient`) for caching in selected services.
  - External data sources as configured (e.g. Alpha Vantage, Finnhub) when refreshing data.

### Data Flow

- `frontend → gateway-service (/api/*) → market-api-service (routers → services → db repos) → Postgres / Redis`
- **Routers** under `api/routers/` define URL structure and map to service classes in `services/`.
- **Services** encapsulate business logic and call repositories in `db/` and optional helpers in `data_loaders/`.
- **Data loader** (`data_loaders/data_loader.py`) is still used at runtime by several services for CSV-backed or mock data.

### Service Boundary Rules

- **MUST**:
  - Own the HTTP API contract for market and financial data.
  - Be the only service that talks directly to the **financial** and **market** schemas for API use-cases.
- **MUST NOT**:
  - Consume Kafka topics directly.
  - Consume Redis Streams used for realtime WebSocket broadcasting (those belong to `market-stream-service` and `gateway-service`).
  - Implement Alpaca WebSocket ingestion (owned by `market-ingest-service`).

### Shared Components Used

- Conceptually aligned with:
  - `shared/constants/tickers.py` and ETL pipelines that populate the underlying Postgres schemas.
  - Realtime configuration under `shared/realtime` for topic and stream naming (used indirectly via other services).


