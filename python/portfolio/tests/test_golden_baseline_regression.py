"""Golden Baseline Regression & System Invariants Test Suite (T17, T20)."""

import pytest
from portfolio.policy.models import InvestmentDecisionContext
from portfolio.policy.engine import evaluate_decision
from portfolio.policy.context_builder import build_decision_context
from portfolio.personal_finance.models import PersonalBalanceSheetInput
from portfolio.personal_finance.service import calculate_capital_durability
from portfolio.value_engine.business_review import evaluate_business_review
from portfolio.value_engine.value_trap import evaluate_value_trap


def test_baseline_symbols_acb_dgc_fpt_ledger_invariants():
    """Verify ACB, DGC, FPT symbols preserve ledger quantity invariants."""
    for symbol in ("ACB", "DGC", "FPT"):
        holding = {"symbol": symbol, "quantity": 1000, "cost_basis": 50000, "weight": 0.10, "market_value": 50_000_000}
        val = {"price": 50000, "base_iv": 70000, "required_mos": 15.0, "actual_mos": 28.5, "model_status": "VALID"}
        b_rev = evaluate_business_review(symbol, valuation_report=val).to_dict()
        v_trap = evaluate_value_trap(symbol, valuation_report=val).to_dict()

        ctx = build_decision_context(
            symbol=symbol,
            holding=holding,
            valuation=val,
            business_review=b_rev,
            value_trap=v_trap,
        )

        assert ctx.symbol == symbol
        assert ctx.shares_held == 1000
        assert ctx.current_market_value == 50_000_000


def test_golden_scenario_1_buy():
    """Good business + sufficient MOS + fortress healthy => BUY."""
    ctx = InvestmentDecisionContext(
        symbol="FPT",
        current_weight=0.0,
        current_price=100000,
        base_iv=150000,
        required_mos=15.0,
        actual_mos=33.3,
        model_status="VALID",
        business_review_status="BUSINESS_PASS",
        value_trap_status="CLEAR",
        survival_reserve_status="SAFE",
        available_long_term_capital=100_000_000,
    )
    ev = evaluate_decision(ctx)
    assert ev.decision == "BUY"


def test_golden_scenario_2_buy_more():
    """Existing holding + sufficient MOS + fortress healthy => BUY_MORE."""
    ctx = InvestmentDecisionContext(
        symbol="FPT",
        current_weight=0.10,
        shares_held=500,
        current_price=100000,
        base_iv=150000,
        required_mos=15.0,
        actual_mos=33.3,
        model_status="VALID",
        business_review_status="BUSINESS_PASS",
        value_trap_status="CLEAR",
        survival_reserve_status="SAFE",
        available_long_term_capital=100_000_000,
    )
    ev = evaluate_decision(ctx)
    assert ev.decision == "BUY_MORE"


def test_golden_scenario_3_build_reserve_first():
    """Good business + attractive valuation + reserve unsafe => BUILD_RESERVE_FIRST."""
    ctx = InvestmentDecisionContext(
        symbol="FPT",
        current_weight=0.0,
        current_price=100000,
        base_iv=150000,
        required_mos=15.0,
        model_status="VALID",
        business_review_status="BUSINESS_PASS",
        value_trap_status="CLEAR",
        survival_reserve_status="UNSAFE",
        available_long_term_capital=0.0,
    )
    ev = evaluate_decision(ctx)
    assert ev.decision == "BUILD_RESERVE_FIRST"


def test_golden_scenario_4_high_volatility_not_sell():
    """High volatility => NOT SELL."""
    ctx = InvestmentDecisionContext(
        symbol="DGC",
        current_weight=0.15,
        shares_held=1000,
        current_price=90000,
        base_iv=120000,
        model_status="VALID",
        business_review_status="BUSINESS_PASS",
        value_trap_status="CLEAR",
        survival_reserve_status="SAFE",
    )
    ev = evaluate_decision(ctx)
    assert ev.decision not in ("SELL", "SELL_REVIEW")


def test_golden_scenario_5_value_trap_high_risk_not_buy():
    """Price < Base IV + ValueTrap HIGH_RISK => NOT BUY (returns AVOID/REVIEW_BUSINESS)."""
    ctx = InvestmentDecisionContext(
        symbol="TRAP",
        current_weight=0.0,
        current_price=5000,
        base_iv=25000,
        model_status="VALID",
        value_trap_status="HIGH_RISK",
        survival_reserve_status="SAFE",
    )
    ev = evaluate_decision(ctx)
    assert ev.decision in ("AVOID", "REVIEW_BUSINESS")
    assert ev.decision != "BUY"


def test_golden_scenario_6_accounting_unreliable_sell_review():
    """Accounting unreliable => AVOID (new) or SELL_REVIEW (existing)."""
    ctx_holding = InvestmentDecisionContext(symbol="BAD", current_weight=0.05, shares_held=200, accounting_reliability="FAIL")
    ev = evaluate_decision(ctx_holding)
    assert ev.decision == "SELL_REVIEW"


def test_golden_scenario_7_solvency_failure_avoid():
    """Solvency failure => AVOID (new candidate)."""
    ctx_cand = InvestmentDecisionContext(symbol="FAIL_DEBT", current_weight=0.0, financial_strength="FAIL")
    ev = evaluate_decision(ctx_cand)
    assert ev.decision == "AVOID"


def test_golden_scenario_8_position_capacity_exceeded():
    """Business PASS + position capacity exceeded (weight >= 0.35) => HOLD_NO_NEW_CAPITAL."""
    ctx = InvestmentDecisionContext(
        symbol="FPT",
        current_weight=0.36,
        shares_held=10000,
        current_price=100000,
        base_iv=160000,
        model_status="VALID",
        business_review_status="BUSINESS_PASS",
        value_trap_status="CLEAR",
        survival_reserve_status="SAFE",
        available_long_term_capital=100_000_000,
    )
    ev = evaluate_decision(ctx)
    assert ev.decision == "HOLD_NO_NEW_CAPITAL"


def test_golden_scenario_9_no_material_issue_hold():
    """No material issue => HOLD."""
    ctx = InvestmentDecisionContext(
        symbol="ACB",
        current_weight=0.10,
        shares_held=4000,
        current_price=25000,
        base_iv=25000,
        required_mos=0.0,
        model_status="VALID",
        business_review_status="BUSINESS_PASS",
        value_trap_status="CLEAR",
        survival_reserve_status="SAFE",
    )
    ev = evaluate_decision(ctx)
    assert ev.decision == "HOLD"


