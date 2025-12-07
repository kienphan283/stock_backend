import redis
from config.settings import settings
import logging
import json

logger = logging.getLogger(__name__)

# Import shared Redis client helper
import sys
from pathlib import Path

ROOT_PATH = Path(__file__).resolve().parent.parent
if str(ROOT_PATH) not in sys.path:
    sys.path.insert(0, str(ROOT_PATH))
from shared.python.redis.client import get_redis_connection

class RedisClient:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(RedisClient, cls).__new__(cls)
            cls._instance.client = None
            cls._instance.enabled = False
            cls._instance._connect()
        return cls._instance

    def _connect(self):
        try:
            if settings.REDIS_HOST:
                self.client = get_redis_connection(
                    host=settings.REDIS_HOST,
                    port=settings.REDIS_PORT,
                    db=0,
                    decode_responses=True,
                )
                self.client.ping()
                self.enabled = True
                logger.info(f"Redis connected at {settings.REDIS_HOST}:{settings.REDIS_PORT}")
            else:
                logger.warning("Redis host not configured")
        except Exception as e:
            logger.warning(f"Redis connection failed: {e}")
            self.enabled = False

    def get(self, key: str):
        if not self.enabled:
            return None
        try:
            data = self.client.get(key)
            return json.loads(data) if data else None
        except Exception as e:
            logger.error(f"Redis get error: {e}")
            return None

    def set(self, key: str, value: any, ttl: int = 1800):
        if not self.enabled:
            return
        try:
            self.client.setex(key, ttl, json.dumps(value))
        except Exception as e:
            logger.error(f"Redis set error: {e}")

    def setex(self, key: str, ttl: int, value: any):
        """Set key with TTL (time to live) in seconds."""
        if not self.enabled:
            return
        try:
            self.client.setex(key, ttl, json.dumps(value) if not isinstance(value, str) else value)
        except Exception as e:
            logger.error(f"Redis setex error: {e}")