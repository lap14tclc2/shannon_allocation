"""Unit tests for Buffett/Munger Business Review & Value Trap Gate (T07, T07A-J)."""

import pytest
from portfolio.value_engine.business_review import evaluate_business_review
from portfolio.value_engine.value_trap import evaluate_value_trap


def test_business_review_high_quality_company_with_evidence():
    val = {
        "understandability": "PASS",
        "quality_tier": "HIGH_QUALITY",
        "financial_strength_score": 85,
        "owner_earnings": 100_000_000_000,
        "earnings_durability": "PASS",
        "moat_strength": "WIDE",
        "management_capital_allocation": "PASS",
        "accounting_reliability": "PASS",
        "hard_rejects": [],
    }

    res = evaluate_business_review("FPT", valuation_report=val)

    assert res.symbol == "FPT"
    assert res.understandability == "PASS"
    assert res.business_quality == "PASS"
    assert res.financial_strength == "PASS"
    assert res.earnings_durability == "PASS"
    assert res.moat == "PASS"
    assert res.management_capital_allocation == "PASS"
    assert res.accounting_reliability == "PASS"
    assert res.overall_status == "BUSINESS_PASS"


def test_business_review_single_positive_owner_earnings_not_automatic_pass():
    """BLOCKER 4: Single positive owner earnings without history must NOT evaluate to PASS."""
    val = {
        "understandability": "PASS",
        "quality_tier": "HIGH_QUALITY",
        "financial_strength_score": 80,
        "owner_earnings": 50_000_000,  # Single positive value, no history
        "moat_strength": "WIDE",
        "management_capital_allocation": "PASS",
        "accounting_reliability": "PASS",
    }

    res = evaluate_business_review("SINGLE_OE", valuation_report=val)
    assert res.earnings_durability != "PASS"
    assert res.earnings_durability == "WATCH"


def test_value_trap_missingness_preservation():
    """BLOCKER 3: Missing receivables/inventory must NOT be treated as zero or calculate fake growth."""
    history = [
        {"net_income": 100, "cfo": 110},  # Missing revenue, receivables, inventory
        {"net_income": 120, "cfo": 130},
    ]
    val = {
        "current_price": 10000,
        "bear_iv": 12000,
        "base_iv": 20000,
        "dilution_status": "STABLE",
        "accounting_reliability": "PASS",
        "financial_strength": "PASS",
    }

    res = evaluate_value_trap("MISSING_DATA_CO", valuation_report=val, financial_history=history)
    assert "REVENUE_HISTORY" in res.missing_data
    assert "RECEIVABLES_HISTORY" in res.missing_data
    assert "INVENTORY_HISTORY" in res.missing_data


def test_value_trap_structural_classification_does_not_overstate():
    """BLOCKER 6: Quantitative warnings alone should produce POSSIBLY_STRUCTURAL/WATCH, not STRUCTURAL_EVIDENCE."""
    val = {
        "current_price": 10000,
        "bear_iv": 12000,
        "base_iv": 20000,
        "cfo_to_net_income": 0.9,
        "dilution_status": "STABLE",
        "accounting_reliability": "PASS",
        "financial_strength": "PASS",
        "return_on_capital_trend": "DECLINING",  # Soft warning 1
        "normalized_earnings_trend": "DECLINING",  # Soft warning 2
    }

    res = evaluate_value_trap("SOFT_WARN_CO", valuation_report=val)
    assert res.deterioration_classification == "POSSIBLY_STRUCTURAL"
    assert res.status == "WATCH"
    assert res.status != "HIGH_RISK"


def test_value_trap_uses_financial_history():
    """Invariant: Value trap gate evaluates multi-year CFO/NI and earnings trend from history."""
    history = [
        {"net_income": 100, "cfo": 110, "revenue": 500},
        {"net_income": 120, "cfo": 130, "revenue": 550},
        {"net_income": 150, "cfo": 160, "revenue": 650},
    ]
    val = {
        "current_price": 10000,
        "bear_iv": 12000,
        "base_iv": 20000,
        "dilution_status": "STABLE",
        "accounting_reliability": "PASS",
        "financial_strength": "PASS",
        "hard_rejects": [],
    }

    res = evaluate_value_trap("GROWTH_CO", valuation_report=val, financial_history=history)

    assert res.normalized_earnings_trend == "GROWING"
    assert res.cash_conversion_status == "CONFIRMED"
    assert res.status == "CLEAR"
