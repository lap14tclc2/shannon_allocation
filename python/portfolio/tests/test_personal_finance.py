"""Unit tests for Personal Balance Sheet & Stress Engine (T04, T05, T06)."""

import pytest
from portfolio.personal_finance.models import PersonalBalanceSheetInput
from portfolio.personal_finance.service import calculate_capital_durability
from portfolio.personal_finance.stress import run_crash_job_loss_stress_engine


def test_capital_durability_healthy_fortress():
    pb = PersonalBalanceSheetInput(
        monthly_net_income=50_000_000,
        monthly_essential_spending=20_000_000,
        safe_liquid_assets=240_000_000,  # 12 months essential spending
        near_term_liabilities=40_000_000,
        target_survival_months=12.0,
    )

    # 100M portfolio cash, 500M portfolio equity
    res = calculate_capital_durability(pb, portfolio_equity_value=500_000_000, deployable_portfolio_cash=100_000_000)

    assert res.survival_months == 12.0
    assert res.survival_reserve_status == "SAFE"
    assert res.near_term_liability_status == "COVERED"
    assert res.status == "SAFE"

    # Total liquid = 240M safe + 100M portfolio cash = 340M
    # Required reservations = 240M reserve target + 40M near-term = 280M
    # Available long-term capital = 340M - 280M = 60M
    assert res.available_long_term_capital == 60_000_000


def test_capital_durability_unsafe_reserve_blocks_buy_capital():
    """Invariant: When safe_liquid_assets is below reserve target, Available Long-Term Capital must not allow auto-buy."""
    pb = PersonalBalanceSheetInput(
        monthly_net_income=30_000_000,
        monthly_essential_spending=20_000_000,
        safe_liquid_assets=60_000_000,  # Only 3 months (target: 12 months = 240M)
        near_term_liabilities=50_000_000,
        target_survival_months=12.0,
    )

    # Portfolio cash = 50M
    res = calculate_capital_durability(pb, portfolio_equity_value=200_000_000, deployable_portfolio_cash=50_000_000)

    assert res.survival_months == 3.0
    assert res.survival_reserve_status == "UNSAFE"
    # Total liquid = 60M safe + 50M cash = 110M.
    # Required reservations = 240M reserve target + 50M = 290M.
    # Raw = -180M -> Clamped to 0.0 (Never negative)
    assert res.available_long_term_capital == 0.0
    assert res.status == "UNSAFE"


def test_crash_job_loss_stress_engine_scenarios():
    pb = PersonalBalanceSheetInput(
        monthly_net_income=40_000_000,
        monthly_essential_spending=15_000_000,
        safe_liquid_assets=180_000_000,  # 12 months
        near_term_liabilities=20_000_000,
    )

    st = run_crash_job_loss_stress_engine(
        input_data=pb,
        portfolio_equity_value=400_000_000,
        portfolio_cash=50_000_000,
        largest_position_value=200_000_000,
    )

    assert len(st) == 4
    names = [s.scenario_name for s in st]
    assert "MARKET_CRASH" in names
    assert "JOB_LOSS" in names
    assert "COMBINED" in names
    assert "FAMILY_SHOCK" in names

    # In JOB_LOSS, safe assets 180M covers 12 months annual burn (180M), so forced sale is False
    job_loss_res = next(s for s in st if s.scenario_name == "JOB_LOSS")
    assert job_loss_res.forced_equity_sale_required is False


def test_personal_finance_lifecycle_mapping_and_new_contributions():
    """Invariant: Legacy lifecycle stages map deterministically and new contributions add to available capital."""
    data = {
        "monthly_net_income": 50_000_000,
        "monthly_essential_spending": 20_000_000,
        "safe_liquid_assets": 240_000_000,
        "near_term_liabilities": 40_000_000,
        "expected_new_contributions": 50_000_000,
        "reinvestable_dividends": 10_000_000,
        "lifecycle_stage": "MID_CAREER",  # Legacy label
    }

    pb = PersonalBalanceSheetInput.from_dict(data)
    assert pb.lifecycle_stage == "FAMILY_WITH_CHILDREN"
    assert pb.near_term_horizon_months == 36

    res = calculate_capital_durability(pb, portfolio_equity_value=500_000_000, deployable_portfolio_cash=100_000_000)
    # Available long term capital = 60M base + 50M new contributions + 10M reinvestable dividends = 120M
    assert res.available_long_term_capital == 120_000_000


def test_multi_user_personal_finance_isolation(tmp_path):
    """BLOCKER 1: Two users with different Personal Balance Sheets receive different capital durability results."""
    from portfolio.service import PortfolioService
    from portfolio.storage import PortfolioStore

    db1 = tmp_path / "u1.sqlite3"
    db2 = tmp_path / "u2.sqlite3"

    svc1 = PortfolioService(store=PortfolioStore(db1))
    svc2 = PortfolioService(store=PortfolioStore(db2))

    # User 1 has strong fortress
    svc1.set_personal_balance_sheet({
        "monthly_net_income": 100_000_000,
        "monthly_essential_spending": 20_000_000,
        "safe_liquid_assets": 500_000_000,
        "near_term_liabilities": 0.0,
    })

    # User 2 has weak fortress
    svc2.set_personal_balance_sheet({
        "monthly_net_income": 20_000_000,
        "monthly_essential_spending": 20_000_000,
        "safe_liquid_assets": 10_000_000,
        "near_term_liabilities": 50_000_000,
    })

    pb1 = svc1.get_personal_balance_sheet()
    pb2 = svc2.get_personal_balance_sheet()

    assert pb1 != pb2
    assert pb1["safe_liquid_assets"] == 500_000_000
    assert pb2["safe_liquid_assets"] == 10_000_000

    from portfolio.personal_finance.models import PersonalBalanceSheetInput
    eq_val, cash_val = 100_000_000, 50_000_000
    dur1 = calculate_capital_durability(PersonalBalanceSheetInput.from_dict(pb1), eq_val, cash_val)
    dur2 = calculate_capital_durability(PersonalBalanceSheetInput.from_dict(pb2), eq_val, cash_val)

    assert dur1.survival_reserve_status == "SAFE"
    assert dur2.survival_reserve_status == "UNSAFE"
    assert dur1.available_long_term_capital > dur2.available_long_term_capital


def test_missing_personal_finance_blocks_buy_and_attention_policy_gate():
    """BLOCKER 1 & 8: Missing personal finance blocks BUY; ATTENTION prohibits BUY."""
    from portfolio.policy.context_builder import build_decision_context
    from portfolio.policy.engine import evaluate_decision

    # 1. Missing personal finance
    ctx_missing = build_decision_context("FPT", personal_finance=None)
    ev_missing = evaluate_decision(ctx_missing)
    assert ev_missing.decision == "BUILD_RESERVE_FIRST"
    assert ev_missing.decision not in ("BUY", "BUY_MORE")

    # 2. ATTENTION status
    pf_att = {"survival_reserve_status": "ATTENTION", "available_long_term_capital": 10_000_000}
    ctx_att = build_decision_context("FPT", personal_finance=pf_att)
    ev_att = evaluate_decision(ctx_att)
    assert ev_att.decision == "BUILD_RESERVE_FIRST"
    assert ev_att.decision not in ("BUY", "BUY_MORE")

