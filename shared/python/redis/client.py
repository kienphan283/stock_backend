"""
Shared Redis client helper for Python services.

This module provides a thin factory for creating Redis connections. It is
intentionally minimal so that callers can preserve their existing behavior by
passing through the same arguments they used previously.
"""

from __future__ import annotations

from typing import Any

import redis


def get_redis_connection(
    *,
    host: str,
    port: int,
    db: int = 0,
    decode_responses: bool = True,
    **kwargs: Any,
) -> redis.Redis:
    """
    Create a Redis client with the given connection parameters.

    Callers are expected to pass the same arguments they historically used when
    constructing redis.Redis instances directly. This helper does not alter any
    defaults beyond what is explicitly provided via arguments.
    """

    return redis.Redis(
        host=host,
        port=port,
        db=db,
        decode_responses=decode_responses,
        **kwargs,
    )


