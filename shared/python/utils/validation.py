"""
Shared validation helpers for backend services.

Centralizes basic symbol/ticker validation to avoid duplicate regex checks
across FastAPI and streaming services.
"""

from __future__ import annotations

import re
from typing import Iterable, List, Tuple


# Allow indices starting with ^ (e.g. ^GSPC) and increase max length
_SYMBOL_RE = re.compile(r"^[\^A-Z][A-Z0-9\.\-]{0,19}$")


class ValidationError(ValueError):
    """Raised when validation fails for client-provided data."""


def normalize_symbol(symbol: str) -> str:
    """Normalize and validate a single symbol."""
    candidate = (symbol or "").strip().upper()
    if not candidate or not _SYMBOL_RE.match(candidate):
        raise ValidationError(f"Invalid symbol: {symbol}")
    return candidate


def normalize_symbols(symbols: Iterable[str]) -> List[str]:
    """
    Normalize and validate an iterable of symbols, returning a de-duplicated list
    while preserving the original order of first appearance.
    """
    seen = set()
    normalized: List[str] = []
    for raw in symbols:
        cleaned = normalize_symbol(raw)
        if cleaned not in seen:
            seen.add(cleaned)
            normalized.append(cleaned)
    if not normalized:
        raise ValidationError("At least one valid symbol is required")
    return normalized


def parse_symbols_csv(csv_symbols: str) -> List[str]:
    """Parse a comma-separated string of symbols into a validated list."""
    parts = [s for s in (csv_symbols or "").split(",") if s.strip()]
    return normalize_symbols(parts)


