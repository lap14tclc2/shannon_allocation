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


def test_business_review_missing_evidence_returns_unknown():
    """Invariant: Missing qualitative evidence must remain UNKNOWN and not silently default to PASS."""
    val = {
        "quality_tier": "HIGH_QUALITY",
        # Understandability, management, accounting, moat missing!
    }

    res = evaluate_business_review("UNKNOWN_CO", valuation_report=val)

    assert res.understandability == "UNKNOWN"
    assert res.moat == "UNKNOWN"
    assert res.management_capital_allocation == "UNKNOWN"
    assert res.accounting_reliability == "UNKNOWN"
    assert res.overall_status == "BUSINESS_REVIEW"
    assert "UNDERSTANDABILITY" in res.missing_dimensions
    assert "ACCOUNTING_RELIABILITY" in res.missing_dimensions


def test_business_review_solvency_risk_fails():
    val = {
        "understandability": "PASS",
        "quality_tier": "HIGH_QUALITY",
        "financial_strength_score": 20,
        "hard_rejects": ["SOLVENCY_RISK"],
    }

    res = evaluate_business_review("ACB", valuation_report=val)

    assert res.financial_strength == "FAIL"
    assert res.overall_status == "BUSINESS_FAIL"
    assert "Rủi ro khả năng thanh toán / nợ cao." in res.reasons


def test_value_trap_gate_clear_for_healthy_valuation():
    val = {
        "current_price": 120000,
        "bear_iv": 130000,
        "base_iv": 160000,
        "cfo_to_net_income": 1.1,
        "dilution_status": "STABLE",
        "accounting_reliability": "PASS",
        "financial_strength": "PASS",
        "normalized_earnings_trend": "STABLE",
        "hard_rejects": [],
    }

    res = evaluate_value_trap("FPT", valuation_report=val)

    assert res.symbol == "FPT"
    assert res.status == "CLEAR"
    assert res.earnings_quality == "CONFIRMED"
    assert res.bear_case_protection == "PROTECTED"
    assert len(res.structural_deterioration_flags) == 0


def test_value_trap_gate_high_risk_on_insolvency_or_accounting_failure():
    """Invariant: Solvency risk or accounting failure MUST trigger HIGH_RISK status."""
    val = {
        "current_price": 5000,  # Appears very cheap
        "base_iv": 20000,
        "cfo_to_net_income": 0.2,
        "dilution_status": "DESTRUCTIVE_DILUTION",
        "hard_rejects": ["SOLVENCY_RISK", "ACCOUNTING_UNRELIABLE"],
    }

    res = evaluate_value_trap("TRAP", valuation_report=val)

    assert res.status == "HIGH_RISK"
    assert res.accounting_status == "FAIL"
    assert res.balance_sheet_status == "SOLVENCY_RISK"
    assert res.deterioration_classification == "STRUCTURAL_EVIDENCE"
    assert len(res.structural_deterioration_flags) >= 2


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
