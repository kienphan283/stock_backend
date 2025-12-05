#!/usr/bin/env python

# LEGACY SYNC ZONE:
# These constants are documentation mirrors for the TypeScript gateway.
# They are NOT used at runtime and must never override the TS definitions.
#
# NOTE: These constants must match the TypeScript mirror in
# `services/gateway-service/src/config/realtime.constants.ts`.

"""
Shared Redis Streams configuration for the realtime pipeline.

There are two levels of naming:
1. Publisher-side streams written by `market-stream-service`.
2. Gateway-side streams / consumer group used by `gateway-service`.

Publisher side:
- `market-stream-service` publishes processed trade/bar events into the
  `TRADES_REDIS_STREAM` and `BARS_REDIS_STREAM` streams.

Gateway side:
- `gateway-service` listens on the gateway-level streams using
  `GATEWAY_STOCK_TRADES_STREAM` and `GATEWAY_STOCK_BARS_STREAM` together with
  the configured consumer group and consumer name.

This file documents the naming conventions so that all services maintain a
consistent contract for Redis Streams.
"""

# Publisher-side Redis Streams used by market-stream-service
TRADES_REDIS_STREAM = "market:realtime:trades"
BARS_REDIS_STREAM = "market:realtime:bars"

# ------------------------------------------------------------------
# Gateway-side Redis Streams & consumer group (as used in gateway-service)
#
# NOTE: The gateway-service (TypeScript) is the source of truth.
# These Python constants MUST mirror the actual gateway constants:
#   market:realtime:trades
#   market:realtime:bars
#
# WARNING:
#   Do NOT import these in runtime path.
#   Gateway does NOT read these constants from Python.
#   They are maintained ONLY to keep shared/realtime consistent.
# ------------------------------------------------------------------
GATEWAY_STOCK_TRADES_STREAM = "market:realtime:trades"
GATEWAY_STOCK_BARS_STREAM = "market:realtime:bars"

GATEWAY_CONSUMER_GROUP = "gateway_stream_consumers"
GATEWAY_CONSUMER_NAME = "gateway-consumer"


