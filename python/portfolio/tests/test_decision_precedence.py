"""Mandatory Scenario Tests & Precedence Invariants for Buffett-Munger Policy Engine (Task 134)."""

import pytest
from portfolio.policy.models import InvestmentDecisionContext
from portfolio.policy.engine import evaluate_decision


def test_scenario_a_business_unknown_attractive_mos_safe_pbs():
    """Scenario A: Qualitative UNKNOWN + ValueTrap CLEAR + MOS 50% + PBS SAFE -> BUY under Task 136 BCTC-only pipeline."""
    ctx = InvestmentDecisionContext(
        symbol="SYM_A",
        current_weight=0.0,
        current_price=50000,
        base_iv=100000,
        required_mos=15.0,
        actual_mos=50.0,
        model_status="VALID",
        business_review_status="UNKNOWN",
        value_trap_status="CLEAR",
        survival_reserve_status="SAFE",
        available_long_term_capital=100_000_000,
    )
    ev = evaluate_decision(ctx)
    assert ev.decision == "BUY"
    assert "BUSINESS_REVIEW_INCOMPLETE" not in ev.blocking_reasons


def test_scenario_b_business_pass_mos_insufficient_candidate():
    """Scenario B: Business PASS + ValueTrap CLEAR + MOS insufficient + PBS SAFE + candidate -> WAIT_FOR_MOS."""
    ctx = InvestmentDecisionContext(
        symbol="SYM_B",
        current_weight=0.0,
        current_price=95000,
        base_iv=100000,
        required_mos=15.0,
        actual_mos=5.0,
        model_status="VALID",
        business_review_status="BUSINESS_PASS",
        value_trap_status="CLEAR",
        survival_reserve_status="SAFE",
        available_long_term_capital=100_000_000,
    )
    ev = evaluate_decision(ctx)
    assert ev.decision == "WAIT_FOR_MOS"
    assert ev.primary_reason == "MOS_INSUFFICIENT"
    assert "MOS_INSUFFICIENT" in ev.blocking_reasons


def test_scenario_c_business_pass_mos_sufficient_pbs_unknown():
    """Scenario C: Business PASS + ValueTrap CLEAR + MOS sufficient + PBS UNKNOWN -> BUILD_RESERVE_FIRST."""
    ctx = InvestmentDecisionContext(
        symbol="SYM_C",
        current_weight=0.0,
        current_price=50000,
        base_iv=100000,
        required_mos=15.0,
        actual_mos=50.0,
        model_status="VALID",
        business_review_status="BUSINESS_PASS",
        value_trap_status="CLEAR",
        survival_reserve_status="UNKNOWN",
        available_long_term_capital=0.0,
    )
    ev = evaluate_decision(ctx)
    assert ev.decision == "BUILD_RESERVE_FIRST"
    assert ev.primary_reason == "PERSONAL_BALANCE_SHEET_UNKNOWN"
    assert "PERSONAL_BALANCE_SHEET_UNKNOWN" in ev.blocking_reasons


def test_scenario_d_business_unknown_pbs_unknown_multiple_blockers():
    """Scenario D: Qualitative UNKNOWN + ValueTrap CLEAR + MOS sufficient + PBS UNKNOWN -> BUILD_RESERVE_FIRST."""
    ctx = InvestmentDecisionContext(
        symbol="SYM_D",
        current_weight=0.0,
        current_price=50000,
        base_iv=100000,
        required_mos=15.0,
        actual_mos=50.0,
        model_status="VALID",
        business_review_status="UNKNOWN",
        value_trap_status="CLEAR",
        survival_reserve_status="UNKNOWN",
        available_long_term_capital=0.0,
    )
    ev = evaluate_decision(ctx)
    assert ev.decision == "BUILD_RESERVE_FIRST"
    assert ev.primary_reason == "PERSONAL_BALANCE_SHEET_UNKNOWN"
    assert "PERSONAL_BALANCE_SHEET_UNKNOWN" in ev.blocking_reasons


def test_scenario_e_business_fail_cheap_price_candidate():
    """Scenario E: Business FAIL + MOS 70% + PBS SAFE + candidate -> AVOID."""
    ctx = InvestmentDecisionContext(
        symbol="SYM_E",
        current_weight=0.0,
        current_price=30000,
        base_iv=100000,
        required_mos=15.0,
        actual_mos=70.0,
        model_status="VALID",
        business_review_status="BUSINESS_FAIL",
        value_trap_status="CLEAR",
        survival_reserve_status="SAFE",
        available_long_term_capital=100_000_000,
    )
    ev = evaluate_decision(ctx)
    assert ev.decision == "AVOID"
    assert ev.primary_reason == "STRUCTURAL_DETERIORATION"
    assert "STRUCTURAL_DETERIORATION" in ev.blocking_reasons


def test_scenario_f_business_fail_existing_holding():
    """Scenario F: Business FAIL + existing holding -> SELL_REVIEW."""
    ctx = InvestmentDecisionContext(
        symbol="SYM_F",
        current_weight=0.10,
        shares_held=1000,
        current_price=30000,
        base_iv=100000,
        required_mos=15.0,
        model_status="VALID",
        business_review_status="BUSINESS_FAIL",
        value_trap_status="CLEAR",
        survival_reserve_status="SAFE",
        available_long_term_capital=100_000_000,
    )
    ev = evaluate_decision(ctx)
    assert ev.decision == "SELL_REVIEW"
    assert ev.primary_reason == "STRUCTURAL_DETERIORATION"


