"""Regression checks for clean rebuilds and CafeF data validation."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "python"))

from portfolio.finance_catalog import (
    ProviderPayloadError,
    _cafef_dividend_rows,
    _validate_cafef_payload,
)


def test_cafef_dividend_history_parser_extracts_cash_and_stock_events():
    payload = """
    <table>
      <tr><th>Ngày GDKHQ</th><th>Sự kiện</th><th>Giá trị</th></tr>
      <tr><td>21/07/2026</td><td>Cổ tức bằng Tiền</td><td>300 đ/cp</td></tr>
      <tr><td>01/09/2021</td><td>Thưởng bằng Cổ phiếu</td><td>5%</td></tr>
    </table>
    """
    rows = _cafef_dividend_rows(payload)
    assert rows == [
        {
            "ex_date": "2026-07-21",
            "raw_payload": {"cells": ["21/07/2026", "Cổ tức bằng Tiền", "300 đ/cp"]},
            "dividend_type": "CASH_DIVIDEND",
            "cash_per_share": 300,
        },
        {
            "ex_date": "2021-09-01",
            "raw_payload": {"cells": ["01/09/2021", "Thưởng bằng Cổ phiếu", "5%"]},
            "dividend_type": "STOCK_DIVIDEND",
            "stock_ratio": 5,
        },
    ]


def test_cafef_rejects_error_or_wrong_page_payload():
    try:
        _validate_cafef_payload(
            "<html><title>404 Not Found</title></html>",
            symbol="AAA",
            document_type="DIVIDEND",
        )
    except ProviderPayloadError as exc:
        assert "AAA" in str(exc)
    else:
        raise AssertionError("error page must not be accepted")


def test_cafef_finance_page_requires_numeric_rows():
    try:
        _validate_cafef_payload(
            "<html><body>Company overview only</body></html>",
            symbol="AAA",
            document_type="CASH_FLOW",
        )
    except ProviderPayloadError:
        pass
    else:
        raise AssertionError("wrong page must not be accepted")


def test_clear_all_command_is_explicit_and_covers_catalog_tables():
    root = Path(__file__).resolve().parents[1]
    script = (root / "scripts" / "finance_db.py").read_text(encoding="utf-8")
    catalog = (root / "python" / "portfolio" / "finance_catalog.py").read_text(encoding="utf-8")
    assert '"clear-all"' in script
    assert "args.confirm" in script
    for table in (
        "securities",
        "crawl_runs",
        "crawl_queue",
        "documents",
        "canonical_facts",
        "parse_errors",
        "dividend_observations",
        "dividend_canonical",
        "dividend_conflicts",
    ):
        assert f'"{table}"' in catalog
