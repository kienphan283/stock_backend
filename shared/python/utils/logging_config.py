"""
Shared logging configuration utilities.

Provides a consistent logger setup for all Python services without altering
log message content.
"""

from __future__ import annotations

import logging
import threading


LOG_FORMAT = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
LOG_LEVEL = logging.INFO

_configure_lock = threading.Lock()
_configured = False


def _configure_logging() -> None:
    global _configured
    if _configured:
        return
    with _configure_lock:
        if _configured:
            return
        logging.basicConfig(level=LOG_LEVEL, format=LOG_FORMAT)
        _configured = True


def get_logger(name: str) -> logging.Logger:
    """
    Return a logger with the shared configuration applied.
    """
    _configure_logging()
    return logging.getLogger(name)


