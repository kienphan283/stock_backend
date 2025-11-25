"""
Shared PostgreSQL helpers for ETL modules.
"""
import logging
from contextlib import contextmanager
from typing import Any, Dict, Generator, Optional

import psycopg2

logger = logging.getLogger(__name__)


class PostgresConnector:
    """
    Base class that manages a reusable psycopg2 connection.
    """

    def __init__(self, db_config: Dict[str, Any]):
        self.db_config = db_config
        self.conn: Optional[psycopg2.extensions.connection] = None

    def connect(self) -> psycopg2.extensions.connection:
        if self.conn is None or self.conn.closed:
            self.conn = psycopg2.connect(**self.db_config)
            logger.info(
                "Connected to PostgreSQL host=%s db=%s",
                self.db_config.get("host"),
                self.db_config.get("dbname") or self.db_config.get("database"),
            )
        return self.conn

    def close(self) -> None:
        if self.conn and not self.conn.closed:
            self.conn.close()
            logger.info("PostgreSQL connection closed")

    @contextmanager
    def cursor(self, *args, **kwargs) -> Generator[psycopg2.extensions.cursor, None, None]:
        conn = self.connect()
        cur = conn.cursor(*args, **kwargs)
        try:
            yield cur
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            cur.close()

