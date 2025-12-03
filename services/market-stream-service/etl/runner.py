"""
Unified ETL runner for on-demand batch jobs.

Usage examples:
    python etl/runner.py bctc
    python etl/runner.py eod
    python etl/runner.py financial
    python etl/runner.py all
"""

from __future__ import annotations

import argparse
import sys
from typing import Callable, Dict, List, Optional

from etl.bctc.pipeline import run as run_bctc
from etl.eod.pipeline import run as run_eod


PipelineFunc = Callable[..., None]


def parse_args(argv: Optional[List[str]]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run ETL batch pipelines on demand.",
    )
    parser.add_argument(
        "job",
        choices=["bctc", "financial", "eod", "all"],
        help="Pipeline to execute (use 'all' to run every pipeline sequentially).",
    )
    parser.add_argument("--symbol", type=str, help="Ticker symbol to process.")
    parser.add_argument("--date", type=str, help="ISO date (YYYY-MM-DD).")
    parser.add_argument("--limit", type=int, help="Record limit for batch operations.")
    return parser.parse_args(argv)


def execute_bctc(symbol: Optional[str], limit: Optional[int]) -> None:
    print(f"[runner] Running BCTC pipeline (symbol={symbol}, limit={limit})")
    run_bctc(symbol=symbol, limit=limit)


def execute_eod(symbol: Optional[str], date: Optional[str], limit: Optional[int]) -> None:
    print(f"[runner] Running EOD pipeline (symbol={symbol}, date={date}, limit={limit})")
    run_eod(symbol=symbol, date=date, limit=limit)


def main(argv: Optional[List[str]] = None) -> int:
    args = parse_args(argv or sys.argv[1:])

    if args.job == "bctc":
        execute_bctc(args.symbol, args.limit)
    elif args.job == "eod":
        execute_eod(args.symbol, args.date, args.limit)
    elif args.job == "financial":
        print("[runner] Financial ETL not implemented yet.")
    elif args.job == "all":
        execute_bctc(args.symbol, args.limit)
        execute_eod(args.symbol, args.date, args.limit)
    else:
        print(f"[runner] Unknown job '{args.job}'")
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

