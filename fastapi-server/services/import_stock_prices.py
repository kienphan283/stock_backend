"""Import end-of-day stock prices into PostgreSQL.

This module fetches historical price data from Yahoo Finance via yfinance
and loads it into the `market_data_oltp.stock_eod_prices` table. It follows
the same configuration approach used by other service modules (see
`data.py` and `data_loader.py`) by reading database credentials from the
`.env.local` file.

Usage:
    python services/import_stock_prices.py --tickers IBM MSFT AAPL --years 5

If no tickers are provided, all tickers from `financial_oltp.company` are
processed.
"""

from __future__ import annotations

import argparse
import logging
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Iterable, List, Optional, Sequence, Tuple

import pandas as pd
import psycopg2
from psycopg2.extensions import connection as PGConnection
from psycopg2.extras import execute_values
from psycopg2.extras import RealDictCursor
import yfinance as yf
from dotenv import load_dotenv
import os


logger = logging.getLogger(__name__)


# Load environment variables in the same fashion as other service modules
CURRENT_FILE_PATH = Path(__file__).resolve()
ENV_PATH = CURRENT_FILE_PATH.parent.parent / ".env.local"
if ENV_PATH.exists():
    load_dotenv(ENV_PATH)


DB_CONFIG = {
    "host": os.getenv("DB_HOST", "localhost"),
    "port": os.getenv("DB_PORT", "5432"),
    "dbname": os.getenv("DB_NAME", "Web_quan_li_danh_muc"),
    "user": os.getenv("DB_USER", "postgres"),
    "password": os.getenv("DB_PASSWORD"),
}

# Validate password is set
if not DB_CONFIG["password"]:
    raise ValueError("DB_PASSWORD environment variable is required")


DEFAULT_TICKERS: Sequence[str] = (
    "AAPL",  # Apple
    "MSFT",  # Microsoft
    "GOOGL",  # Alphabet (Google)
    "AMZN",  # Amazon
    "NVDA",  # Nvidia
    "META",  # Meta Platforms
    "TSLA",  # Tesla
    "BRK-B",  # Berkshire Hathaway
    "JNJ",  # Johnson & Johnson
    "JPM",  # JPMorgan Chase
    "IBM",  # IBM (initial dataset)
)


__all__ = [
    "DEFAULT_TICKERS",
    "import_eod_prices_for_symbol",
    "import_eod_prices_for_companies",
    "import_prices_for_all_companies",
]


@dataclass
class PriceRecord:
    stock_id: int
    trading_date: date
    open_price: Optional[float]
    high_price: Optional[float]
    low_price: Optional[float]
    close_price: Optional[float]
    volume: Optional[int]
    pct_change: Optional[float]


def _get_connection() -> PGConnection:
    """Create a new PostgreSQL connection using environment configuration."""

    return psycopg2.connect(**DB_CONFIG)


def _ensure_company(cursor, ticker: str) -> None:
    """Ensure the company exists in financial_oltp.company.

    In case the company record is missing, insert a minimal placeholder so that
    the foreign key constraint in market_data_oltp.stocks is satisfied.
    """

    cursor.execute(
        """
        INSERT INTO financial_oltp.company (company_id, company_name, exchange)
        VALUES (%s, %s, %s)
        ON CONFLICT (company_id) DO NOTHING
        """,
        (ticker, f"{ticker} Corporation", "NYSE"),
    )


