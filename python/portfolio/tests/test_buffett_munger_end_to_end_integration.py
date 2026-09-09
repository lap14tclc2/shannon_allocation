"""End-to-end integration test suite for the complete Buffett/Munger decision pipeline.

Flow:
financial facts → valuation report → BusinessReviewResult → ValueTrapAssessment → PersonalBalanceSheet → InvestmentDecisionContext → evaluate_decision()

Fixtures for representative tickers: ACB, DGC, FPT.
"""

import pytest
from portfolio.personal_finance.models import PersonalBalanceSheetInput
from portfolio.personal_finance.service import calculate_capital_durability
from portfolio.policy.context_builder import build_decision_context
from portfolio.policy.engine import evaluate_decision
from portfolio.value_engine.business_review import evaluate_business_review
from portfolio.value_engine.value_trap import evaluate_value_trap


def test_full_pipeline_fpt_fully_qualified_buy():
    """FPT: MODEL_VERIFIED + fully qualified evidence + SAFE fortress => BUY decision."""
    valuation = {
        "symbol": "FPT",
        "current_price": 100000,
        "bear_iv": 110000,
        "base_iv": 140000,
        "bull_iv": 180000,
        "required_mos": 15.0,
        "actual_mos": 28.57,
        "valuation_confidence": "HIGH",
        "model_status": "MODEL_VERIFIED",
        "quality_score": 90,
        "quality_tier": "HIGH_QUALITY",
        "cfo_to_net_income": 1.1,
        "dilution_status": "STABLE",
        "accounting_reliability": "PASS",
        "financial_strength": "PASS",
        "hard_rejects": [],
        "understandability": "PASS",
        "earnings_durability": "PASS",
        "moat_strength": "WIDE",
        "management_capital_allocation": "PASS",
    }

    b_rev = evaluate_business_review("FPT", valuation_report=valuation).to_dict()
    v_trap = evaluate_value_trap("FPT", valuation_report=valuation).to_dict()

    pb_input = PersonalBalanceSheetInput(
        monthly_net_income=50_000_000,
        monthly_essential_spending=20_000_000,
        safe_liquid_assets=240_000_000,
    )
    durability = calculate_capital_durability(pb_input, portfolio_equity_value=100_000_000, deployable_portfolio_cash=50_000_000).to_dict()

    ctx = build_decision_context(
        symbol="FPT",
        holding={"weight": 0.0, "market_value": 0, "quantity": 0},
        valuation=valuation,
        personal_finance=durability,
        business_review=b_rev,
        value_trap=v_trap,
    )

    evidence = evaluate_decision(ctx)

    assert b_rev["overall_status"] == "BUSINESS_PASS"
    assert b_rev["moat"] == "PASS"
    assert b_rev["management_capital_allocation"] == "PASS"
    assert v_trap["status"] == "CLEAR"
    assert ctx.business_review_status == "BUSINESS_PASS"
    assert ctx.moat_assessment == "PASS"
    assert ctx.capital_allocation_quality == "PASS"
    assert ctx.survival_reserve_status == "SAFE"
    assert evidence.decision == "BUY"


def test_full_pipeline_acb_solvency_risk_fails():
    """ACB: Solvency risk failure yields HIGH_RISK and AVOID / SELL_REVIEW."""
    valuation = {
        "symbol": "ACB",
        "current_price": 25000,
        "base_iv": 35000,
        "model_status": "MODEL_VERIFIED",
        "financial_strength_score": 20,
        "hard_rejects": ["SOLVENCY_RISK"],
        "accounting_reliability": "PASS",
    }

    b_rev = evaluate_business_review("ACB", valuation_report=valuation).to_dict()
    v_trap = evaluate_value_trap("ACB", valuation_report=valuation).to_dict()
    pf = {"survival_reserve_status": "SAFE", "available_long_term_capital": 100_000_000}

    ctx = build_decision_context(
        symbol="ACB",
        holding=None,
        valuation=valuation,
        personal_finance=pf,
        business_review=b_rev,
        value_trap=v_trap,
    )

    evidence = evaluate_decision(ctx)
    assert b_rev["overall_status"] == "BUSINESS_FAIL"
    assert evidence.decision == "AVOID"


def test_full_pipeline_dgc_cyclical_watch():
    """DGC: Cyclical earnings / ValueTrap WATCH prohibits unrestricted BUY."""
    valuation = {
        "symbol": "DGC",
        "current_price": 90000,
        "base_iv": 100000,
        "bear_iv": 70000,
        "model_status": "MODEL_VERIFIED",
        "dilution_status": "STABLE",
        "accounting_reliability": "PASS",
        "financial_strength": "PASS",
        "return_on_capital_trend": "DECLINING",
        "normalized_earnings_trend": "DECLINING",
        "hard_rejects": [],
    }

    b_rev = evaluate_business_review("DGC", valuation_report=valuation).to_dict()
    v_trap = evaluate_value_trap("DGC", valuation_report=valuation).to_dict()
    pf = {"survival_reserve_status": "SAFE", "available_long_term_capital": 100_000_000}

    ctx = build_decision_context(
        symbol="DGC",
        holding=None,
        valuation=valuation,
        personal_finance=pf,
        business_review=b_rev,
        value_trap=v_trap,
    )

    evidence = evaluate_decision(ctx)
    assert v_trap["status"] == "WATCH"
    assert evidence.decision not in ("BUY", "BUY_MORE")
    assert evidence.decision in ("REVIEW_BUSINESS", "WAIT_FOR_MOS")
