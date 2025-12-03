"""
Environment variable helpers.
"""

from __future__ import annotations

import os
from typing import Iterable, Optional

from shared.python.utils.logging_config import get_logger

logger = get_logger(__name__)


def load_env(key: str, default: Optional[str] = None) -> Optional[str]:
    """
    Load environment variable with optional default.
    """
    value = os.getenv(key, default)
    if value is None:
        logger.debug("Environment variable '%s' not set; using default %s", key, default)
    return value


def validate_env(keys: Iterable[str]) -> None:
    """
    Ensure required environment variables are present.
    """
    missing = [key for key in keys if not os.getenv(key)]
    if missing:
        raise ValueError(f"Missing required environment variables: {', '.join(missing)}")


