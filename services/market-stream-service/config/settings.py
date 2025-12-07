import sys
from pathlib import Path
from pydantic_settings import BaseSettings

ROOT_PATH = Path(__file__).resolve().parents[2]
if str(ROOT_PATH) not in sys.path:
    sys.path.insert(0, str(ROOT_PATH))

from shared.python.utils.env import load_env


class Settings(BaseSettings):
    # Database
    DB_HOST: str = load_env("DB_HOST", "postgres")
    DB_PORT: int = int(load_env("DB_PORT", "5432"))
    DB_NAME: str = load_env("DB_NAME", "Web_quan_li_danh_muc")
    DB_USER: str = load_env("DB_USER", "postgres")
    DB_PASSWORD: str

    # Redis
    REDIS_HOST: str = load_env("REDIS_HOST", "redis")
    REDIS_PORT: int = int(load_env("REDIS_PORT", "6379"))

    # Kafka
    KAFKA_BOOTSTRAP_SERVERS: str = load_env("KAFKA_BOOTSTRAP_SERVERS", "kafka:9092")
    KAFKA_ENABLE_AUTO_COMMIT: bool = load_env("KAFKA_ENABLE_AUTO_COMMIT", "false").lower() == "true"

    # API Keys
    ALPHA_VANTAGE_API_KEY: str = load_env("ALPHA_VANTAGE_API_KEY", "demo")

    # Redis Streams
    REDIS_STREAM_MAXLEN: int = int(load_env("REDIS_STREAM_MAXLEN", "20000"))

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"


settings = Settings()

