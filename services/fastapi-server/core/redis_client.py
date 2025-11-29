import redis
from config.settings import settings
import logging
import json

logger = logging.getLogger(__name__)

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
                self.client = redis.Redis(
                    host=settings.REDIS_HOST,
                    port=settings.REDIS_PORT,
                    db=0,
                    decode_responses=True
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
