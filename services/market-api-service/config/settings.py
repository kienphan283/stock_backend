import sys
from pathlib import Path
from pydantic_settings import BaseSettings
from typing import Optional

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
    REDIS_URL: Optional[str] = load_env("REDIS_URL")
    CACHE_TTL: int = int(load_env("CACHE_TTL", "1800"))

    # Security
    ALLOWED_ORIGINS: str = load_env(
        "ALLOWED_ORIGINS",
        "http://localhost:3000,http://127.0.0.1:3000",
    )

    # API Keys
    ALPHA_VANTAGE_API_KEY: str = load_env("ALPHA_VANTAGE_API_KEY", "demo")
    FINNHUB_API_KEY: Optional[str] = load_env("FINNHUB_API_KEY")
    
    # Alpaca API (for EOD data fetching)
    ALPACA_API_KEY: Optional[str] = load_env("ALPACA_API_KEY")
    ALPACA_SECRET_KEY: Optional[str] = load_env("ALPACA_SECRET_KEY")
    ALPACA_BASE_URL: str = load_env("ALPACA_BASE_URL", "https://data.alpaca.markets")

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"


settings = Settings()

