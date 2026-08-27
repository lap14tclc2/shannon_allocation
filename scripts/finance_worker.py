#!/usr/bin/env python3
"""Local worker that consumes qport_finance.crawl_queue."""

from __future__ import annotations

import argparse
import os
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from python.portfolio.finance_catalog import (  # noqa: E402
    claim_next_crawl_job,
    crawl_symbol,
    finish_crawl_job,
)


def log(message: str) -> None:
    print(f"[finance-worker] {message}", flush=True)


def main() -> int:
    parser = argparse.ArgumentParser(description="Consume the QPort finance crawl queue.")
    parser.add_argument("--once", action="store_true", help="Process one job and exit.")
    parser.add_argument("--limit", type=int, default=0, help="Stop after N jobs; 0 means until empty.")
    parser.add_argument("--poll-seconds", type=float, default=5.0)
    parser.add_argument("--stale-after-seconds", type=int, default=900)
    parser.add_argument("--retry-failed-only", action="store_true")
    args = parser.parse_args()

    os.environ.setdefault("QPORT_FINANCE_RUNTIME", "worker")
    if os.environ.get("VERCEL"):
        log("refused: Vercel runtime is database-read-only")
        return 2

    processed = 0
    log(
        f"start limit={args.limit or 'until-empty'} "
        f"stale_after_seconds={args.stale_after_seconds}"
    )
    while True:
        if args.limit > 0 and processed >= args.limit:
            break
        job = claim_next_crawl_job(args.stale_after_seconds)
        if job is None:
            log(f"queue empty processed={processed}")
            return 0

        queue_id = int(job["id"])
        symbol = str(job["symbol"])
        log(f"claimed queue_id={queue_id} symbol={symbol}")
        try:
            result = crawl_symbol(
                symbol,
                job.get("requested_by"),
                retry_failed_only=args.retry_failed_only,
            )
            failures = int(result.get("failure_count") or 0)
            status = "COMPLETED" if result.get("ok") and failures == 0 else "FAILED"
            error = None if status == "COMPLETED" else (
                f"crawl failed: {failures} provider requests failed"
            )
            finish_crawl_job(queue_id, status=status, error=error)
            log(
                f"finished queue_id={queue_id} symbol={symbol} status={status} "
                f"success={result.get('success_count', 0)} "
                f"failed={failures} skipped={result.get('skipped_count', 0)}"
            )
        except Exception as exc:
            finish_crawl_job(
                queue_id,
                status="FAILED",
                error=f"{type(exc).__name__}: {exc}",
            )
            log(f"failed queue_id={queue_id} symbol={symbol} error={type(exc).__name__}")
        processed += 1
        if args.once:
            break
        if args.poll_seconds > 0:
            time.sleep(args.poll_seconds)

    log(f"stopped processed={processed}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
