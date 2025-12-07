## Shared Python Infrastructure

This package contains reusable, Python-specific infrastructure helpers that can
be safely shared across services.

### Database Connector (`db/connector.py`)

- Provides `PostgresConnector`, a unified way for Python services to obtain
  PostgreSQL connections (and optionally use a connection pool).
- Used by:
  - ETL pipelines under `services/market-stream-service/etl/common`.
  - Realtime `DatabaseWriter` under `services/market-stream-service/db/writer.py`.

### Redis Client (`redis/client.py`)

- Provides `get_redis_connection(...)`, a thin factory that wraps `redis.Redis`.
- Used by:
  - `services/market-stream-service/redis_client/publisher.RedisStreamsPublisher`.
  - `services/market-api-service/core/redis_client.RedisClient`.
- Services pass through their existing connection parameters, so behaviour
  remains unchanged.


