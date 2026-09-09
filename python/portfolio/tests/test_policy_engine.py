"""Golden Decision Tests for Buffett/Munger Policy Engine (T08, T09)."""

import pytest
from portfolio.policy.models import InvestmentDecisionContext
from portfolio.policy.engine import evaluate_decision


def test_golden_1_buy_candidate_qualified():
    ctx = InvestmentDecisionContext(
        symbol="FPT",
        current_weight=0.0,
        current_price=100000,
        base_iv=150000,
        bear_iv=120000,
        required_mos=15.0,
        actual_mos=33.3,
        model_status="VALID",
        valuation_confidence="HIGH",
        business_review_status="BUSINESS_PASS",
        value_trap_status="CLEAR",
        survival_reserve_status="SAFE",
        available_long_term_capital=200_000_000,
    )

    ev = evaluate_decision(ctx)
    assert ev.decision == "BUY"
    assert ev.confidence == "HIGH"
    assert len(ev.reasons) > 0


def test_golden_2_buy_more_existing_holding():
    ctx = InvestmentDecisionContext(
        symbol="FPT",
        current_weight=0.15,
        shares_held=1000,
        current_price=100000,
        base_iv=150000,
        required_mos=15.0,
        model_status="VALID",
        business_review_status="BUSINESS_PASS",
        value_trap_status="CLEAR",
        survival_reserve_status="SAFE",
        available_long_term_capital=200_000_000,
    )

    ev = evaluate_decision(ctx)
    assert ev.decision == "BUY_MORE"


def test_golden_3_unsafe_reserve_forces_build_reserve_first():
    """Invariant: Unsafe personal survival reserve forces BUILD_RESERVE_FIRST despite cheap valuation."""
    ctx = InvestmentDecisionContext(
        symbol="FPT",
        current_weight=0.0,
        current_price=100000,
        base_iv=180000,
        required_mos=15.0,
        model_status="VALID",
        business_review_status="BUSINESS_PASS",
        value_trap_status="CLEAR",
        survival_reserve_status="UNSAFE",  # Personal reserve is below target!
        available_long_term_capital=0.0,
    )

    ev = evaluate_decision(ctx)
    assert ev.decision == "BUILD_RESERVE_FIRST"
    assert "R-01-SURVIVAL-RESERVE" in [r.rule_id for r in ev.rules_triggered]


def test_golden_4_value_trap_high_risk_blocks_buy():
    """Invariant: Value trap HIGH_RISK prohibits BUY even if price < Base IV."""
    ctx = InvestmentDecisionContext(
        symbol="TRAP",
        current_weight=0.0,
        current_price=10000,
        base_iv=30000,
        model_status="VALID",
        business_review_status="BUSINESS_PASS",
        value_trap_status="HIGH_RISK",  # Cash flow divergence / severe deterioration!
        survival_reserve_status="SAFE",
        available_long_term_capital=100_000_000,
    )

    ev = evaluate_decision(ctx)
    assert ev.decision == "AVOID"
    assert ev.decision != "BUY"


def test_golden_5_accounting_unreliable_triggers_avoid_or_sell_review():
    ctx_new = InvestmentDecisionContext(symbol="BAD1", current_weight=0.0, accounting_reliability="FAIL")
    ev_new = evaluate_decision(ctx_new)
    assert ev_new.decision == "AVOID"

    ctx_old = InvestmentDecisionContext(symbol="BAD2", current_weight=0.10, shares_held=500, accounting_reliability="FAIL")
    ev_old = evaluate_decision(ctx_old)
    assert ev_old.decision == "SELL_REVIEW"


def test_golden_6_solvency_failure_triggers_avoid_or_sell_review():
    ctx_new = InvestmentDecisionContext(symbol="DEBT1", current_weight=0.0, financial_strength="FAIL")
    ev_new = evaluate_decision(ctx_new)
    assert ev_new.decision == "AVOID"

    ctx_old = InvestmentDecisionContext(symbol="DEBT2", current_weight=0.12, shares_held=1000, financial_strength="FAIL")
    ev_old = evaluate_decision(ctx_old)
    assert ev_old.decision == "SELL_REVIEW"


