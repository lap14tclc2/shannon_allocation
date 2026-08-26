"""Contract tests for the Finance DB-first architecture.

These tests are intentionally provider/network independent: they validate the
normalizer and the source-level invariants that protect serverless runtime.
"""
from __future__ import annotations

import ast
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "python"))

from portfolio.finance_catalog import _periods, _value  # noqa: E402
from portfolio.dividend_reconciliation import _same_economics  # noqa: E402


def test_provider_label_value_rows_are_normalized():
    row = {"itemName": "Lợi nhuận sau thuế", "value": "1.234.567"}
    assert _value(row, "net profit after tax", "loi nhuan sau thue") == 1234567


def test_period_generation_excludes_current_incomplete_fy_and_quarterly_dividend_is_not_created():
    periods = _periods()
    current_year = __import__("datetime").date.today().year
    assert ("FY", current_year, None, f"{current_year}-12-31") not in periods
    assert any(period_type == "QUARTER" and year == current_year for period_type, year, _, _ in periods)
    source = (ROOT / "python" / "portfolio" / "finance_catalog.py").read_text(encoding="utf-8")
    assert 'if document_type == "DIVIDEND" and period_type != "FY":' in source


def test_user_valuation_route_is_database_only():
    source = (ROOT / "app" / "main.py").read_text(encoding="utf-8")
    tree = ast.parse(source)
    route = next(
        node for node in ast.walk(tree)
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        and node.name == "portfolio_symbol_valuation"
    )
    route_source = ast.get_source_segment(source, route) or ""
    assert "valuation_snapshot_from_catalog" in route_source
    assert "run_valuation_snapshot" not in route_source
    assert "vnstock" not in route_source.lower()
    assert "cafef" not in route_source.lower()
    assert "tcbs" not in route_source.lower()


def test_log_pagination_uses_sql_limit_offset_before_materialization():
    source = (ROOT / "python" / "portfolio" / "activity.py").read_text(encoding="utf-8")
    tree = ast.parse(source)
    page_fn = next(node for node in ast.walk(tree)
                    if isinstance(node, ast.FunctionDef) and node.name == "list_activity_page")
    page_source = ast.get_source_segment(source, page_fn) or ""
    assert "COUNT(*)" in page_source
    assert "ORDER BY occurred_at DESC, id DESC" in page_source
    assert "LIMIT ? OFFSET ?" in page_source

def test_dividend_reconciliation_detects_provider_mismatch():
    base = {"dividend_type": "CASH_DIVIDEND", "cash_per_share": 1000}
    assert _same_economics(base, {**base, "cash_per_share": 1000})
    assert not _same_economics(base, {**base, "cash_per_share": 1200})


def test_dividend_history_is_one_endpoint_per_provider_run():
    source = (ROOT / "python" / "portfolio" / "finance_catalog.py").read_text(encoding="utf-8")
    fetch = source[source.index("def crawl_symbol("):source.index("def enqueue_crawl_all(")]
    assert fetch.count('document_type == "DIVIDEND"') >= 1
    assert "latest_fy" in fetch
