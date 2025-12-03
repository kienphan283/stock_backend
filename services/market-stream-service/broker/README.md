# Broker Layer

This folder is part of Stage 1 cleanup.

Its role is documented to avoid confusion during refactor phases.

## Purpose

The `broker/` folder contains Kafka consumer and message processing logic.

Currently contains:
- `consumer.py` - `KafkaMessageConsumer` class that consumes from Kafka topics
- `processor.py` - `MessageProcessor` class that routes messages to database writers

## Status

This folder contains the active Kafka integration logic. The `infrastructure/kafka/consumer.py` file re-exports the consumer for cleaner imports.

