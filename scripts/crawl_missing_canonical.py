#!/usr/bin/env python3
"""Crawl TCBS financial statements for symbols that have NO canonical facts.

Scans qport_finance.securities for active equities that currently have zero
rows in canonical_facts, then crawls each via finance_catalog.crawl_symbol
which writes both documents and canonical_facts into the catalog DB.
"""
from __future__ import annotations

import os
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "python"))

# Reuse the same bearer token used by the checked-in TCBS crawler, but allow an
# explicit TCBS_BEARER_TOKEN env override (checked-in tokens expire).
sys.path.insert(0, str(ROOT / "scripts"))
from crawl_tcbs_all import TOKEN  # noqa: E402

from portfolio.finance_catalog import crawl_symbol  # noqa: E402


def symbols_without_canonical_facts() -> list[str]:
    from portfolio.finance_catalog import FINANCE_SCHEMA, _schema_connection

    with _schema_connection(FINANCE_SCHEMA) as db:
        rows = db.execute(
            """
            SELECT s.symbol
            FROM securities s
            WHERE s.is_active = 1
              AND s.exchange IN ('HOSE','HNX','UPCOM')
              AND s.company_name IS NOT NULL
              AND NOT EXISTS (
                  SELECT 1 FROM canonical_facts cf WHERE cf.symbol = s.symbol
              )
            ORDER BY s.symbol
            """
        ).fetchall()
    return [str(r["symbol"]) for r in rows]


def main() -> int:
    os.environ["QPORT_FINANCE_RUNTIME"] = "local"
    token = os.environ.get("TCBS_BEARER_TOKEN") or TOKEN
    os.environ["TCBS_BEARER_TOKEN"] = token

    symbols = symbols_without_canonical_facts()
    print(f"[batch-crawl] symbols_without_canonical_facts={len(symbols)}", flush=True)
    if not symbols:
        print("[batch-crawl] nothing to do", flush=True)
        return 0

    ok: list[str] = []
    failed: list[str] = []
    for idx, symbol in enumerate(symbols, start=1):
        started = time.monotonic()
        try:
            result = crawl_symbol(symbol, requested_by=None)
            duration = time.monotonic() - started
            if result.get("ok"):
                ok.append(symbol)
                print(
                    f"[batch-crawl] OK {idx}/{len(symbols)} {symbol} "
                    f"({duration:.1f}s) success={result.get('success_count', 0)} "
                    f"failed={result.get('failure_count', 0)}",
                    flush=True,
                )
            else:
                failed.append(symbol)
                print(
                    f"[batch-crawl] FAIL {idx}/{len(symbols)} {symbol} "
                    f"code={result.get('code')} msg={result.get('message') or result.get('error') or ''}",
                    flush=True,
                )
        except Exception as exc:
            failed.append(symbol)
            print(
                f"[batch-crawl] ERROR {idx}/{len(symbols)} {symbol} "
                f"{type(exc).__name__}: {exc}",
                flush=True,
            )
        time.sleep(0.2)

    print(f"[batch-crawl] done ok={len(ok)} failed={len(failed)}", flush=True)
    print(f"[batch-crawl] failed_symbols={','.join(failed) or '-'}", flush=True)
    return 0 if not failed else 1


if __name__ == "__main__":
    raise SystemExit(main())