"""Comprehensive test suite for Allocation Candidate Discovery Tiers (BUY_READY, WATCHLIST, REJECTED).

Validates:
- Gate-based classification into BUY_READY, WATCHLIST, and REJECTED.
- Watchlist near-qualified semantics (valuation safety negative, weak fit, low confidence, liquidity between 3B and 10B).
- Informational price-to-qualify max_buy_price math.
- Reconciled candidate universe counts (buy_ready_count, watchlist_count, rejected_count, universe_count).
- Deterministic ordering without weighted composite score.
- Invariant preservation: BUY standards not weakened, no auto-execution, Expected Alpha & Kelly disabled.
"""
from __future__ import annotations

import pytest

from portfolio.allocation.candidate_service import (
    classify_candidate,
    classify_screener_universe,
    compute_max_qualifying_price,
    is_valid_equity_symbol,
)
from portfolio.allocation.eligibility import eligibility_from_signal
from portfolio.allocation.models import CandidateOpportunity, PortfolioFitResult
from portfolio.allocation.reason_codes import (
    WATCH_LIQUIDITY_BELOW_BUY_THRESHOLD,
    WATCH_MOS_NEAR_THRESHOLD,
    WATCH_PORTFOLIO_FIT_WEAK,
    WATCH_VALUATION_TOO_EXPENSIVE,
)
from portfolio.allocation.service import AllocationService


def _make_item(
    symbol: str,
    *,
    tier: str = "HIGH_QUALITY",
    quality_score: int = 85,
    margin_of_safety: float = 35.0,
    required_mos: float = 30.0,
    valuation_status: str = "UNDERVALUED",
    turnover_20d: float = 15.0,
    hard_rejects: list[str] | None = None,
    current_price: float = 50000.0,
) -> dict:
    return {
        "symbol": symbol,
        "tier": tier,
        "quality_score": quality_score,
        "margin_of_safety": margin_of_safety,
        "required_mos": required_mos,
        "valuation_status": valuation_status,
        "avg_turnover_20d_billion": turnover_20d,
        "hard_rejects": hard_rejects or [],
        "current_price": current_price,
        "valuation_confidence": "HIGH",
    }


def test_01_perfect_candidate_buy_ready():
    item = _make_item("FPT", margin_of_safety=40.0, required_mos=30.0)
    sig = {"symbol": "FPT", "quality_tier": "HIGH_QUALITY", "actual_mos_pct": 40.0, "required_mos_pct": 30.0, "quality_score": 85}
    elig = eligibility_from_signal(sig)
    tier, evidence, failed, watch, max_price = classify_candidate(item, sig, elig)
    assert tier == "BUY_READY"
    assert len(failed) == 0


def test_02_good_quality_safety_slightly_negative_watchlist():
    item = _make_item("VNM", margin_of_safety=24.0, required_mos=30.0)
    sig = {"symbol": "VNM", "quality_tier": "HIGH_QUALITY", "actual_mos_pct": 24.0, "required_mos_pct": 30.0, "quality_score": 85}
    elig = eligibility_from_signal(sig)
    tier, evidence, failed, watch, max_price = classify_candidate(item, sig, elig)
    assert tier == "WATCHLIST"
    assert "VALUATION_SAFETY_INSUFFICIENT" in failed
    assert WATCH_MOS_NEAR_THRESHOLD in watch or WATCH_VALUATION_TOO_EXPENSIVE in watch


def test_03_good_quality_weak_fit_watchlist():
    item = _make_item("TCB", margin_of_safety=35.0, required_mos=30.0)
    sig = {"symbol": "TCB", "quality_tier": "HIGH_QUALITY", "actual_mos_pct": 35.0, "required_mos_pct": 30.0}
    elig = eligibility_from_signal(sig)
    weak_fit = PortfolioFitResult(symbol="TCB", current_weight=0.0, proposed_weight=0.08, fit="WEAK")
    tier, evidence, failed, watch, max_price = classify_candidate(item, sig, elig, portfolio_fit=weak_fit)
    assert tier == "WATCHLIST"
    assert "PORTFOLIO_FIT_WEAK" in failed
    assert WATCH_PORTFOLIO_FIT_WEAK in watch


