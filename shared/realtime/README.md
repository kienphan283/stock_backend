## Shared Realtime Configuration

This package defines cross-service configuration for the realtime pipeline.

### Kafka Topics

- Defined in `kafka_topics.py`.
- Used by:
  - `market-ingest-service` when publishing normalized trades and bars.
  - `market-stream-service` when consuming from Kafka.
- These constants are the canonical source of Kafka topic names for realtime streaming.

### Redis Streams

- Defined in `redis_streams.py`.
- Publisher side:
  - `market-stream-service` publishes to:
    - `TRADES_REDIS_STREAM`
    - `BARS_REDIS_STREAM`
- Gateway side:
  - `gateway-service` consumes from:
    - `GATEWAY_STOCK_TRADES_STREAM`
    - `GATEWAY_STOCK_BARS_STREAM`
  - Uses `GATEWAY_CONSUMER_GROUP` and `GATEWAY_CONSUMER_NAME` as its consumer group metadata.
- The TypeScript mirror in `services/gateway-service/src/config/realtime.constants.ts`
  must keep values exactly in sync with this module.

### Symbols

- Defined in `symbols.py`.
- Provides shared symbol/ticker defaults, for example:
  - `INGEST_DEFAULT_SYMBOLS` used by `market-ingest-service` via its settings.


