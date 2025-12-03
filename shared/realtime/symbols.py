"""
Shared symbol / ticker configuration for realtime services.

This module centralizes default symbol lists used by streaming services.
Logic for parsing / normalizing environment variables remains in the
individual services' settings modules; only the constant values are shared.
"""

from typing import List

# NOTE:
# The ingest service previously hardcoded DEFAULT_SYMBOLS = ["AAPL", "MSFT", "GOOGL"].
# We preserve that exact list here to avoid any behavior change.

INGEST_DEFAULT_SYMBOLS: List[str] = ["AAPL", "MSFT", "GOOGL"]



