"""Task 131 Runtime Evidence Data Completeness Audit Test Suite."""

from __future__ import annotations

import os
from decimal import Decimal
import pytest

from portfolio.canonical_valuation import build_canonical_valuation
from portfolio.value_engine.business_review import evaluate_business_review
from portfolio.value_engine.value_trap import evaluate_value_trap


def test_acb_bank_archetype_isolation():
    """Verify that ACB (bank) evaluates ROIC as NOT_APPLICABLE and is not penalized by enterprise-only facts."""
    val = {
        "symbol": "ACB",
        "is_bank": True,
        "archetype": "BANK",
        "current_price": 22250.0,
        "bear_iv": 18117.0,
        "base_iv": 27056.0,
        "value_investor_pillars": {
            "financial_fortress": {"status": "FORTRESS"},
            "earnings_quality": {"status": "EXCELLENT", "avg_roe_5y": 20.8},
            "capital_allocation": {"status": "EXCELLENT", "dilution_classification": "NON_ECONOMIC_SHARE_CHANGE"},
        },
    }
    vt = evaluate_value_trap("ACB", val)
    assert vt.return_on_capital_trend == "NOT_APPLICABLE"
    assert "ROIC_HISTORICAL_SERIES" not in vt.missing_data
    assert "INVENTORY_HISTORY" not in vt.missing_data
    assert "RECEIVABLES_HISTORY" not in vt.missing_data
    assert vt.balance_sheet_status == "SAFE"
    assert vt.accounting_status == "PASS"
    assert vt.dilution_status == "OK"


def test_qualitative_evidence_boundaries_moat_understandability():
    """Verify that absent Moat and Understandability evidence stay UNKNOWN (not fabricated into PASS)."""
    val = {
        "symbol": "FPT",
        "quality_tier": "HIGH_QUALITY",
        "value_investor_pillars": {
            "financial_fortress": {"status": "FORTRESS"},
            "earnings_quality": {"status": "EXCELLENT"},
            "capital_allocation": {"status": "EXCELLENT"},
        },
    }
    biz = evaluate_business_review("FPT", val)
    assert biz.understandability == "UNKNOWN"
    assert biz.moat == "UNKNOWN"
    assert biz.business_quality == "PASS"
    assert biz.financial_strength == "PASS"
    assert "UNDERSTANDABILITY" in biz.missing_dimensions
    assert "MOAT" in biz.missing_dimensions
    assert any("Circle of Competence" in r for r in biz.reasons)
    assert any("Moat" in r for r in biz.reasons)


def test_accounting_numeric_quality_separated_from_governance():
    """Quantitative accounting quality can PASS while qualitative governance remains UNKNOWN."""
    val = {
        "symbol": "DGC",
        "value_investor_pillars": {
            "earnings_quality": {"status": "EXCELLENT", "avg_cash_conversion_5y": 95.0},
        },
    }
    biz = evaluate_business_review("DGC", val)
    assert biz.accounting_reliability == "PASS"


def test_base_iv_attractive_with_unprotected_bear_case_yields_watch():
    """Base MOS attractive but Bear IV protection weak MUST result in WATCH, not CLEAR or BUY."""
    val = {
        "symbol": "ACB",
        "is_bank": True,
        "current_price": 22250.0,
        "base_iv": 27056.0,
        "bear_iv": 18117.0,  # price > bear_iv
        "value_investor_pillars": {
            "financial_fortress": {"status": "FORTRESS"},
            "earnings_quality": {"status": "EXCELLENT"},
            "capital_allocation": {"status": "EXCELLENT"},
        },
    }
    vt = evaluate_value_trap("ACB", val)
    assert vt.bear_case_protection == "UNPROTECTED"
    assert vt.status == "WATCH"
    assert any("kịch bản Thận trọng" in r for r in vt.reasons)


def test_dgc_cyclicality_not_classified_as_permanent_structural_impairment():
    """Cyclical profit fluctuations should be LIKELY_CYCLICAL, not STRUCTURAL_EVIDENCE."""
    val = {
        "symbol": "DGC",
        "is_bank": False,
        "current_price": 47000.0,
        "base_iv": 107169.0,
        "bear_iv": 75391.0,
        "value_investor_pillars": {
            "financial_fortress": {"status": "STRONG"},
            "earnings_quality": {"status": "EXCELLENT"},
            "capital_allocation": {"status": "EXCELLENT"},
        },
        "financial_history": [
            {"net_income": 1000, "cfo": 1200},
            {"net_income": 6000, "cfo": 5500},
            {"net_income": 3000, "cfo": 2800},
        ],
    }
    vt = evaluate_value_trap("DGC", val)
    assert vt.deterioration_classification in ("UNKNOWN", "LIKELY_CYCLICAL")
    assert vt.status == "CLEAR"


def test_genuine_insufficient_evidence_yields_insufficient_data():
    """When critical solvency and accounting facts are missing, status MUST be INSUFFICIENT_DATA."""
    val = {
        "symbol": "XYZ",
        "current_price": 10000.0,
        # No pillars, no solvency facts, no accounting facts
    }
    vt = evaluate_value_trap("XYZ", val)
    assert vt.status == "INSUFFICIENT_DATA"
    assert len(vt.missing_data) >= 2


@pytest.mark.skipif(not os.environ.get("DATABASE_URL"), reason="Requires PostgreSQL database connection")
def test_runtime_evidence_chain_acb_dgc_fpt():
    """Regression test for ACB, DGC, FPT canonical valuation and evidence propagation against DB."""
    from portfolio.finance_catalog import _schema_connection, FINANCE_SCHEMA

    with _schema_connection(FINANCE_SCHEMA) as conn:
        for sym, px in [("ACB", 22250.0), ("DGC", 47000.0), ("FPT", 72400.0)]:
            val = build_canonical_valuation(sym, market_price=px)
            assert val.get("ok") is True, f"Canonical valuation failed for {sym}"
            assert val.get("base_iv") is not None, f"Base IV missing for {sym}"

            biz = evaluate_business_review(sym, val)
            assert biz.business_quality in ("PASS", "WATCH", "UNKNOWN")
            assert biz.financial_strength in ("PASS", "SAFE", "WATCH")


            vt = evaluate_value_trap(sym, val)
            assert vt.status in ("CLEAR", "WATCH")
            if sym == "ACB":
                assert len(vt.missing_data) == 0, f"ACB bank should have zero missing data, got: {vt.missing_data}"
            else:
                assert "ROIC_HISTORICAL_SERIES" not in vt.missing_data, f"ROIC history should be populated for {sym}"
                assert vt.status in ("CLEAR", "WATCH")
