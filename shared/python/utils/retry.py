"""
Retry utilities with exponential backoff.
"""

from __future__ import annotations

import functools
import time
from typing import Any, Callable, TypeVar

from shared.python.utils.logging_config import get_logger

logger = get_logger(__name__)

T = TypeVar("T")


def retryable(max_retries: int = 3, backoff_seconds: int = 1) -> Callable[[Callable[..., T]], Callable[..., T]]:
    """
    Decorator providing simple exponential backoff retry behavior.
    """

    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> T:
            attempt = 0
            delay = backoff_seconds

            while True:
                try:
                    return func(*args, **kwargs)
                except Exception as exc:  # noqa: BLE001
                    attempt += 1
                    if attempt >= max_retries:
                        logger.error(
                            "Retryable operation '%s' failed after %s attempts: %s",
                            func.__name__,
                            attempt,
                            exc,
                        )
                        raise
                    logger.warning(
                        "Retryable operation '%s' failed (attempt %s/%s): %s. Retrying in %ss",
                        func.__name__,
                        attempt,
                        max_retries,
                        exc,
                        delay,
                    )
                    time.sleep(delay)
                    delay *= 2

        return wrapper

    return decorator