def test_scenario_g_business_pass_overweight_holding():
    """Scenario G: Business PASS + MOS sufficient + PBS SAFE + weight >= 0.35 -> HOLD_NO_NEW_CAPITAL."""
    ctx = InvestmentDecisionContext(
        symbol="SYM_G",
        current_weight=0.38,
        shares_held=10000,
        current_price=50000,
        base_iv=100000,
        required_mos=15.0,
        actual_mos=50.0,
        model_status="VALID",
        business_review_status="BUSINESS_PASS",
        value_trap_status="CLEAR",
        survival_reserve_status="SAFE",
        available_long_term_capital=100_000_000,
    )
    ev = evaluate_decision(ctx)
    assert ev.decision == "HOLD_NO_NEW_CAPITAL"
    assert ev.primary_reason == "POSITION_CAP_REACHED"


def test_scenario_h_business_pass_mos_insufficient_holding():
    """Scenario H: Business PASS + MOS insufficient + existing holding -> HOLD."""
    ctx = InvestmentDecisionContext(
        symbol="SYM_H",
        current_weight=0.10,
        shares_held=1000,
        current_price=90000,
        base_iv=100000,
        required_mos=15.0,
        actual_mos=10.0,
        model_status="VALID",
        business_review_status="BUSINESS_PASS",
        value_trap_status="CLEAR",
        survival_reserve_status="SAFE",
        available_long_term_capital=100_000_000,
    )
    ev = evaluate_decision(ctx)
    assert ev.decision == "HOLD"
    assert ev.primary_reason == "MOS_INSUFFICIENT"


def test_scenario_i_price_decline_no_sell_trigger():
    """Scenario I: Stock price drops 50%, fundamentals unchanged -> NO SELL TRIGGER."""
    ctx = InvestmentDecisionContext(
        symbol="SYM_I",
        current_weight=0.15,
        shares_held=2000,
        current_price=50000,  # Dropped from 100k
        base_iv=120000,
        required_mos=15.0,
        actual_mos=58.3,
        model_status="VALID",
        business_review_status="BUSINESS_PASS",
        value_trap_status="CLEAR",
        survival_reserve_status="SAFE",
        available_long_term_capital=100_000_000,
    )
    ev = evaluate_decision(ctx)
    assert ev.decision in ("BUY_MORE", "HOLD", "HOLD_NO_NEW_CAPITAL")
    assert ev.decision not in ("SELL", "SELL_REVIEW", "AVOID")


def test_scenario_j_accounting_fail_existing_holding():
    """Scenario J: Accounting reliability FAIL + existing holding -> SELL_REVIEW."""
    ctx = InvestmentDecisionContext(
        symbol="SYM_J",
        current_weight=0.10,
        shares_held=1000,
        current_price=50000,
        base_iv=100000,
        accounting_reliability="FAIL",
        business_review_status="BUSINESS_PASS",
        value_trap_status="CLEAR",
        survival_reserve_status="SAFE",
    )
    ev = evaluate_decision(ctx)
    assert ev.decision == "SELL_REVIEW"
    assert ev.primary_reason == "ACCOUNTING_FAILURE"


def test_invariant_unknown_not_equal_to_pass():
    """Invariant: UNKNOWN business evidence cannot pass BUY gate."""
    ctx = InvestmentDecisionContext(
        symbol="INV_1",
        current_weight=0.0,
        current_price=30000,
        base_iv=100000,
        business_review_status="UNKNOWN",
        survival_reserve_status="SAFE",
        available_long_term_capital=100_000_000,
        data_readiness={"financial_core": "INSUFFICIENT", "valuation": "READY", "value_trap": "READY"},
    )
    ev = evaluate_decision(ctx)
    assert ev.decision != "BUY"
    assert ev.decision == "REVIEW_BUSINESS"


def test_invariant_valuetrap_clear_not_equal_to_buy():
    """Invariant: ValueTrap CLEAR alone does NOT produce BUY if MOS or business incomplete."""
    ctx = InvestmentDecisionContext(
        symbol="INV_2",
        current_weight=0.0,
        current_price=90000,
        base_iv=100000,
        required_mos=15.0,
        business_review_status="BUSINESS_PASS",
        value_trap_status="CLEAR",
        survival_reserve_status="SAFE",
    )
    ev = evaluate_decision(ctx)
    assert ev.decision == "WAIT_FOR_MOS"
    assert ev.decision != "BUY"


def test_invariant_bad_business_cannot_be_rescued_by_cheap_price():
    """Invariant: Bad business (FAIL) cannot be bought no matter how cheap the price."""
    ctx = InvestmentDecisionContext(
        symbol="INV_3",
        current_weight=0.0,
        current_price=1000,  # Extremely cheap!
        base_iv=100000,
        required_mos=15.0,
        business_review_status="BUSINESS_FAIL",
        value_trap_status="CLEAR",
        survival_reserve_status="SAFE",
        available_long_term_capital=500_000_000,
    )
    ev = evaluate_decision(ctx)
    assert ev.decision == "AVOID"
    assert ev.decision != "BUY"
