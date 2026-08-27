#!/usr/bin/env python3
"""Probe the authenticated TCBS statement history endpoints safely."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from python.portfolio.finance_catalog import (  # noqa: E402
    TCBS_FINANCE_ENDPOINTS,
    _fetch_tcbs_history,
    _tcbs_records,
)


def main() -> int:
    parser = argparse.ArgumentParser(description="Probe TCBS finance history endpoints.")
    parser.add_argument("--symbol", default="MWG")
    args = parser.parse_args()
    symbol = str(args.symbol).upper().strip()
    if not symbol:
        parser.error("--symbol must not be empty")

    failures = 0
    print(f"[tcbs-probe] start symbol={symbol}", flush=True)
    for document_type in (
        "CASH_FLOW",
        "FINANCIAL_STATEMENTS",
        "INCOME_STATEMENT",
    ):
        try:
            url, payload = _fetch_tcbs_history(symbol, document_type)
            records = _tcbs_records(payload)
            years = sorted({
                int(row["year"])
                for row in records
                if str(row.get("year") or "").strip().isdigit()
            })
            fields = sorted({
                str(key)
                for row in records[:3]
                for key in row.keys()
            })
            print(
                f"[tcbs-probe] success document={document_type} "
                f"endpoint={TCBS_FINANCE_ENDPOINTS[document_type]} "
                f"records={len(records)} "
                f"years={years[0] if years else '-'}..{years[-1] if years else '-'} "
                f"fields={','.join(fields[:20]) or '-'}",
                flush=True,
            )
        except Exception as exc:
            failures += 1
            print(
                f"[tcbs-probe] failed document={document_type} "
                f"error={type(exc).__name__}: {str(exc)[:200]}",
                flush=True,
            )
    print(f"[tcbs-probe] completed failures={failures}", flush=True)
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
