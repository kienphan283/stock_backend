import os
from pydantic_settings import BaseSettings
from typing import Optional

class Settings(BaseSettings):
    # Database
    DB_HOST: str = "postgres"
    DB_PORT: int = 5432
    DB_NAME: str = "Web_quan_li_danh_muc"
    DB_USER: str = "postgres"
    DB_PASSWORD: str

    # Redis
    REDIS_HOST: str = "redis"
    REDIS_PORT: int = 6379
    REDIS_URL: Optional[str] = None
    CACHE_TTL: int = 1800

    # API Keys
    ALPHA_VANTAGE_API_KEY: str = "demo"
    FINNHUB_API_KEY: Optional[str] = None

    # Kafka
    KAFKA_BOOTSTRAP_SERVERS: str = "kafka:9092"

    class Config:
        env_file = "../../.env"
        extra = "ignore"

settings = Settings()
