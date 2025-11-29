"""
Normalize raw Yahoo Finance data for EOD loading.
"""

from __future__ import annotations

from datetime import date
from typing import Iterable, List, Optional, Tuple

import pandas as pd

EODRecord = Tuple[int, date, Optional[float], Optional[float], Optional[float], Optional[float], Optional[int], Optional[float]]


def filter_by_start_date(df: pd.DataFrame, start_date: Optional[str]) -> pd.DataFrame:
    if not start_date:
        return df
    mask = df["Date"] >= pd.to_datetime(start_date).date()
    return df.loc[mask]


def prepare_records(stock_id: int, df: pd.DataFrame) -> List[EODRecord]:
    records: List[EODRecord] = []

    def to_float(value):
        if value is None or pd.isna(value):
            return None
        return float(value)

    def to_int(value):
        if value is None or pd.isna(value):
            return None
        return int(value)

    for row in df.itertuples():
        records.append(
            (
                stock_id,
                row.Date,
                to_float(getattr(row, "Open", None)),
                to_float(getattr(row, "High", None)),
                to_float(getattr(row, "Low", None)),
                to_float(getattr(row, "Close", None)),
                to_int(getattr(row, "Volume", None)),
                to_float(getattr(row, "pct_change", None)),
            )
        )
    return records

