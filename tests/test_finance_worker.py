from __future__ import annotations

import inspect
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "python"))

from portfolio import finance_catalog  # noqa: E402


def test_worker_queue_claim_and_finish_api_exists():
    assert callable(finance_catalog.claim_next_crawl_job)
    assert callable(finance_catalog.finish_crawl_job)
    assert "RUNNING" in inspect.getsource(finance_catalog.claim_next_crawl_job)
    assert "SECURITY_NOT_CRAWLABLE" in inspect.getsource(finance_catalog.claim_next_crawl_job)


def test_worker_script_is_local_and_processes_claimed_jobs():
    script = (ROOT / "scripts" / "finance_worker.py").read_text(encoding="utf-8")
    assert "claim_next_crawl_job" in script
    assert "crawl_symbol" in script
    assert "finish_crawl_job" in script
    assert "Vercel runtime is database-read-only" in script
