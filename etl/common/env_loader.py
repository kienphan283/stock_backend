"""
Environment loader for ETL modules.
Ensures the repository root .env (or fallback) is loaded exactly once.
"""
from pathlib import Path
from functools import lru_cache
from dotenv import load_dotenv
import logging

logger = logging.getLogger(__name__)


@lru_cache(maxsize=1)
def load_root_env() -> None:
    """
    Load environment variables from the repository root .env file.
    Falls back to .env.local or .env.example if needed.
    """
    root_dir = Path(__file__).resolve().parents[2]
    candidates = [
        root_dir / ".env",
        root_dir / ".env.local",
        root_dir / ".env.example",
    ]

    for path in candidates:
        if path.exists():
            load_dotenv(path)
            if path.name != ".env":
                logger.warning(
                    "Loaded environment variables from %s. "
                    "Consider copying it to a dedicated .env file for local runs.",
                    path,
                )
            return

    logger.warning(
        "No .env/.env.local/.env.example file found at %s. "
        "Environment variables must be provided by the shell.",
        root_dir,
    )

