"""
Shared error handling helpers for external integrations.
"""

from __future__ import annotations

from typing import Any, Callable, Optional, TypeVar

from shared.python.utils.logging_config import get_logger

logger = get_logger(__name__)

T = TypeVar("T")
Fn = Callable[[], T]


def _log_error(kind: str, context: Optional[str], error: Exception) -> None:
    prefix = f"[{kind}]"
    suffix = f" ({context})" if context else ""
    logger.error(f"{prefix}{suffix} error: {error}")


def safe_redis_call(
    fn: Fn[T],
    *,
    context: Optional[str] = None,
    on_error: Optional[Callable[[Exception], None]] = None,
) -> Optional[T]:
    try:
        return fn()
    except Exception as exc:  # noqa: BLE001
        _log_error("Redis", context, exc)
        if on_error:
            on_error(exc)
        return None


def safe_kafka_call(
    fn: Fn[T],
    *,
    context: Optional[str] = None,
    on_error: Optional[Callable[[Exception], None]] = None,
) -> Optional[T]:
    try:
        return fn()
    except Exception as exc:  # noqa: BLE001
        _log_error("Kafka", context, exc)
        if on_error:
            on_error(exc)
        return None


def safe_db_call(
    fn: Fn[T],
    *,
    context: Optional[str] = None,
    on_error: Optional[Callable[[Exception], None]] = None,
) -> Optional[T]:
    try:
        return fn()
    except Exception as exc:  # noqa: BLE001
        _log_error("DB", context, exc)
        if on_error:
            on_error(exc)
        return None


