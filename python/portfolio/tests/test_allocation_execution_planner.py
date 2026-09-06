import pytest
from portfolio.allocation.models import (
    AllocationDecision,
    CandidateOpportunity,
    AllocationExecutionPlan,
    EligibilityResult,
)
from portfolio.allocation.execution_planner import compute_execution_plan
from portfolio.allocation.candidate_service import (
    is_valid_equity_symbol,
    build_selection_evidence,
    shortlist_candidates,
)
from portfolio.allocation.service import AllocationService

def make_decision(symbol: str, action: str, current_weight: float = 0.0, target_weight: float = 0.10, target_min: float = 0.08, target_max: float = 0.12) -> AllocationDecision:
    return AllocationDecision(
        symbol=symbol,
        action=action,
        current_weight=current_weight,
        target_mid=target_weight,
        target_min=target_min,
        target_max=target_max,
        reason_codes=("TEST_REASON",),
    )

def test_buy_raw_quantity_and_board_lot_rounding():
    # portfolio NAV = 1,000,000,000, target weight 0.10 => desired value = 100M
    # current value = 0, price = 50,000.
    # effective cost per share = 50,000 * (1 + 0.001 + 0.0005) = 50,075
    # raw buy = 100,000,000 / 50,075 = 1997.004 => rounded down to 1900
    decision = make_decision("VNM", "BUY_MORE", current_weight=0.0, target_weight=0.10, target_min=0.08, target_max=0.12)
    plan = compute_execution_plan(
        decision,
        current_quantity=0,
        reference_price=50000.0,
        price_date="2026-09-06",
        price_source="CANONICAL",
        available_cash=500000000.0,
        portfolio_nav=1000000000.0,
        lot_size=100,
    )
    assert plan.is_executable is True
    assert plan.raw_quantity_change == 1997
    assert plan.rounded_quantity_change == 1900
    assert plan.post_trade_quantity == 1900
    assert plan.gross_trade_value == 1900 * 50000.0
    assert plan.estimated_fee == 1900 * 50000.0 * 0.001
    assert plan.estimated_tax == 0.0  # Buy has no sell tax


def test_buy_never_exceeds_cash():
    # Only 4,000,000 cash available. 1 share cost ~50,075 VND => max 79 shares => 0 lots.
    decision = make_decision("VNM", "BUY_MORE", current_weight=0.0, target_weight=0.10, target_min=0.08, target_max=0.12)
    plan = compute_execution_plan(
        decision,
        current_quantity=0,
        reference_price=50000.0,
        available_cash=4000000.0,  # Insufficient cash for 1 lot (needs ~5,007,500)
        portfolio_nav=1000000000.0,
    )
    assert plan.is_executable is False
    assert "CASH_INSUFFICIENT_FOR_LOT" in plan.blocking_reasons
    assert plan.rounded_quantity_change == 0


def test_stale_or_missing_price_blocks_execution():
    decision = make_decision("VNM", "BUY_MORE", current_weight=0.0, target_weight=0.10, target_min=0.08, target_max=0.12)
    plan_missing = compute_execution_plan(
        decision,
        current_quantity=0,
        reference_price=0.0,
        available_cash=500000000.0,
        portfolio_nav=1000000000.0,
    )
    assert plan_missing.is_executable is False
    assert "PRICE_UNAVAILABLE" in plan_missing.blocking_reasons


def test_reduce_never_accidental_full_exit_and_includes_tax():
    # current 10,000 shares, current weight 0.20, target 0.10 (band 0.09-0.11)
    decision = make_decision("REE", "REDUCE", current_weight=0.20, target_weight=0.10, target_min=0.09, target_max=0.11)
    plan = compute_execution_plan(
        decision,
        current_quantity=10000,
        reference_price=50000.0,
        available_cash=100000000.0,
        portfolio_nav=2500000000.0,  # 10,000 shares * 50k = 500M (20%)
        lot_size=100,
    )
    assert plan.is_executable is True
    # Theoretical sell value = 250M => 5,000 shares
    assert plan.rounded_quantity_change == -5000
    assert plan.post_trade_quantity == 5000
    assert plan.post_trade_quantity > 0  # Not a full exit!
    assert plan.estimated_tax == 5000 * 50000.0 * 0.001  # Sell tax 0.1%


def test_sell_equals_holding_quantity():
    decision = make_decision("FRT", "SELL", current_weight=0.05, target_weight=0.0, target_min=0.0, target_max=0.0)
    plan = compute_execution_plan(
        decision,
        current_quantity=1250,
        reference_price=80000.0,
        available_cash=50000000.0,
        portfolio_nav=2000000000.0,
    )
    assert plan.is_executable is True
    assert plan.rounded_quantity_change == -1250
    assert plan.post_trade_quantity == 0


def test_security_universe_gate():
    assert is_valid_equity_symbol("FPT") is True
    assert is_valid_equity_symbol("CFPT2301") is False  # Warrant
    assert is_valid_equity_symbol("FUESSVFL") is False  # ETF
    assert is_valid_equity_symbol("CBB2001") is False  # Derivative/Warrant


def test_selection_evidence_formatting():
    item = {"symbol": "CTR", "avg_turnover_20d_billion": 18.5}
    signal = {"quality_score": 85.0, "actual_mos_pct": 38.0, "required_mos_pct": 28.0}
    elig = EligibilityResult(
        symbol="CTR",
        status="INVESTABLE",
        quality_tier="HIGH_QUALITY",
        quality_score=85.0,
        actual_mos_pct=38.0,
        required_mos_pct=28.0,
        valuation_safety=10.0,
        hard_rejects=(),
    )
    ev = build_selection_evidence(
        item=item,
        signal=signal,
        eligibility=elig,
        candidate_rank=1,
    )
    assert ev["security_type_pass"] is True
    assert ev["liquidity_pass"] is True
    assert ev["valuation_safety_pp"] == 10.0
    assert len(ev["why_selected"]) == 4
    assert "Cổ phiếu phổ thông" in ev["why_selected"][0]
    assert "Thanh khoản" in ev["why_selected"][1]
    assert "Chất lượng" in ev["why_selected"][2]
    assert "Biên an toàn" in ev["why_selected"][3]
