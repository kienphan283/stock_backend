# Application Layer

This folder is part of Stage 3 cleanup.

Its role is documented to avoid confusion during refactor phases.

## Purpose

The `application/` folder contains application-layer abstractions for the market-stream-service.

Currently contains:
- `services/event_router.py` - Thin wrapper around the message processor for application-layer routing
- `processors/message_processor.py` - Kafka message processor that routes messages to database writers

## Status

This folder reflects an incremental refactor toward a clearer separation between application and infrastructure layers. All business logic remains unchanged; only file locations and imports have been updated.

