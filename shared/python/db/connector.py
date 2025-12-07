# MODULE: Shared PostgreSQL connector.
# PURPOSE: Provide a unified way for Python services to obtain DB connections.

"""
Unified PostgreSQL connector for all Python services
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Optional

import psycopg2
from psycopg2.extensions import connection as PGConnection
from psycopg2.pool import SimpleConnectionPool
import logging

logger = logging.getLogger(__name__)


@dataclass
class PostgresConnector:
    """
    Unified PostgreSQL connector
    Used by market-api-service and market-stream-service
    """
    config: Dict[str, Any]
    pool: Optional[SimpleConnectionPool] = None
    min_conn: int = 1
    max_conn: int = 10

    def get_connection(self) -> PGConnection:
        """Get a database connection"""
        if self.pool:
            return self.pool.getconn()
        return psycopg2.connect(**self.config)

    def return_connection(self, conn: PGConnection):
        """Return connection to pool"""
        if self.pool:
            self.pool.putconn(conn)
        else:
            conn.close()

    def create_pool(self):
        """Create connection pool"""
        try:
            self.pool = SimpleConnectionPool(
                self.min_conn,
                self.max_conn,
                **self.config
            )
            logger.info(f"Connection pool created: {self.min_conn}-{self.max_conn} connections")
        except Exception as e:
            logger.error(f"Failed to create connection pool: {e}")
            raise

    def close_pool(self):
        """Close connection pool"""
        if self.pool:
            self.pool.closeall()
            logger.info("Connection pool closed")

