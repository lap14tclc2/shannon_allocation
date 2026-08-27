#!/usr/bin/env python3
"""Import prepared TCBS JSON files into the local Finance catalog."""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from python.portfolio.finance_catalog import (  # noqa: E402
    import_tcbs_crawled_directory,
)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Import prepared TCBS files from docs/crawled."
    )
    parser.add_argument("--directory", default="docs/crawled")
    parser.add_argument("--limit", type=int, default=0)
    parser.add_argument("--retry-failed-only", action="store_true")
    args = parser.parse_args()

    os.environ.setdefault("QPORT_FINANCE_RUNTIME", "worker")
    try:
        result = import_tcbs_crawled_directory(
            args.directory,
            limit=args.limit,
            retry_failed_only=args.retry_failed_only,
        )
    except Exception as exc:
        print(
            json.dumps(
                {"ok": False, "error": f"{type(exc).__name__}: {exc}"},
                ensure_ascii=False,
            )
        )
        return 1

    print(
        json.dumps(
            {
                "ok": result["ok"],
                "run_id": result["run_id"],
                "directory": result["directory"],
                "files": result["files"],
                "processed": result["processed"],
                "imported_documents": result["imported_documents"],
                "failed_documents": result["failed_documents"],
                "skipped_documents": result["skipped_documents"],
                "success_symbols": len(result["success_symbols"]),
                "failed_symbols": len(result["failed_symbols"]),
                "failed_sample": result["failed_symbols"][:20],
            },
            ensure_ascii=False,
        )
    )
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
