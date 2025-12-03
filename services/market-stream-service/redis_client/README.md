# Redis Client

This folder is part of Stage 1 cleanup.

Its role is documented to avoid confusion during refactor phases.

## Purpose

The `redis_client/` folder contains the actual implementation of the Redis Streams publisher.

Currently contains:
- `publisher.py` - `RedisStreamsPublisher` class that publishes trade/bar messages to Redis Streams

## Status

This is the active implementation. The `infrastructure/redis/publisher.py` file re-exports this module for cleaner imports.