def _ensure_stock(cursor, ticker: str) -> int:
    """Get or create the stock entry in market_data_oltp.stocks."""

    cursor.execute(
        """
        SELECT stock_id
        FROM market_data_oltp.stocks
        WHERE stock_ticker = %s
        """,
        (ticker,),
    )
    result = cursor.fetchone()
    if result:
        return result[0]

    cursor.execute(
        """
        SELECT company_name, exchange
        FROM financial_oltp.company
        WHERE company_id = %s
        """,
        (ticker,),
    )
    company_row = cursor.fetchone()
    company_name = company_row[0] if company_row else f"{ticker} Corporation"
    exchange = company_row[1] if company_row and company_row[1] else "NYSE"

    cursor.execute(
        """
        INSERT INTO market_data_oltp.stocks (
            company_id,
            stock_ticker,
            stock_name,
            exchange,
            delisted
        )
        VALUES (%s, %s, %s, %s, FALSE)
        ON CONFLICT (stock_ticker) DO UPDATE
        SET stock_name = EXCLUDED.stock_name,
            exchange = EXCLUDED.exchange,
            delisted = EXCLUDED.delisted
        RETURNING stock_id
        """,
        (ticker, ticker, company_name, exchange),
    )

    stock_id = cursor.fetchone()[0]
    logger.info("Created/updated stock entry for %s (stock_id=%s)", ticker, stock_id)
    return stock_id


def _prepare_records(stock_id: int, df: pd.DataFrame) -> List[PriceRecord]:
    """Convert the pandas DataFrame into a list of PriceRecord objects."""

    records: List[PriceRecord] = []

    def to_float(value: float | int | None) -> Optional[float]:
        if value is None:
            return None
        if pd.isna(value):
            return None
        return float(value)

    def to_int(value: float | int | None) -> Optional[int]:
        if value is None:
            return None
        if pd.isna(value):
            return None
        return int(value)

    for row in df.itertuples():
        records.append(
            PriceRecord(
                stock_id=stock_id,
                trading_date=row.Date,
                open_price=to_float(row.Open),
                high_price=to_float(row.High),
                low_price=to_float(row.Low),
                close_price=to_float(row.Close),
                volume=to_int(row.Volume),
                pct_change=to_float(getattr(row, "pct_change", None)),
            )
        )

    return records


def _fetch_price_history(ticker: str, years: int) -> pd.DataFrame:
    """Download historical price data for the given ticker."""

    logger.info("Downloading %s years of EOD data for %s", years, ticker)
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


def _upsert_eod_prices(cursor, records: Iterable[PriceRecord]) -> int:
    """Insert or update end-of-day price records using ON CONFLICT."""

    records_list = list(records)
    if not records_list:
        return 0

    insert_query = """
        INSERT INTO market_data_oltp.stock_eod_prices (
            stock_id,
            trading_date,
            open_price,
            high_price,
            low_price,
            close_price,
            volume,
            pct_change
        )
        VALUES %s
        ON CONFLICT (stock_id, trading_date) DO UPDATE
        SET open_price = EXCLUDED.open_price,
            high_price = EXCLUDED.high_price,
            low_price = EXCLUDED.low_price,
            close_price = EXCLUDED.close_price,
            volume = EXCLUDED.volume,
            pct_change = EXCLUDED.pct_change,
            inserted_at = CURRENT_TIMESTAMP
    """

    values = [
        (
            rec.stock_id,
            rec.trading_date,
            rec.open_price,
            rec.high_price,
            rec.low_price,
            rec.close_price,
            rec.volume,
            rec.pct_change,
        )
        for rec in records_list
    ]

    execute_values(cursor, insert_query, values, page_size=500)

    return len(records_list)


def import_eod_prices_for_symbol(
    ticker: str,
    *,
    years: int = 5,
    conn: Optional[PGConnection] = None,
) -> int:
    """Fetch and load EOD prices for a single ticker.

    Args:
        ticker: Stock ticker symbol.
        years: Number of years of history to download from Yahoo Finance.
        conn: Optional existing PostgreSQL connection. If omitted, a new
            connection will be created and closed within the function.

    Returns:
        The number of records inserted or updated.
    """

    ticker = ticker.upper()
    managed_connection = False
    if conn is None:
        conn = _get_connection()
        managed_connection = True

    try:
        with conn.cursor() as cursor:
            _ensure_company(cursor, ticker)
            stock_id = _ensure_stock(cursor, ticker)
            df = _fetch_price_history(ticker, years)
            records = _prepare_records(stock_id, df)
            inserted = _upsert_eod_prices(cursor, records)
            conn.commit()
            logger.info(
                "Imported %s EOD records for %s (stock_id=%s)",
                inserted,
                ticker,
                stock_id,
            )
            return inserted
    except Exception:
        conn.rollback()
        logger.exception("Failed to import EOD prices for %s", ticker)
        raise
    finally:
        if managed_connection:
            conn.close()


