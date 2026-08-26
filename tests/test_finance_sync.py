from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("finance_sync", ROOT / "scripts" / "finance_sync.py")
finance_sync = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
SPEC.loader.exec_module(finance_sync)


def empty_catalog():
    return {table: [] for table in finance_sync.TABLE_ORDER}


def test_sync_covers_all_runtime_finance_tables():
    assert set(finance_sync.TABLE_ORDER) == {
        "crawl_runs",
        "crawl_queue",
        "securities",
        "documents",
        "canonical_facts",
        "parse_errors",
        "dividend_observations",
        "dividend_canonical",
        "dividend_conflicts",
    }


def test_validate_rows_rejects_empty_universe():
    with pytest.raises(RuntimeError, match="universe is empty"):
        finance_sync.validate_rows(empty_catalog())


def test_validate_rows_rejects_document_checksum_mismatch():
    data = empty_catalog()
    data["securities"] = [{"symbol": "FPT"}]
    data["documents"] = [{
        "id": 1,
        "symbol": "FPT",
        "provider": "tcbs",
        "status": "SUCCESS",
        "payload": "{}",
        "content_hash": "invalid",
    }]
    with pytest.raises(RuntimeError, match="checksum mismatch"):
        finance_sync.validate_rows(data)


def test_validate_rows_accepts_complete_minimal_catalog():
    data = empty_catalog()
    data["securities"] = [{"symbol": "FPT"}]
    data["documents"] = [{
        "id": 1,
        "symbol": "FPT",
        "provider": "tcbs",
        "status": "SUCCESS",
        "payload": "{}",
        "content_hash": "44136fa355b3678a1146ad16f7e8649e94fb4fc21fe77e8310c060f61caaff8a",
    }]
    data["canonical_facts"] = [{
        "symbol": "FPT",
        "provider": "tcbs",
        "quality_status": "SINGLE_SOURCE",
        "source_document_id": 1,
    }]
    data["dividend_observations"] = []
    data["dividend_canonical"] = []
    data["parse_errors"] = []
    data["dividend_conflicts"] = []
    finance_sync.validate_rows(data)
