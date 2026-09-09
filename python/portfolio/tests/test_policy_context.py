"""Unit tests for InvestmentDecisionContext and context builder."""

import pytest
from portfolio.policy.models import InvestmentDecisionContext
from portfolio.policy.context_builder import build_decision_context


def test_investment_decision_context_serialization():
    ctx = InvestmentDecisionContext(
        symbol="FPT",
        current_weight=0.15,
        current_market_value=150_000_000,
        quality_score=85.0,
        quality_tier="HIGH_QUALITY",
        base_iv=150000.0,
        current_price=120000.0,
        actual_mos=20.0,
        required_mos=15.0,
        survival_reserve_status="SAFE",
        available_long_term_capital=500_000_000.0,
        business_review_status="PASS",
        value_trap_status="CLEAR",
    )

    d = ctx.to_dict()
    assert d["symbol"] == "FPT"
    assert d["current_weight"] == 0.15
    assert d["quality_tier"] == "HIGH_QUALITY"
    assert d["available_long_term_capital"] == 500_000_000.0

    restored = InvestmentDecisionContext.from_dict(d)
    assert restored.symbol == "FPT"
    assert restored.quality_score == 85.0
    assert restored.survival_reserve_status == "SAFE"


def test_build_decision_context_with_all_reports():
    holding = {"weight": 0.20, "market_value": 200_000_000, "quantity": 1500, "cost_basis": 110000}
    valuation = {
        "price": 130000,
        "bear_iv": 110000,
        "base_iv": 160000,
        "bull_iv": 200000,
        "required_mos": 15.0,
        "actual_mos": 18.75,
        "valuation_confidence": "HIGH",
        "model_status": "VALID",
        "quality_score": 88,
        "quality_tier": "HIGH_QUALITY",
    }
    business = {
        "circle_of_competence": "PASS",
        "accounting_reliability": "PASS",
        "financial_strength": "PASS",
        "earnings_durability": "PASS",
        "capital_allocation_quality": "PASS",
        "moat_assessment": "PASS",
        "status": "PASS",
    }
    value_trap = {"status": "CLEAR", "flags": []}
    pf = {
        "survival_reserve_status": "SAFE",
        "available_long_term_capital": 300_000_000,
        "near_term_liability_status": "COVERED",
    }

    ctx = build_decision_context(
        symbol="FPT",
        holding=holding,
        valuation=valuation,
        personal_finance=pf,
        business_review=business,
        value_trap=value_trap,
    )

    assert ctx.symbol == "FPT"
    assert ctx.current_weight == 0.20
    assert ctx.base_iv == 160000
    assert ctx.circle_of_competence == "PASS"
    assert ctx.value_trap_status == "CLEAR"
    assert ctx.available_long_term_capital == 300_000_000
    assert ctx.data_readiness["financial_core"] == "READY"
    assert len(ctx.missing_data) == 0


def test_build_decision_context_missing_reports_degrades_gracefully():
    ctx = build_decision_context(symbol="ACB")

    assert ctx.symbol == "ACB"
    assert ctx.current_weight == 0.0
    assert ctx.model_status == "INVALID"
    assert ctx.business_review_status == "UNKNOWN"
    assert ctx.value_trap_status == "INSUFFICIENT_DATA"
    assert ctx.survival_reserve_status == "UNKNOWN"
    assert ctx.available_long_term_capital == 0.0
    assert "VALUATION_REPORT" in ctx.missing_data
    assert "PERSONAL_FINANCE" in ctx.missing_data