def import_eod_prices_for_companies(
    tickers: Iterable[str],
    *,
    years: int = 5,
) -> int:
    """Import EOD prices for multiple tickers using a shared connection."""

    tickers = [ticker.upper() for ticker in tickers]
    if not tickers:
        return 0

    total_inserted = 0
    conn = _get_connection()

    try:
        for ticker in tickers:
            inserted = import_eod_prices_for_symbol(
                ticker,
                years=years,
                conn=conn,
            )
            total_inserted += inserted
    finally:
        conn.close()

    return total_inserted


def import_prices_for_all_companies(
    *,
    years: int = 5,
    fallback_tickers: Optional[Sequence[str]] = None,
) -> Tuple[List[str], int]:
    """Import prices for every company in the database.

    Args:
        years: Number of years of EOD data to fetch from Yahoo Finance.
        fallback_tickers: Optional list of tickers to use when the
            ``financial_oltp.company`` table is empty. Defaults to
            ``DEFAULT_TICKERS``.

    Returns:
        A tuple of ``(tickers_processed, total_records_inserted)``.
    """

    fallback_list = [ticker.upper() for ticker in (fallback_tickers or DEFAULT_TICKERS)]

    conn = _get_connection()

    try:
        tickers = _fetch_all_company_tickers(conn)
        if not tickers:
            tickers = list(fallback_list)
            logger.info(
                "No tickers found in financial_oltp.company; using fallback list: %s",
                ", ".join(tickers),
            )

        processed: List[str] = []
        total_inserted = 0
        for ticker in tickers:
            try:
                inserted = import_eod_prices_for_symbol(
                    ticker,
                    years=years,
                    conn=conn,
                )
                total_inserted += inserted
                processed.append(ticker)
            except Exception as exc:  # pragma: no cover - network/db issues
                logger.error("Skipping %s due to error: %s", ticker, exc)

        return processed, total_inserted
    finally:
        conn.close()


def _fetch_all_company_tickers(conn: PGConnection) -> List[str]:
    """Fetch all company tickers from financial_oltp.company."""

    with conn.cursor(cursor_factory=RealDictCursor) as cursor:
        cursor.execute(
            """
            SELECT company_id
            FROM financial_oltp.company
            ORDER BY company_id
            """
        )
        rows = cursor.fetchall()
        return [row["company_id"].upper() for row in rows if row["company_id"]]


def main(argv: Optional[List[str]] = None) -> None:
    parser = argparse.ArgumentParser(description="Import EOD stock prices")
    parser.add_argument(
        "--tickers",
        nargs="*",
        help="List of ticker symbols. If omitted, all companies in the database are used.",
    )
    parser.add_argument(
        "--years",
        type=int,
        default=5,
        help="Number of years of historical data to download (default: 5)",
    )

    args = parser.parse_args(argv)

    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

    if args.tickers:
        tickers = [ticker.upper() for ticker in args.tickers]
        total = import_eod_prices_for_companies(tickers, years=args.years)
        logger.info(
            "Completed EOD import for provided tickers (%s). Total records processed: %s",
            ", ".join(tickers),
            total,
        )
    else:
        processed, total = import_prices_for_all_companies(
            years=args.years,
            fallback_tickers=DEFAULT_TICKERS,
        )
        logger.info(
            "Completed EOD import for %s tickers. Total records processed: %s",
            len(processed),
            total,
        )


if __name__ == "__main__":
    main()

