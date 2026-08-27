from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_finance_period_policy_uses_ten_completed_fiscal_years():
    source = (ROOT / "python" / "portfolio" / "finance_catalog.py").read_text(encoding="utf-8")

    assert "FISCAL_YEAR_HISTORY = 10" in source
    assert "range(today.year - FISCAL_YEAR_HISTORY, today.year)" in source
    assert "ten completed FYs plus completed quarters" in source


def test_finance_period_policy_keeps_only_completed_current_year_quarters():
    source = (ROOT / "python" / "portfolio" / "finance_catalog.py").read_text(encoding="utf-8")

    assert 'quarter = ((today.month - 1) // 3)' in source
    assert "for q in range(1, quarter + 1)" in source
    assert "Include only completed quarters." in source
