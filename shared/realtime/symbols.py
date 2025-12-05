"""
Shared symbol / ticker configuration for realtime services.

This module centralizes default symbol lists used by streaming services.
Logic for parsing / normalizing environment variables remains in the
individual services' settings modules; only the constant values are shared.
"""

from typing import List
import sys
from pathlib import Path

# Import DEFAULT_TICKERS from shared constants
# Add parent directory to path to allow import
SHARED_PATH = Path(__file__).resolve().parent.parent
if str(SHARED_PATH) not in sys.path:
    sys.path.insert(0, str(SHARED_PATH))

from shared.constants.tickers import DEFAULT_TICKERS

# Use all 30 tickers from DEFAULT_TICKERS for realtime ingest
INGEST_DEFAULT_SYMBOLS: List[str] = DEFAULT_TICKERS.copy()
