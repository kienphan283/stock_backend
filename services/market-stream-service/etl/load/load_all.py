"""
Unified load helpers for financial data (company, financial statements, EOD).

This module wraps the existing BCTC and EOD loaders so that a single entrypoint
can persist all extracted data into Postgres without changing the DB schema.
"""

from __future__ import annotations

from typing import Dict, Iterable, List

from etl.bctc.load.database_loader import BCTCDatabaseLoader
from etl.eod.load.db_loader import EODLoader, EODRecord
from shared.python.db.connector import PostgresConnector


def load_company_and_statements(
    bctc_loader: BCTCDatabaseLoader,
    conn,
    overview: Dict,
    symbol: str,
    statements: Dict[str, List[Dict]],
) -> None:
    """
    Persist company metadata and financial statements (IS/BS/CF).

    - overview: Alpha Vantage OVERVIEW payload (may be empty).
    - statements: dict with keys "IS", "BS", "CF" pointing to quarterlyReports lists.
    """
    company_name = overview.get("Name") if overview else None
    sector = overview.get("Sector") if overview else None
    exchange = overview.get("Exchange") if overview else None
    currency = overview.get("Currency") if overview else None

    bctc_loader.ensure_company(
        conn,
        symbol,
        company_name=company_name,
        sector=sector,
        exchange=exchange,
        currency=currency,
    )

    for code in ["IS", "BS", "CF"]:
        reports = statements.get(code, [])
        # Gracefully skip when Alpha Vantage returns empty or error
        if not reports:
            continue
        bctc_loader.load_statement(conn, symbol, code, reports)


def load_eod_prices(
    eod_loader: EODLoader,
    records: Iterable[EODRecord],
) -> int:
    """
    Persist EOD price series using the existing EODLoader.

    This delegates to EODLoader.upsert_eod_prices, keeping the current schema:
    - market_data_oltp.stocks
    - market_data_oltp.stock_eod_prices
    """
    with eod_loader._get_connection() as conn:
        with conn.cursor() as cursor:
            inserted = eod_loader.upsert_eod_prices(cursor, records)
            conn.commit()
            return inserted


