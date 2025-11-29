"""
Lightweight PostgreSQL connector utilities shared across ETL jobs.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict

import psycopg2
from psycopg2.extensions import connection as PGConnection


@dataclass
class PostgresConnector:
    config: Dict[str, Any]

    def get_connection(self) -> PGConnection:
        return psycopg2.connect(**self.config)



