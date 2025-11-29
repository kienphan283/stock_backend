"""
Database loaders for EOD ETL.
"""

from __future__ import annotations

import logging
from typing import Iterable, List, Sequence, Tuple

from psycopg2.extras import execute_values

from etl.common.db import PostgresConnector

logger = logging.getLogger(__name__)


EODRecord = Tuple[int, object, object, object, object, object, object, object]


class EODLoader:
    def __init__(self, connector: PostgresConnector):
        self.connector = connector

    def _get_connection(self):
        return self.connector.get_connection()

    def ensure_company(self, cursor, ticker: str) -> None:
        cursor.execute(
            """
            INSERT INTO financial_oltp.company (company_id, company_name, exchange)
            VALUES (%s, %s, %s)
            ON CONFLICT (company_id) DO NOTHING
            """,
            (ticker, f"{ticker} Corporation", "NYSE"),
        )

    def ensure_stock(self, cursor, ticker: str) -> int:
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

    def upsert_eod_prices(self, cursor, records: Iterable[EODRecord]) -> int:
        record_list = list(records)
        if not record_list:
            return 0
        execute_values(
            cursor,
            """
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
            """,
            record_list,
            page_size=500,
        )
        return len(record_list)

    def fetch_all_company_tickers(self, cursor) -> List[str]:
        cursor.execute(
            """
            SELECT company_id
            FROM financial_oltp.company
            ORDER BY company_id
            """
        )
        rows = cursor.fetchall()
        return [row[0].upper() for row in rows if row[0]]

