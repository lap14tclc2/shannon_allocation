from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_finance_documents_deduplicate_nullable_fiscal_quarter():
    source = (ROOT / "python" / "portfolio" / "finance_catalog.py").read_text(encoding="utf-8")

    assert "documents_deduplicate_v1" in source
    assert "uq_finance_documents_logical_period" in source
    assert "COALESCE(fiscal_quarter, 0)" in source
    assert "FIRST_VALUE(id) OVER" in source
    assert "UPDATE canonical_facts SET source_document_id=?" in source
    assert "UPDATE parse_errors SET source_document_id=?" in source
    assert source.count("ON CONFLICT (symbol, provider, document_type, period_type, fiscal_year, (COALESCE(fiscal_quarter, 0)))") == 2


def test_finance_worker_claim_serializes_concurrent_workers():
    source = (ROOT / "python" / "portfolio" / "finance_catalog.py").read_text(encoding="utf-8")

    claim = source[source.index("def claim_next_crawl_job"):source.index("def finish_crawl_job")]
    assert "FOR UPDATE SKIP LOCKED" in claim
    assert "WHERE id=? AND status='QUEUED'" in claim
