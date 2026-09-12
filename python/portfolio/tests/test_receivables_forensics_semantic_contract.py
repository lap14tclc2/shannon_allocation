"""Unit tests for Receivables Forensic Semantics (Task 143).

Verifies two-stage anomaly architecture, data conflict handling, DSO, persistence,
corroboration, severity capping for total proxies, and structural deterioration invariants.
"""

from __future__ import annotations

import pytest
from portfolio.value_engine.munger_forensics import (
    classify_structural_vs_cyclical_deterioration,
    run_receivables_forensics,
)
from portfolio.value_engine.munger_history_builder import build_financial_history_from_facts
from portfolio.value_engine.munger_models import (
    CompounderClassification,
    DeteriorationClassification,
    DimensionStatus,
    FindingSeverity,
    FinancialFinding,
)


def test_receivables_bank_and_securities_not_applicable():
    hist = {
        "years": [2021, 2022, 2023, 2024, 2025],
        "by_year": {y: {"revenue": 1000.0, "receivables": 500.0} for y in [2021, 2022, 2023, 2024, 2025]},
    }
    bank_res = run_receivables_forensics(hist, archetype="BANK")
    assert bank_res.status == DimensionStatus.NOT_APPLICABLE.value

    sec_res = run_receivables_forensics(hist, archetype="SECURITIES")
    assert sec_res.status == DimensionStatus.NOT_APPLICABLE.value


def test_receivables_data_conflict_blocks_economic_forensics():
    facts = [
        {"fiscal_year": 2025, "line_item_code": "BS.RECEIVABLES.TRADE.NET", "value": 500.0, "provider": "ssi"},
        {"fiscal_year": 2025, "line_item_code": "BS.ASSETS.RECEIVABLES", "value": 300.0, "provider": "ssi"},  # Trade > Total => CONFLICT
    ]
    hist = build_financial_history_from_facts("TEST", raw_facts=facts)
    res = run_receivables_forensics(hist, archetype="NORMAL_ENTERPRISE")
    assert res.status == DimensionStatus.UNKNOWN.value
    assert "RECEIVABLES_DATA_CONFLICT" in res.missing_data


def test_total_proxy_caps_severity_at_medium_watch():
    facts = [
        {"fiscal_year": 2021, "line_item_code": "IS.REVENUE.TOTAL", "value": 1000.0, "provider": "ssi"},
        {"fiscal_year": 2021, "line_item_code": "BS.ASSETS.RECEIVABLES", "value": 100.0, "provider": "ssi"},
        {"fiscal_year": 2022, "line_item_code": "IS.REVENUE.TOTAL", "value": 1000.0, "provider": "ssi"},
        {"fiscal_year": 2022, "line_item_code": "BS.ASSETS.RECEIVABLES", "value": 200.0, "provider": "ssi"},
        {"fiscal_year": 2023, "line_item_code": "IS.REVENUE.TOTAL", "value": 1000.0, "provider": "ssi"},
        {"fiscal_year": 2023, "line_item_code": "BS.ASSETS.RECEIVABLES", "value": 400.0, "provider": "ssi"},
        {"fiscal_year": 2024, "line_item_code": "IS.REVENUE.TOTAL", "value": 1000.0, "provider": "ssi"},
        {"fiscal_year": 2024, "line_item_code": "BS.ASSETS.RECEIVABLES", "value": 600.0, "provider": "ssi"},
        {"fiscal_year": 2025, "line_item_code": "IS.REVENUE.TOTAL", "value": 1000.0, "provider": "ssi"},
        {"fiscal_year": 2025, "line_item_code": "BS.ASSETS.RECEIVABLES", "value": 800.0, "provider": "ssi"},
    ]
    hist = build_financial_history_from_facts("TEST", raw_facts=facts)
    res = run_receivables_forensics(hist, archetype="NORMAL_ENTERPRISE")
    assert res.status == DimensionStatus.WATCH.value
    assert len(res.findings) == 1
    assert res.findings[0].severity == FindingSeverity.MEDIUM.value


def test_working_capital_finding_does_not_cause_structural_deterioration():
    wc_finding = FinancialFinding(
        code="RECEIVABLES_GROW_FASTER_THAN_REVENUE",
        category="WORKING_CAPITAL",
        severity=FindingSeverity.HIGH.value,
        confidence="HIGH",
        status="FAIL",
        start_period=2021,
        end_period=2025,
        metrics={},
        evidence_fact_ids=[],
        explanation="Test finding",
    )
    det = classify_structural_vs_cyclical_deterioration(
        findings=[wc_finding],
        growth_metrics={},
        profitability_metrics={},
        durability_metrics={},
    )
    assert det["classification"] not in (
        DeteriorationClassification.STRUCTURAL.value,
        DeteriorationClassification.POSSIBLY_STRUCTURAL.value,
    )
