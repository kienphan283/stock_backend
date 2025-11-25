from functools import lru_cache
from pathlib import Path
from typing import Optional, Dict, Any
from urllib.parse import urlparse

from dotenv import load_dotenv
from pydantic import BaseSettings, Field

ROOT_DIR = Path(__file__).resolve().parents[2]
ENV_PATH = ROOT_DIR / ".env"
if ENV_PATH.exists():
    load_dotenv(ENV_PATH)


class Settings(BaseSettings):
    database_url: Optional[str] = Field(default=None, env="DATABASE_URL")
    postgres_host: str = Field(default="localhost", env="POSTGRES_HOST")
    postgres_port: int = Field(default=5432, env="POSTGRES_PORT")
    postgres_db: str = Field(default="Web_quan_li_danh_muc", env="POSTGRES_DB")
    postgres_user: str = Field(default="postgres", env="POSTGRES_USER")
    postgres_password: str = Field(env="POSTGRES_PASSWORD")

    redis_host: str = Field(default="localhost", env="REDIS_HOST")
    redis_port: int = Field(default=6379, env="REDIS_PORT")

    cache_ttl: int = Field(default=1800, env="CACHE_TTL")
    alpha_vantage_api_key: str = Field(default="demo", env="ALPHA_VANTAGE_API_KEY")
    alpaca_api_base_url: str = Field(
        default="https://paper-api.alpaca.markets/v2", env="ALPACA_API_BASE_URL"
    )

    class Config:
        env_file = ENV_PATH
        env_file_encoding = "utf-8"

    @property
    def db_config(self) -> Dict[str, Any]:
        if self.database_url:
            parsed = urlparse(self.database_url)
            return {
                "host": parsed.hostname,
                "port": parsed.port or 5432,
                "dbname": parsed.path.lstrip("/"),
                "user": parsed.username,
                "password": parsed.password,
            }

        return {
            "host": self.postgres_host,
            "port": self.postgres_port,
            "dbname": self.postgres_db,
            "user": self.postgres_user,
            "password": self.postgres_password,
        }


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()


settings = get_settings()