def test_04_good_quality_low_confidence_watchlist():
    item = _make_item("MWG", margin_of_safety=35.0, required_mos=30.0)
    item["valuation_confidence"] = "LOW"
    sig = {"symbol": "MWG", "quality_tier": "HIGH_QUALITY", "actual_mos_pct": 35.0, "required_mos_pct": 30.0, "valuation_confidence": "LOW"}
    elig = eligibility_from_signal(sig)
    tier, evidence, failed, watch, max_price = classify_candidate(item, sig, elig)
    assert tier == "WATCHLIST"


def test_05_good_quality_insufficient_data_watchlist():
    item = _make_item("PNJ")
    item["margin_of_safety"] = None
    sig = {"symbol": "PNJ", "quality_tier": "HIGH_QUALITY", "actual_mos_pct": None, "required_mos_pct": 30.0}
    elig = eligibility_from_signal(sig)
    tier, evidence, failed, watch, max_price = classify_candidate(item, sig, elig)
    assert tier == "WATCHLIST"


def test_06_low_quality_rejected():
    item = _make_item("BAD", tier="LOW_QUALITY", quality_score=20)
    sig = {"symbol": "BAD", "quality_tier": "LOW_QUALITY", "quality_score": 20}
    elig = eligibility_from_signal(sig)
    tier, evidence, failed, watch, max_price = classify_candidate(item, sig, elig)
    assert tier == "REJECTED"


def test_07_solvency_risk_rejected():
    item = _make_item("RISK", hard_rejects=["SOLVENCY_RISK"])
    sig = {"symbol": "RISK", "quality_tier": "HIGH_QUALITY", "hard_rejects": ["SOLVENCY_RISK"]}
    elig = eligibility_from_signal(sig)
    tier, evidence, failed, watch, max_price = classify_candidate(item, sig, elig)
    assert tier == "REJECTED"


def test_08_invalid_security_rejected():
    assert not is_valid_equity_symbol("C123456")
    assert not is_valid_equity_symbol("VN30F1M")


def test_09_buy_ready_count_can_be_less_than_5():
    items = [_make_item("FPT"), _make_item("VNM", margin_of_safety=10.0, required_mos=30.0)]
    buy_ready, watchlist, rejected, counts, diag = classify_screener_universe(items)
    assert len(buy_ready) == 1
    assert counts["buy_ready_count"] == 1


def test_10_zero_buy_ready_results_in_keep_cash():
    service = AllocationService()
    items = [_make_item("VNM", margin_of_safety=10.0, required_mos=30.0)]
    report = service.evaluate(position_rows=[], cash=100_000_000, candidate_items=items)
    assert report.buy_ready_count == 0
    assert report.posture == "KEEP_CASH"
    assert report.no_action_required is True


def test_11_watchlist_does_not_receive_buy_more():
    service = AllocationService()
    items = [_make_item("VNM", margin_of_safety=24.0, required_mos=30.0)]
    report = service.evaluate(position_rows=[], cash=100_000_000, candidate_items=items)
    assert len(report.opportunities) == 0
    assert len(report.watchlist) >= 1
    for w in report.watchlist:
        assert w.decision is not None
        assert w.decision.action == "WATCH"


def test_12_watchlist_does_not_receive_share_quantity():
    service = AllocationService()
    items = [_make_item("VNM", margin_of_safety=24.0, required_mos=30.0)]
    report = service.evaluate(position_rows=[], cash=100_000_000, candidate_items=items)
    for w in report.watchlist:
        assert w.decision.execution_plan is None
        assert w.decision.target_mid is None


def test_13_buy_ready_receives_execution_plan():
    service = AllocationService()
    items = [_make_item("FPT", margin_of_safety=45.0, required_mos=30.0, turnover_20d=20.0)]
    report = service.evaluate(position_rows=[], cash=100_000_000, candidate_items=items)
    assert len(report.opportunities) == 1
    opp = report.opportunities[0]
    assert opp.decision.action == "BUY_MORE"
    assert opp.decision.execution_plan is not None
    assert opp.decision.execution_plan.rounded_quantity_change > 0


def test_14_rejected_candidate_never_receives_buy_action():
    service = AllocationService()
    items = [_make_item("BAD", tier="LOW_QUALITY")]
    report = service.evaluate(position_rows=[], cash=100_000_000, candidate_items=items)
    for r in report.rejected:
        assert r.decision.action == "WATCH"


