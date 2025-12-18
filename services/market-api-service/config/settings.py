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
    DB_SSL_MODE: str = load_env("DB_SSL_MODE", "require")
    DB_SSL_MODE: str = load_env("DB_SSL_MODE", "disable")

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
    FINNHUB_API_KEY: str = load_env("FINNHUB_API_KEY", "")
    
    # Authentication
    JWT_SECRET: str = load_env("JWT_SECRET", "super-secret-key-change-me-in-prod")
    JWT_ALGORITHM: str = load_env("JWT_ALGORITHM", "HS256")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = int(load_env("ACCESS_TOKEN_EXPIRE_MINUTES", "1440")) # 1 day

    # OAuth
    GOOGLE_CLIENT_ID: str = load_env("GOOGLE_CLIENT_ID", "")
    GOOGLE_CLIENT_SECRET: str = load_env("GOOGLE_CLIENT_SECRET", "")
    FACEBOOK_CLIENT_ID: str = load_env("FACEBOOK_CLIENT_ID", "")
    FACEBOOK_CLIENT_SECRET: str = load_env("FACEBOOK_CLIENT_SECRET", "")
    
    # Mail
    # Mail - HARDCODED DEBUG
    MAIL_USERNAME: str = "huykien283@gmail.com"
    MAIL_PASSWORD: str = "uuey fygc tuqp nist"
    MAIL_FROM: str = "huykien283@gmail.com"
    MAIL_PORT: int = 587
    MAIL_SERVER: str = "smtp.gmail.com"
    
    # Alpaca API (for EOD data fetching - Kept active as it might be used by quote service)
    ALPACA_API_KEY: Optional[str] = load_env("ALPACA_API_KEY")
    ALPACA_SECRET_KEY: Optional[str] = load_env("ALPACA_SECRET_KEY")
    ALPACA_BASE_URL: str = load_env("ALPACA_BASE_URL", "https://data.alpaca.markets")

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"


settings = Settings()

