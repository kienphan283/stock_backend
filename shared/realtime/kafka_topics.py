"""
Shared Kafka topic names for realtime streaming.

These constants are extracted from the existing services and MUST NOT be
changed without updating all producers/consumers.

Usage:
- `market-ingest-service` uses these topics when publishing trades and bars.
- `market-stream-service` subscribes to the same topics when consuming.

This module is the canonical source of Kafka topic names for the realtime
pipeline; services should depend on these values rather than redefining them.
"""

# Realtime trade topic used by market-ingest-service producer and
# market-stream-service consumer.
STOCK_TRADES_TOPIC = "stock_trades_realtime"

# Realtime bar topic (staging) used by market-ingest-service producer and
# market-stream-service consumer.
STOCK_BARS_TOPIC = "stock_bars_staging"


