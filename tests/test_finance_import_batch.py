from __future__ import annotations

import inspect
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "python"))

from portfolio import finance_catalog  # noqa: E402


def test_prepared_import_batches_document_writes_per_symbol():
    source = inspect.getsource(finance_catalog.import_tcbs_crawled_directory)
    assert "with _schema_connection(FINANCE_SCHEMA) as batch_db:" in source
    assert "db=batch_db" in source
    assert source.count("with _schema_connection(FINANCE_SCHEMA) as batch_db:") == 2


def test_save_document_can_reuse_a_batch_connection():
    source = inspect.getsource(finance_catalog._save_document)
    assert "db: Any | None = None" in source
    assert "nullcontext(db)" in source
    assert "_canonicalize_document(" in source
    assert "db=conn" in source


def test_batch_import_keeps_short_history_as_unavailable():
    fixture = json.loads(
        (ROOT / "docs" / "crawled" / "AAH.json").read_text(encoding="utf-8")
    )
    years = {
        int(row["year"])
        for row in fixture["data"]["incomestatement_year"]
        if row.get("quarter") == 5
    }
    assert years == {2020, 2021, 2022, 2023, 2024, 2025}
    source = (ROOT / "python" / "portfolio" / "finance_catalog.py").read_text(
        encoding="utf-8"
    )
    assert "unavailable_documents" in source
    assert 'document_status == "NOT_AVAILABLE"' in source
