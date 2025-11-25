"""
Shared configuration helpers for ETL pipelines.
"""
import os
from typing import Any, Dict

from etl.common.env_loader import load_root_env

load_root_env()


def get_db_config() -> Dict[str, Any]:
    password = os.getenv("POSTGRES_PASSWORD")
    if not password:
        raise ValueError("POSTGRES_PASSWORD environment variable is required")
    return {
        "host": os.getenv("POSTGRES_HOST", "localhost"),
        "port": int(os.getenv("POSTGRES_PORT", "5432")),
        "dbname": os.getenv("POSTGRES_DB", "Web_quan_li_danh_muc"),
        "user": os.getenv("POSTGRES_USER", "postgres"),
        "password": password,
    }


def get_alpha_vantage_key() -> str:
    api_key = os.getenv("ALPHA_VANTAGE_API_KEY")
    if not api_key:
        raise ValueError("ALPHA_VANTAGE_API_KEY environment variable is required")
    return api_key