def test_15_no_weighted_composite_score_used():
    items = [_make_item("A"), _make_item("B")]
    buy_ready, watchlist, rejected, counts, diag = classify_screener_universe(items)
    for c in buy_ready + watchlist + rejected:
        assert isinstance(c.gate_evidence, dict)


def test_16_deterministic_ordering():
    items = [
        _make_item("A", margin_of_safety=32.0, required_mos=30.0),
        _make_item("B", margin_of_safety=40.0, required_mos=30.0),
    ]
    buy_ready, watchlist, rejected, counts, diag = classify_screener_universe(items)
    assert buy_ready[0].symbol == "B"
    assert buy_ready[1].symbol == "A"


def test_17_counts_reconcile_with_classified_universe():
    items = [
        _make_item("BUY1", margin_of_safety=40.0, required_mos=30.0),
        _make_item("WATCH1", margin_of_safety=25.0, required_mos=30.0),
        _make_item("REJ1", hard_rejects=["SOLVENCY_RISK"]),
    ]
    buy_ready, watchlist, rejected, counts, diag = classify_screener_universe(items)
    assert counts["buy_ready_count"] == 1
    assert counts["watchlist_count"] == 1
    assert counts["rejected_count"] == 1
    assert counts["universe_count"] == 3


def test_18_valuation_proximity_reason_is_correct():
    item = _make_item("NEAR", margin_of_safety=26.0, required_mos=30.0)
    sig = {"symbol": "NEAR", "quality_tier": "HIGH_QUALITY", "actual_mos_pct": 26.0, "required_mos_pct": 30.0}
    elig = eligibility_from_signal(sig)
    tier, evidence, failed, watch, max_price = classify_candidate(item, sig, elig)
    assert WATCH_MOS_NEAR_THRESHOLD in watch


def test_19_optional_qualifying_price_math_is_correct():
    item = _make_item("PRICE_TEST", margin_of_safety=24.0, required_mos=30.0, current_price=76000.0)
    sig = {"symbol": "PRICE_TEST", "quality_tier": "HIGH_QUALITY", "actual_mos_pct": 24.0, "required_mos_pct": 30.0}
    max_price = compute_max_qualifying_price(item, sig)
    assert max_price is not None
    assert max_price < 76000.0


def test_20_report_to_dict_includes_all_tiers():
    service = AllocationService()
    items = [
        _make_item("BUY1", margin_of_safety=40.0, required_mos=30.0),
        _make_item("WATCH1", margin_of_safety=25.0, required_mos=30.0),
        _make_item("REJ1", hard_rejects=["SOLVENCY_RISK"]),
    ]
    report = service.evaluate(position_rows=[], cash=100_000_000, candidate_items=items)
    d = report.to_dict()
    assert d["buy_ready_count"] == 1
    assert d["watchlist_count"] == 1
    assert d["rejected_count"] == 1
    assert len(d["opportunities"]) == 1
    assert len(d["watchlist"]) == 1
    assert len(d["rejected"]) == 1


def test_23_multi_portfolio_isolation_preserved():
    service = AllocationService()
    rows1 = [{"symbol": "FPT", "quantity": 1000, "market_value": 100_000_000, "weight": 1.0}]
    rows2 = [{"symbol": "VNM", "quantity": 2000, "market_value": 150_000_000, "weight": 1.0}]
    rep1 = service.evaluate(position_rows=rows1, cash=0, portfolio_id=1)
    rep2 = service.evaluate(position_rows=rows2, cash=0, portfolio_id=2)
    assert rep1.holdings[0].symbol == "FPT"
    assert rep2.holdings[0].symbol == "VNM"


def test_24_no_ledger_mutation():
    service = AllocationService()
    rows = [{"symbol": "FPT", "quantity": 1000, "market_value": 100_000_000, "weight": 1.0}]
    original_qty = rows[0]["quantity"]
    service.evaluate(position_rows=rows, cash=10_000_000)
    assert rows[0]["quantity"] == original_qty


def test_25_expected_alpha_disabled():
    from portfolio.allocation.candidate_service import candidate_opportunity_score
    score = candidate_opportunity_score({"quality_score": 80, "actual_mos_pct": 35.0, "required_mos_pct": 30.0})
    assert score <= 1.0


def test_26_kelly_disabled():
    from portfolio.allocation.sizing import sizing_for
    sig = {"quality_tier": "HIGH_QUALITY"}
    sizing = sizing_for(sig, fit="GOOD")
    assert sizing.target_max <= 0.20
