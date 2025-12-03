## Market Stream Service

### Purpose and Responsibilities

- **Role**: Realtime stream processor and batch ETL runner.
- **Responsibilities**:
  - Consume normalized trade/bar messages from Kafka.
  - Write trades and bars into Postgres (`market_data_oltp` tables).
  - Publish processed events into Redis Streams for consumption by `gateway-service`.
  - Run batch ETL pipelines (BCTC / EOD) on a schedule.

### Runtime Dependencies

- **Inbound**:
  - Kafka topics (see `shared/realtime/kafka_topics.py`):
    - `stock_trades_realtime`
    - `stock_bars_staging`
- **Outbound**:
  - Postgres database (via `db/writer.DatabaseWriter`).
  - Redis (via `infrastructure/redis/publisher.RedisStreamsPublisher`).
- **Batch ETL**:
  - Uses ETL helpers under `etl/` to import financial statements and EOD prices into Postgres.

### Data Flow

- **Realtime path**:
  - `market-ingest-service (Kafka producer) → Kafka → KafkaMessageConsumer (infrastructure/kafka/consumer.py) → MessageProcessor (application/processors/message_processor.py) → DatabaseWriter (db/writer.py) → Postgres`
  - After DB write, messages are published to Redis Streams:
    - `infrastructure/redis/publisher.RedisStreamsPublisher` uses stream keys from `shared/realtime/redis_streams.py`.
  - `gateway-service` subscribes to these Redis Streams and pushes events to WebSocket clients`.
- **Batch ETL path**:
  - `scheduler.ETLJobScheduler` triggers BCTC and EOD pipelines under `etl/` at configured times.
  - `etl/runner.py` provides a CLI entrypoint to run pipelines on demand.

### Service Boundary Rules

- **MUST**:
  - Be the only component that bridges Kafka → Postgres → Redis Streams for realtime events.
  - Own ETL execution for BCTC/EOD within this project.
- **MUST NOT**:
  - Expose HTTP or WebSocket endpoints directly.
  - Talk to external Alpaca APIs (handled by `market-ingest-service`).

### Shared Components Used

- Uses `shared/realtime/kafka_topics.py` for Kafka topic names.
- Uses `shared/realtime/redis_streams.py` for Redis Streams configuration.
- Uses `shared/constants/tickers.py` and `shared/python/db/connector.py` indirectly through the ETL pipelines under `etl/`.

### Domain and Application Layers

- The `domain/` package currently contains high-level documentation for a future domain-driven design extraction.
- The `application/services/event_router.py` provides an application-layer alias around the existing `MessageProcessor` without changing behavior.


