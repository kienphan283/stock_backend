"""
Redis Streams publisher for market-stream-service.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import redis

from config.settings import settings

# Ensure project root (/app in Docker) is on sys.path
ROOT_PATH = Path(__file__).resolve().parents[2]
if str(ROOT_PATH) not in sys.path:
    sys.path.insert(0, str(ROOT_PATH))

from shared.python.redis.client import get_redis_connection
from shared.python.utils.error_handlers import safe_redis_call
from shared.python.utils.logging_config import get_logger
from shared.python.utils.retry import retryable
from shared.realtime.redis_streams import BARS_REDIS_STREAM, TRADES_REDIS_STREAM

logger = get_logger(__name__)


class RedisStreamsPublisher:
    def __init__(self):
        self.client: redis.Redis | None = None
        self.maxlen = settings.REDIS_STREAM_MAXLEN
        self._connect()

    def _connect(self) -> None:
        """Connect to Redis."""

        def _connect_op() -> redis.Redis:
            client = get_redis_connection(
                host=settings.REDIS_HOST,
                port=settings.REDIS_PORT,
                db=0,
                decode_responses=False,
            )
            client.ping()
            return client

        client = safe_redis_call(
            _connect_op,
            context="connect",
            on_error=lambda exc: logger.error("[RedisStreamsPublisher] Failed to connect to Redis: %s", exc),
        )
        if client:
            self.client = client
            logger.info(
                "[RedisStreamsPublisher] Connected to Redis at %s:%s",
                settings.REDIS_HOST,
                settings.REDIS_PORT,
            )

    @retryable()
    def _xadd(self, stream_key: str, payload: dict) -> None:
        if not self.client:
            raise RuntimeError("Redis client is not connected")
        self.client.xadd(stream_key, payload, maxlen=self.maxlen, approximate=True)

    def publish_trade(self, symbol: str, message: dict) -> None:
        """Publish trade messages to Redis Stream."""
        if not self.client:
            logger.warning(
                "[RedisStreamsPublisher] publish_trade called but Redis client is None"
            )
            return

        payload = {
            b"symbol": symbol.encode("utf-8"),
            b"data": json.dumps(message).encode("utf-8"),
        }

        safe_redis_call(
            lambda: self._xadd(TRADES_REDIS_STREAM, payload),
            context="xadd_trade",
            on_error=lambda exc: logger.error(
                "[RedisStreamsPublisher] Error publishing trade to Redis: %s", exc
            ),
        )

    def publish_bar(self, symbol: str, message: dict) -> None:
        """Publish bar messages to Redis Stream."""
        if not self.client:
            logger.warning(
                "[RedisStreamsPublisher] publish_bar called but Redis client is None"
            )
            return

        payload = {
            b"symbol": symbol.encode("utf-8"),
            b"data": json.dumps(message).encode("utf-8"),
        }

        safe_redis_call(
            lambda: self._xadd(BARS_REDIS_STREAM, payload),
            context="xadd_bar",
            on_error=lambda exc: logger.error(
                "[RedisStreamsPublisher] Error publishing bar to Redis: %s", exc
            ),
        )

    def close(self) -> None:
        """Close Redis connection."""
        if not self.client:
            return

        safe_redis_call(
            lambda: self.client.close(),
            context="close",
            on_error=lambda exc: logger.error(
                "[RedisStreamsPublisher] Error closing Redis connection: %s", exc
            ),
        )
        logger.info("[RedisStreamsPublisher] Redis connection closed")

