"""
Helpers for Alpaca credentials and configuration.
"""
import os
from dataclasses import dataclass
from typing import List

from etl.common.env_loader import load_root_env

load_root_env()


@dataclass
class AlpacaCredentials:
    api_key: str
    api_secret: str
    data_ws_url: str
    symbols: List[str]

    def validate(self) -> None:
        if not self.api_key or not self.api_secret:
            raise ValueError("ALPACA_API_KEY and ALPACA_API_SECRET are required")


def get_alpaca_credentials() -> AlpacaCredentials:
    symbols = os.getenv("SUBSCRIBED_SYMBOLS", "AAPL,MSFT,GOOGL").split(",")
    creds = AlpacaCredentials(
        api_key=os.getenv("ALPACA_API_KEY", ""),
        api_secret=os.getenv("ALPACA_API_SECRET", ""),
        data_ws_url=os.getenv(
            "ALPACA_DATA_WS_URL", "wss://stream.data.alpaca.markets/v2/iex"
        ),
        symbols=[symbol.strip().upper() for symbol in symbols if symbol.strip()],
    )
    creds.validate()
    return creds

