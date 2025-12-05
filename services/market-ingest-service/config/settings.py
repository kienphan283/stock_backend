import json
from typing import List, Optional, ClassVar

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
import sys
from pathlib import Path

ROOT_PATH = Path(__file__).resolve().parent.parent
if str(ROOT_PATH) not in sys.path:
    sys.path.insert(0, str(ROOT_PATH))
from shared.realtime.symbols import INGEST_DEFAULT_SYMBOLS
from shared.python.utils.env import load_env


class Settings(BaseSettings):
    """
    Settings for market-ingest-service.

    SUBSCRIBE_SYMBOLS supports:
    - YAML list: ['AAPL', 'MSFT']
    - JSON list string: '["AAPL","MSFT"]'
    - CSV string: 'AAPL,MSFT,GOOGL'
    - Empty / missing: falls back to INGEST_DEFAULT_SYMBOLS (all 30 tickers from shared.constants.tickers)
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Kafka
    KAFKA_BOOTSTRAP_SERVERS: str = load_env("KAFKA_BOOTSTRAP_SERVERS", "kafka:9092")

    # Alpaca API
    ALPACA_API_KEY: Optional[str] = load_env("ALPACA_API_KEY")
    ALPACA_SECRET_KEY: Optional[str] = load_env("ALPACA_SECRET_KEY")
    ALPACA_WS_URL: str = load_env("ALPACA_WS_URL", "wss://stream.data.alpaca.markets/v2/iex")

    # Symbols to subscribe to
    SUBSCRIBE_SYMBOLS: List[str] = Field(default_factory=list)

    # Class constant (NOT a model field) — centralized in shared.realtime.symbols
    DEFAULT_SYMBOLS: ClassVar[List[str]] = INGEST_DEFAULT_SYMBOLS

    @field_validator("SUBSCRIBE_SYMBOLS", mode="before")
    @classmethod
    def parse_symbols(cls, v):
        """
        Normalize SUBSCRIBE_SYMBOLS from:
        - Python list
        - JSON list string
        - CSV string
        - Empty / None → default fallback
        """

        # Empty / missing / blank string → fallback
        if not v or (isinstance(v, str) and not v.strip()):
            return [s.strip().upper() for s in cls.DEFAULT_SYMBOLS]

        # Already a Python list
        if isinstance(v, list):
            cleaned = [str(x).strip().upper() for x in v if str(x).strip()]
            return cleaned or [s.strip().upper() for s in cls.DEFAULT_SYMBOLS]

        # String input: JSON list or CSV
        if isinstance(v, str):
            v = v.strip()

            # JSON list string
            if v.startswith("["):
                try:
                    parsed = json.loads(v)
                    if isinstance(parsed, list):
                        cleaned = [str(x).strip().upper() for x in parsed]
                        return cleaned or [s.strip().upper() for s in cls.DEFAULT_SYMBOLS]
                except json.JSONDecodeError:
                    pass  # fallback below

            # CSV string
            cleaned = [p.strip().upper() for p in v.split(",") if p.strip()]
            return cleaned or [s.strip().upper() for s in cls.DEFAULT_SYMBOLS]

        # Anything else → fallback
        return [s.strip().upper() for s in cls.DEFAULT_SYMBOLS]

    def model_post_init(self, __context) -> None:
        print(f"Loaded symbols: {self.SUBSCRIBE_SYMBOLS}")


settings = Settings()
