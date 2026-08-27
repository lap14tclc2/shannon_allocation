from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "python"))

from portfolio.finance_catalog import _should_fetch_document  # noqa: E402


def test_incremental_crawl_skips_successful_documents():
    assert _should_fetch_document("SUCCESS", retry_failed_only=False) is False
    assert _should_fetch_document("SUCCESS", retry_failed_only=True) is False


def test_incremental_crawl_fetches_new_and_failed_documents():
    assert _should_fetch_document(None, retry_failed_only=False) is True
    assert _should_fetch_document("PENDING", retry_failed_only=False) is True
    assert _should_fetch_document("FAILED", retry_failed_only=False) is True


def test_retry_failed_only_does_not_fetch_pending_documents():
    assert _should_fetch_document("FAILED", retry_failed_only=True) is True
    assert _should_fetch_document("PENDING", retry_failed_only=True) is False
