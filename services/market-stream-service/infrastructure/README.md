# Infrastructure Layer

This folder is part of Stage 3 cleanup.

Its role is documented to avoid confusion during refactor phases.

## Purpose

The `infrastructure/` folder contains concrete integrations with external systems used by the market-stream-service.

Currently contains:
- `kafka/consumer.py` - `KafkaMessageConsumer` implementation (Kafka consumer)
- `redis/publisher.py` - `RedisStreamsPublisher` implementation (Redis Streams publisher)

## Status

This folder now holds the active Kafka and Redis implementations that were previously located under `broker/` and `redis_client/`. All behavior is identical; only file locations and imports have changed.

