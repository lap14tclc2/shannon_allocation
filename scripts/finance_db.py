#!/usr/bin/env python3
"""Inspect or safely reset the local finance database."""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from python.portfolio.finance_catalog import (  # noqa: E402
    clear_all_finance_data,
    clear_finance_queue,
    clear_provider_finance_data,
    clear_incomplete_finance_data,
    finance_database_status,
)


def main() -> int:
    parser = argparse.ArgumentParser(description="Inspect/reset qport_finance.")
    parser.add_argument(
        "command",
        choices=("status", "clear-queue", "clear-incomplete", "clear-cafef", "clear-all"),
    )
    parser.add_argument(
        "--confirm",
        action="store_true",
        help="Required for destructive clear commands.",
    )
    args = parser.parse_args()

    os.environ.setdefault("QPORT_FINANCE_RUNTIME", "worker")
    if args.command == "status":
        print(finance_database_status())
        return 0
    if not args.confirm:
        parser.error("--confirm is required for clear commands")
    if args.command == "clear-queue":
        print(clear_finance_queue())
    elif args.command == "clear-incomplete":
        print(clear_incomplete_finance_data())
    elif args.command == "clear-cafef":
        print(clear_provider_finance_data("cafef"))
    else:
        print(clear_all_finance_data())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
