"""
Yahoo Finance extraction helpers for EOD ETL.
"""

from __future__ import annotations

from typing import Optional

import pandas as pd
import yfinance as yf


def download_price_history(ticker: str, years: int) -> pd.DataFrame:
    df = yf.download(
        ticker,
        period=f"{years}y",
        auto_adjust=False,
        progress=False,
        threads=False,
    )
    if df.empty:
        raise ValueError(f"No historical price data returned for {ticker}")

    df = df.reset_index()
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = [
            col[0] if isinstance(col, tuple) and len(col) > 0 else col
            for col in df.columns
        ]
    if "Date" not in df.columns:
        df = df.rename(columns={df.columns[0]: "Date"})
    df["Date"] = pd.to_datetime(df["Date"]).dt.date
    df = df.sort_values("Date")
    df["pct_change"] = df["Close"].pct_change() * 100
    df["pct_change"] = df["pct_change"].round(2)
    return df

