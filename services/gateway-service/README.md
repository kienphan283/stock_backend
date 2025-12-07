## Gateway Service

### Purpose and Responsibilities

- **Role**: HTTP + WebSocket edge gateway for the stock analytics system.
- **Responsibilities**:
  - Expose a REST API that proxies requests to `market-api-service` without adding business logic.
  - Manage WebSocket connections (Socket.IO) for realtime updates to frontend clients.
  - Bridge Redis Streams events into WebSocket events for subscribed clients.

### Runtime Dependencies

- **Inbound**:
  - HTTP requests from frontend clients.
  - WebSocket connections from frontend clients.
- **Outbound**:
  - HTTP proxy calls to `market-api-service` (`MARKET_API_URL`).
  - Redis connection for consuming Redis Streams (via `src/infrastructure/redis/redisClient.ts`).
- **Infra**:
  - Depends on Redis (for Redis Streams), but **does not access Postgres or Kafka directly**.

### Data Flow

- **REST path**:
  - `frontend → gateway-service (/api/*) → market-api-service (FastAPI) → Postgres`
  - Gateway validates / normalizes requests and forwards them; responses are passed back unchanged.
- **Realtime path**:
  - `market-stream-service → Redis Streams → gateway-service (Redis consumer) → Socket.IO → frontend`
  - `RedisWebSocketBridge` listens on configured Redis Streams and emits `trade_update` / `bar_update` events to clients, including symbol-specific rooms.

### Service Boundary Rules

- **MUST NOT**:
  - Query Postgres directly.
  - Talk to Kafka directly.
  - Implement business rules that belong in `market-api-service` or ETL services.
- **MUST**:
  - Act only as a thin gateway / facade over backend services and Redis Streams.

### Shared Components Used

- Uses **shared realtime configuration** conceptually (Redis Streams names documented in `shared/realtime/redis_streams.py`), although current constants are defined locally in TS.
- Relies on `market-api-service` for all market and financial data.


