"""
Shared Redis client wrapper for streaming pipelines.
"""
import json
import logging
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)

try:
    import redis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False
    logger.warning("redis package not installed. Redis streaming disabled.")


class RedisClient:
    def __init__(self, host: str, port: int, db: int = 0, **kwargs: Any):
        if not REDIS_AVAILABLE:
            raise ImportError("redis package is required for Redis streaming")

        self.host = host
        self.port = port
        self.db = db
        self.kwargs = kwargs
        self.client: Optional["redis.Redis"] = None
        self._connect()

    def _connect(self) -> None:
        try:
            self.client = redis.Redis(
                host=self.host,
                port=self.port,
                db=self.db,
                decode_responses=False,
                socket_connect_timeout=5,
                socket_timeout=5,
                **self.kwargs,
            )
            self.client.ping()
            logger.info("Redis connected to %s:%s", self.host, self.port)
        except Exception:
            logger.exception("Failed to connect to Redis")
            raise

    def publish(self, channel: str, payload: Dict[str, Any]) -> bool:
        if not self.client:
            logger.error("Redis client not initialized")
            return False
        try:
            message = json.dumps(payload).encode("utf-8")
            self.client.publish(channel, message)
            return True
        except Exception:
            logger.exception("Failed to publish to Redis channel %s", channel)
            return False

    def add_to_stream(self, stream_key: str, payload: Dict[str, Any]) -> bool:
        if not self.client:
            logger.error("Redis client not initialized")
            return False
        try:
            stream_payload = {k: str(v) for k, v in payload.items()}
            self.client.xadd(stream_key, stream_payload)
            return True
        except Exception:
            logger.exception("Failed to add message to Redis stream %s", stream_key)
            return False

    def close(self) -> None:
        if self.client:
            self.client.close()
            logger.info("Redis client closed")

