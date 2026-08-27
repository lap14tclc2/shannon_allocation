from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "python"))

from portfolio.finance_catalog import (  # noqa: E402
    ProviderPeriodUnavailableError,
    _provider_failure,
    _should_fetch_document,
    _tcbs_select_record,
)


def test_short_tcbs_history_is_not_a_payload_error():
    fixture = json.loads(
        (ROOT / "docs" / "crawled" / "AAH.json").read_text(encoding="utf-8")
    )
    try:
        _tcbs_select_record(
            json.dumps(fixture),
            symbol="AAH",
            document_type="INCOME_STATEMENT",
            period_type="FY",
            year=2019,
            quarter=None,
        )
    except ProviderPeriodUnavailableError as exc:
        code, detail, label = _provider_failure(exc)
    else:
        raise AssertionError("missing AAH FY:2019 must be classified as unavailable")

    assert code == "SOURCE_PERIOD_UNAVAILABLE"
    assert label == "not-available"
    assert "AAH FY:2019" in detail


def test_not_available_periods_are_not_requeued():
    assert _should_fetch_document("NOT_AVAILABLE", retry_failed_only=False) is False
    assert _should_fetch_document("NOT_AVAILABLE", retry_failed_only=True) is False


def test_prepared_file_import_tracks_unavailable_periods_separately():
    source = (ROOT / "python" / "portfolio" / "finance_catalog.py").read_text(
        encoding="utf-8"
    )
    assert '"NOT_AVAILABLE"' in source
    assert "_document_status_for_failure" in source
    assert "unavailable_documents" in source
    assert "file-unavailable" in source


def test_finance_catalog_exposes_unavailable_status_to_filtering():
    source = (ROOT / "python" / "portfolio" / "finance_catalog.py").read_text(
        encoding="utf-8"
    )
    assert "document_unavailable" in source
    assert '"NOT_AVAILABLE": (' in source
