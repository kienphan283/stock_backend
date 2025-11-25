"""
Central logging utilities for ETL modules.
"""
import logging
from typing import Optional

_configured = False


def configure_logging(level: int = logging.INFO) -> None:
    """
    Configure global logging once for all ETL modules.
    """
    global _configured
    if _configured:
        return

    logging.basicConfig(
        level=level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )
    _configured = True


def get_logger(name: Optional[str] = None) -> logging.Logger:
    """
    Helper to obtain a logger after ensuring logging is configured.
    """
    configure_logging()
    return logging.getLogger(name)

