from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_incremental_finance_resume_filters_complete_symbols():
    source = (ROOT / "python" / "portfolio" / "finance_catalog.py").read_text(encoding="utf-8")

    assert "_current_required_document_keys" in source
    assert "_has_missing_or_incomplete_documents" in source
    assert "skipped_complete" in source
    assert "NO_MISSING_DOCUMENTS" in source
    assert "status='SUCCESS'" in source
    assert "FOR UPDATE SKIP LOCKED" in source


def test_finance_database_clear_is_explicit_and_preserves_success_documents():
    source = (ROOT / "scripts" / "finance_db.py").read_text(encoding="utf-8")

    assert 'choices=("status", "clear-queue", "clear-incomplete")' in source
    assert "--confirm" in source
    catalog = (ROOT / "python" / "portfolio" / "finance_catalog.py").read_text(encoding="utf-8")
    assert "DELETE FROM documents WHERE status <> 'SUCCESS'" in catalog
    assert "stop finance workers before clearing" in catalog
