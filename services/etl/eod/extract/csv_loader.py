"""
Legacy CSV loader utilities (migrated from FastAPI).

These helpers are no longer used by FastAPI directly but remain available
for offline ETL/debugging workflows.
"""

from __future__ import annotations

import json
import os
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd
import psycopg2
from psycopg2.extras import RealDictCursor
from dotenv import load_dotenv


CURRENT_FILE_PATH = Path(__file__).resolve()
ENV_PATH = CURRENT_FILE_PATH.parents[3] / ".env"
if ENV_PATH.exists():
    load_dotenv(ENV_PATH)


class StockDataLoader:
    """Load stock data from local CSV files."""

    def __init__(self, ticker: str = "APP", data_dir: str = "./data"):
        if not ticker or not isinstance(ticker, str) or len(ticker) > 5:
            raise ValueError("Invalid ticker format")
        if not ticker.isalnum():
            raise ValueError("Ticker must contain only alphanumeric characters")
        self.ticker = ticker
        self.data_dir = data_dir

        self.DB_CONFIG = {
            "host": os.getenv("DB_HOST"),
            "port": os.getenv("DB_PORT"),
            "dbname": os.getenv("DB_NAME"),
            "user": os.getenv("DB_USER"),
            "password": os.getenv("DB_PASSWORD"),
        }

    def _file_exists(self, filename: str) -> bool:
        return os.path.exists(os.path.join(self.data_dir, filename))

    def _safe_read_csv(self, filename: str) -> Optional[pd.DataFrame]:
        try:
            file_path = os.path.join(self.data_dir, filename)
            if not os.path.exists(file_path):
                return None
            df = pd.read_csv(file_path)
            return df if not df.empty else None
        except Exception:
            return None

    def _format_number(self, value: Any, decimals: int = 2) -> float:
        try:
            if pd.isna(value) or value is None:
                return 0.0
            return round(float(value), decimals)
        except (ValueError, TypeError):
            return 0.0

    def _format_date_iso(self, date_str: str) -> str:
        try:
            if pd.isna(date_str) or not date_str:
                return datetime.now(timezone.utc).isoformat()

            formats = ["%Y-%m-%d", "%Y-%m-%d %H:%M:%S", "%m/%d/%Y"]
            for fmt in formats:
                try:
                    dt = datetime.strptime(str(date_str), fmt)
                    return dt.replace(tzinfo=timezone.utc).isoformat()
                except ValueError:
                    continue
            return datetime.now(timezone.utc).isoformat()
        except Exception:
            return datetime.now(timezone.utc).isoformat()

    def get_quote(self) -> Dict[str, Any]:
        df = self._safe_read_csv("stock_quote.csv")
        if df is None or df.empty:
            return {
                "currentPrice": 0.0,
                "change": 0.0,
                "percentChange": 0.0,
                "high": 0.0,
                "low": 0.0,
                "open": 0.0,
                "previousClose": 0.0,
            }
        row = df.iloc[0]
        return {
            "currentPrice": self._format_number(row.get("current_price", 0)),
            "change": self._format_number(row.get("change", 0)),
            "percentChange": self._format_number(row.get("percent_change", 0), 4),
            "high": self._format_number(row.get("high", 0)),
            "low": self._format_number(row.get("low", 0)),
            "open": self._format_number(row.get("open", 0)),
            "previousClose": self._format_number(row.get("previous_close", 0)),
        }

    def get_company_profile(self) -> Dict[str, Any]:
        try:
            conn = psycopg2.connect(**self.DB_CONFIG)
            cursor = conn.cursor(cursor_factory=RealDictCursor)
            cursor.execute(
                """
                SELECT company_id as ticker, company_name as name, exchange, currency
                FROM company
                WHERE company_id = %s
                """,
                (self.ticker,),
            )
            result = cursor.fetchone()
            cursor.close()
            conn.close()
            if result:
                return {
                    "name": result["name"],
                    "ticker": result["ticker"],
                    "exchange": result["exchange"] or "NYSE",
                    "country": "US",
                    "currency": result["currency"] or "USD",
                    "industry": "Technology",
                    "marketCap": 0.0,
                    "ipoDate": "",
                    "logo": "",
                    "sharesOutstanding": 0.0,
                    "website": "",
                    "phone": "",
                }
        except Exception:
            pass

        return {
            "name": f"{self.ticker} Corporation",
            "ticker": self.ticker,
            "exchange": "NYSE",
            "country": "US",
            "currency": "USD",
            "industry": "Technology",
            "marketCap": 0.0,
            "ipoDate": "",
            "logo": "",
            "sharesOutstanding": 0.0,
            "website": "",
            "phone": "",
        }

    def get_price_history(self, period: str = "3m") -> Dict[str, Any]:
        df = self._safe_read_csv("stock_candles.csv")
        if df is None or df.empty:
            return {"dates": [], "series": []}
        df["date"] = pd.to_datetime(df["date"])
        df = df.sort_values("date")
        dates = [self._format_date_iso(date.strftime("%Y-%m-%d")) for date in df["date"]]
        prices = [self._format_number(price) for price in df["close"]]
        return {"dates": dates, "series": [{"name": self.ticker, "data": prices}]}

    def get_dividends(self) -> List[Dict[str, Any]]:
        df = self._safe_read_csv("dividends.csv")
        if df is None or df.empty:
            return []
        dividends = []
        for _, row in df.iterrows():
            dividends.append(
                {
                    "date": self._format_date_iso(row.get("date", "")),
                    "amount": self._format_number(row.get("amount", 0), 4),
                    "adjustedAmount": self._format_number(
                        row.get("adjusted_amount", 0), 4
                    ),
                    "currency": str(row.get("currency", "USD")),
                    "declaredDate": self._format_date_iso(row.get("declared_date", "")),
                    "payDate": self._format_date_iso(row.get("pay_date", "")),
                    "recordDate": self._format_date_iso(row.get("record_date", "")),
                }
            )
        return dividends

    def get_news(self, limit: int = 16) -> Dict[str, Any]:
        df = self._safe_read_csv("company_news.csv")
        if df is None or df.empty:
            return {"newsTotalCount": 0, "news": []}
        df_limited = df.head(limit)
        news_articles = []
        for _, row in df_limited.iterrows():
            datetime_str = str(row.get("datetime", ""))
            if datetime_str and datetime_str != "nan":
                try:
                    dt = pd.to_datetime(datetime_str)
                    iso_datetime = dt.isoformat() + "Z"
                except Exception:
                    iso_datetime = datetime.now(timezone.utc).isoformat()
            else:
                iso_datetime = datetime.now(timezone.utc).isoformat()

            news_articles.append(
                {
                    "id": str(row.get("id", "")),
                    "headline": str(row.get("headline", "")),
                    "summary": str(row.get("summary", "")),
                    "source": str(row.get("source", "")),
                    "url": str(row.get("url", "")),
                    "datetime": iso_datetime,
                    "category": str(row.get("category", "general")),
                    "image": str(row.get("image", "")),
                    "assetInfoIds": [self.ticker],
                }
            )
        return {"newsTotalCount": len(df), "news": news_articles}

    def get_financials(self) -> Dict[str, Any]:
        df = self._safe_read_csv("financials_reported.csv")
        if df is None or df.empty:
            return {
                "incomeStatement": [],
                "balanceSheet": [],
                "cashFlow": [],
                "supplemental": [],
                "ratios": self._get_financial_ratios(),
            }
        # Simplified copy of previous logic retained for reference.
        return {"rawData": json.loads(df.to_json(orient="records"))}

    def _get_financial_ratios(self) -> List[Dict[str, Any]]:
        df = self._safe_read_csv("financials_metrics.csv")
        if df is None or df.empty:
            return []
        row = df.iloc[0]
        ratios = []
        ratio_mappings = {
            "pe_ratio": ("P/E Ratio", "peRatio"),
            "profit_margin": ("Profit Margin", "profitMargin"),
            "roe": ("Return on Equity", "returnOnEquity"),
            "roa": ("Return on Assets", "returnOnAssets"),
            "debt_to_equity": ("Debt to Equity", "debtToEquity"),
            "current_ratio": ("Current Ratio", "currentRatio"),
            "quick_ratio": ("Quick Ratio", "quickRatio"),
        }
        for csv_field, (display_name, camel_name) in ratio_mappings.items():
            value = row.get(csv_field, 0)
            if not pd.isna(value) and value != 0:
                ratios.append(
                    {
                        "name": camel_name,
                        "displayName": display_name,
                        "value": self._format_number(value, 4),
                        "unit": "ratio"
                        if "ratio" in camel_name.lower()
                        else "percentage",
                    }
                )
        return ratios

    def refresh_data(self) -> bool:
        try:
            script_path = os.path.join(self.data_dir, "fetch_finnhub_data.py")
            if not os.path.exists(script_path):
                return False
            result = subprocess.run(
                ["python", script_path],
                cwd=self.data_dir,
                capture_output=True,
                text=True,
            )
            return result.returncode == 0
        except Exception:
            return False

