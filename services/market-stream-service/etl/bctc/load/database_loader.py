"""
Database loading helpers for BCTC ETL.
"""

from __future__ import annotations

import logging
from typing import Dict, Iterable, List, Tuple

import psycopg2
from psycopg2.extras import execute_values

from etl.bctc.transform.financial_transformer import normalize_item_name

logger = logging.getLogger(__name__)


class BCTCDatabaseLoader:
    def __init__(self, db_config: Dict[str, str]):
        self.db_config = db_config

    def _get_connection(self):
        return psycopg2.connect(**self.db_config)

    def ensure_company(
        self,
        conn,
        symbol: str,
        company_name: str | None = None,
        sector: str | None = None,
        exchange: str | None = None,
        currency: str | None = None,
    ):
        """
        Ensure that a company row exists in financial_oltp.company.

        - Uses Alpha Vantage metadata when available (name, sector, exchange, currency).
        - Falls back to sensible defaults when fields are missing.
        - On conflict, updates mutable fields while preserving an existing non-null sector.
        """
        name = company_name or f"{symbol} Corporation"
        ex = exchange or "NYSE"
        curr = currency or "USD"

        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO financial_oltp.company
                    (company_id, company_name, sector, exchange, currency)
                VALUES (%s, %s, %s, %s, %s)
                ON CONFLICT (company_id) DO UPDATE
                SET
                    company_name = EXCLUDED.company_name,
                    exchange     = EXCLUDED.exchange,
                    currency     = EXCLUDED.currency,
                    sector       = COALESCE(EXCLUDED.sector, financial_oltp.company.sector)
                """,
                (symbol, name, sector, ex, curr),
            )
        conn.commit()

    def load_statement(
        self,
        conn,
        symbol: str,
        statement_code: str,
        reports: Iterable[Dict],
    ):
        reports = list(reports)
        if not reports:
            logger.warning("No reports returned for %s (%s)", symbol, statement_code)
            return

        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT statement_type_id
                FROM financial_oltp.statement_type
                WHERE statement_code = %s
                """,
                (statement_code,),
            )
            row = cur.fetchone()
            if not row:
                raise ValueError(f"Unknown statement_code={statement_code}")
            statement_type_id = row[0]

            # Preload dictionary items so we only insert known items.
            cur.execute(
                """
                SELECT item_code, item_name
                FROM financial_oltp.line_item_dictionary
                """
            )
            dictionary_items = {row[0]: row[1] for row in cur.fetchall()}

            for report in reports:
                statement_id = self._ensure_statement(
                    cur,
                    symbol,
                    statement_type_id,
                    report.get("fiscalDateEnding"),
                )
                if not statement_id:
                    continue

                line_items = self._prepare_line_items(
                    statement_id,
                    report,
                    dictionary_items,
                )
                if line_items:
                    execute_values(
                        cur,
                        """
                        INSERT INTO financial_oltp.financial_line_item
                        (statement_id, item_code, item_name, item_value, unit)
                        VALUES %s
                        """,
                        line_items,
                    )
        conn.commit()

    @staticmethod
    def _ensure_statement(
        cur,
        symbol: str,
        statement_type_id: int,
        fiscal_date: str | None,
    ) -> int | None:
        if not fiscal_date:
            return None
        fiscal_year = int(fiscal_date[:4])
        month = int(fiscal_date[5:7])
        quarter = f"Q{((month - 1) // 3) + 1}"
        cur.execute(
            """
            INSERT INTO financial_oltp.financial_statement
            (company_id, statement_type_id, fiscal_year, fiscal_quarter, report_date)
            VALUES (%s, %s, %s, %s, %s)
            ON CONFLICT (company_id, statement_type_id, fiscal_year, fiscal_quarter)
            DO NOTHING
            RETURNING statement_id
            """,
            (symbol, statement_type_id, fiscal_year, quarter, fiscal_date),
        )
        row = cur.fetchone()
        if row:
            return row[0]
        return None

    @staticmethod
    def _prepare_line_items(
        statement_id: int,
        report: Dict[str, str],
        dictionary_items: Dict[str, str],
    ) -> List[Tuple[int, str, str, float, str]]:
        items: List[Tuple[int, str, str, float, str]] = []
        for key, value in report.items():
            if key in {
                "fiscalDateEnding",
                "reportedCurrency",
                "filedDate",
                "acceptedDate",
                "period",
            }:
                continue
            if value in (None, "", "None"):
                continue
            try:
                numeric_value = float(value)
            except ValueError:
                continue

            # Only insert items that already exist in the dictionary
            if key not in dictionary_items:
                continue

            normalized_name = dictionary_items[key]
            items.append((statement_id, key, normalized_name, numeric_value, "USD"))
        return items