def test_golden_7_position_capacity_exceeded_limits_to_hold_no_new_capital():
    ctx = InvestmentDecisionContext(
        symbol="FPT",
        current_weight=0.38,  # Exceeds 35% max capacity
        shares_held=10000,
        current_price=100000,
        base_iv=160000,
        model_status="VALID",
        business_review_status="BUSINESS_PASS",
        value_trap_status="CLEAR",
        survival_reserve_status="SAFE",
        available_long_term_capital=200_000_000,
    )

    ev = evaluate_decision(ctx)
    assert ev.decision == "HOLD_NO_NEW_CAPITAL"


def test_golden_8_price_above_acceptable_mos_causes_wait_for_mos():
    ctx = InvestmentDecisionContext(
        symbol="FPT",
        current_weight=0.0,
        current_price=150000,  # Base IV is 150k, required MOS is 15% (entry max = 127.5k)
        base_iv=150000,
        required_mos=15.0,
        model_status="VALID",
        business_review_status="BUSINESS_PASS",
        value_trap_status="CLEAR",
        survival_reserve_status="SAFE",
        available_long_term_capital=100_000_000,
    )

    ev = evaluate_decision(ctx)
    assert ev.decision == "WAIT_FOR_MOS"


def test_golden_9_model_verified_allows_buy():
    """Invariant: MODEL_VERIFIED status is accepted as READY valuation status and allows BUY."""
    ctx = InvestmentDecisionContext(
        symbol="ACB",
        current_weight=0.0,
        current_price=20000,
        base_iv=35000,
        bear_iv=28000,
        required_mos=15.0,
        actual_mos=42.8,
        model_status="MODEL_VERIFIED",
        valuation_confidence="HIGH",
        business_review_status="BUSINESS_PASS",
        value_trap_status="CLEAR",
        survival_reserve_status="SAFE",
        available_long_term_capital=500_000_000,
    )

    ev = evaluate_decision(ctx)
    assert ev.decision == "BUY"


def test_golden_10_valuetrap_watch_prohibits_buy():
    """Invariant: ValueTrap WATCH status prohibits BUY and BUY_MORE even when MOS is satisfied."""
    ctx = InvestmentDecisionContext(
        symbol="WATCH_SYM",
        current_weight=0.0,
        current_price=10000,
        base_iv=30000,
        required_mos=15.0,
        model_status="MODEL_VERIFIED",
        business_review_status="BUSINESS_PASS",
        value_trap_status="WATCH",
        survival_reserve_status="SAFE",
        available_long_term_capital=500_000_000,
    )

    ev = evaluate_decision(ctx)
    assert ev.decision != "BUY"
    assert ev.decision != "BUY_MORE"
    assert ev.decision in ("WAIT_FOR_MOS", "REVIEW_BUSINESS", "HOLD")


def test_golden_11_valuetrap_insufficient_data_prohibits_buy():
    """Invariant: ValueTrap INSUFFICIENT_DATA status prohibits BUY and BUY_MORE."""
    ctx = InvestmentDecisionContext(
        symbol="NODATA_SYM",
        current_weight=0.0,
        current_price=10000,
        base_iv=30000,
        required_mos=15.0,
        model_status="MODEL_VERIFIED",
        business_review_status="BUSINESS_PASS",
        value_trap_status="INSUFFICIENT_DATA",
        survival_reserve_status="SAFE",
        available_long_term_capital=500_000_000,
    )

    ev = evaluate_decision(ctx)
    assert ev.decision != "BUY"
    assert ev.decision != "BUY_MORE"


def test_golden_12_personal_finance_unknown_prohibits_buy():
    """Invariant: Personal finance UNKNOWN status forces BUILD_RESERVE_FIRST and prohibits BUY."""
    ctx = InvestmentDecisionContext(
        symbol="FPT",
        current_weight=0.0,
        current_price=100000,
        base_iv=150000,
        required_mos=15.0,
        model_status="MODEL_VERIFIED",
        business_review_status="BUSINESS_PASS",
        value_trap_status="CLEAR",
        survival_reserve_status="UNKNOWN",
        available_long_term_capital=0.0,
    )

    ev = evaluate_decision(ctx)
    assert ev.decision == "BUILD_RESERVE_FIRST"
    assert ev.decision != "BUY"

