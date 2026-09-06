"""Opportunity-cost decision engine unit tests."""
from __future__ import annotations

import pytest

from portfolio.allocation.models import CandidateOpportunity, EligibilityResult, PortfolioFitResult, SizingResult
from portfolio.allocation.opportunity import (
    ROTATION_ADVANTAGE_THRESHOLD,
    decide_candidate,
    decide_holding,
    evaluate_rotation,
    full_opportunity_score,
    opportunity_bands,
)


def eligibility(**kwargs):
    base = {
        "symbol": "FPT",
        "status": "INVESTABLE",
        "quality_tier": "HIGH_QUALITY",
        "quality_score": 85,
        "valuation_safety": 7.0,
        "valuation_confidence": "MEDIUM",
        "reason_codes": ("QUALITY_STRONG",),
    }
    base.update(kwargs)
    return EligibilityResult(**base)


def fit(symbol="VNM", level="GOOD", risk_available=True):
    return PortfolioFitResult(
        symbol=symbol, current_weight=0.0, proposed_weight=0.10,
        portfolio_vol_before=0.20, portfolio_vol_after=0.19,
        risk_contribution_before=0.0, risk_contribution_after=0.05,
        average_correlation_to_portfolio=0.2, max_correlation_to_portfolio=0.3,
        risk_available=risk_available, fit=level,
    )


def sizing(symbol="VNM", tier="HIGH_CONVICTION"):
    bands = {"STARTER": (0.03, 0.04, 0.05), "NORMAL": (0.07, 0.10, 0.12), "HIGH_CONVICTION": (0.12, 0.15, 0.18)}
    low, mid, high = bands[tier]
    return SizingResult(symbol=symbol, conviction_tier=tier, target_min=low, target_mid=mid, target_max=high)


def candidate(symbol="VNM", **kwargs):
    return CandidateOpportunity(
        symbol=symbol,
        source="SCREENER",
        eligibility=eligibility(**kwargs.pop("eligibility", {})),
        candidate_rank=1,
        portfolio_fit=kwargs.pop("portfolio_fit", fit(symbol)),
        sizing=kwargs.pop("sizing", sizing(symbol)),
        opportunity_score=kwargs.pop("opportunity_score", 0.9),
        reason_codes=kwargs.pop("reason_codes", ()),
    )


def test_excellent_attractive_good_fit_buys_more():
    opp = candidate()
    decision = decide_candidate(opp, cash_weight=0.30, rotation_funded=False)
    assert decision.action == "BUY_MORE"
    assert decision.target_mid == 0.15


def test_candidate_insufficient_cash_is_watch():
    opp = candidate(sizing=sizing("VNM", "NORMAL"))
    decision = decide_candidate(opp, cash_weight=0.01, rotation_funded=False)
    assert decision.action == "WATCH"
    assert "CASH_PREFERRED" in decision.reason_codes


def test_candidate_insufficient_cash_but_rotation_funded_buys():
    opp = candidate(sizing=sizing("VNM", "NORMAL"))
    decision = decide_candidate(opp, cash_weight=0.01, rotation_funded=True)
    assert decision.action == "BUY_MORE"


def test_candidate_weak_fit_is_watch_and_capped():
    from portfolio.allocation.sizing import sizing_for

    capped = sizing_for(
        {"symbol": "VNM", "quality_tier": "HIGH_QUALITY", "quality_score": 85, "hard_rejects": [],
         "valuation_status": "ATTRACTIVE", "actual_mos_pct": 30.0, "required_mos_pct": 25.0},
        fit="WEAK",
    )
    opp = candidate(portfolio_fit=fit(level="WEAK"), sizing=capped)
    decision = decide_candidate(opp, cash_weight=0.50, rotation_funded=False)
    assert decision.action == "WATCH"
    assert "CORRELATION_HIGH" in decision.reason_codes
    assert decision.target_max <= 0.05


def test_candidate_unavailable_risk_is_watch_not_buy():
    opp = candidate(portfolio_fit=fit(level="UNAVAILABLE", risk_available=False))
    decision = decide_candidate(opp, cash_weight=0.50, rotation_funded=False)
    assert decision.action == "WATCH"
    assert "DATA_INSUFFICIENT" in decision.reason_codes


def test_candidate_negative_valuation_safety_is_watch():
    opp = candidate(eligibility=dict(status="INVESTABLE", valuation_safety=-12.0))
    decision = decide_candidate(opp, cash_weight=0.50, rotation_funded=False)
    assert decision.action == "WATCH"
    assert "VALUATION_SAFETY_NEGATIVE" in decision.reason_codes


def test_hard_reject_holding_is_sell():
    decision = decide_holding(
        eligibility(status="INELIGIBLE", hard_rejects=("SOLVENCY_RISK",)),
        current_weight=0.3, risk_contribution=0.2, equal_risk=0.5,
        hard_cap=0.20, current_fit="MODERATE",
    )
    assert decision.action == "SELL"
    assert "HARD_REJECT" in decision.reason_codes


def test_low_quality_holding_is_reduce():
    decision = decide_holding(
        eligibility(status="INELIGIBLE", quality_tier="LOW_QUALITY", valuation_safety=None),
        current_weight=0.3, risk_contribution=0.2, equal_risk=0.5,
        hard_cap=0.20, current_fit="MODERATE",
    )
    assert decision.action == "REDUCE"


def test_excessive_risk_contribution_is_reduce():
    decision = decide_holding(
        eligibility(),
        current_weight=0.5, risk_contribution=0.80, equal_risk=0.5,
        hard_cap=0.20, current_fit="WEAK",
    )
    assert decision.action == "REDUCE"
    assert "RISK_CONTRIBUTION_HIGH" in decision.reason_codes


def test_good_holding_no_superior_replacement_is_hold():
    decision = decide_holding(
        eligibility(),
        current_weight=0.28, risk_contribution=0.41, equal_risk=0.5,
        target_min=0.12, target_mid=0.15, target_max=0.18,
        hard_cap=0.20, current_fit="GOOD", best_replacement_advantage=0.0,
    )
    assert decision.action == "HOLD"
    assert "NO_SUPERIOR_REPLACEMENT" in decision.reason_codes
    # High-but-not-excessive contribution is informational, not a forced sale.
    assert decision.target_mid == 0.15


def test_weak_holding_with_superior_replacement_is_reduce():
    decision = decide_holding(
        eligibility(quality_tier="WATCH", quality_score=62, valuation_safety=-5.0),
        current_weight=0.2, risk_contribution=0.2, equal_risk=0.5,
        hard_cap=0.20, current_fit="MODERATE",
        best_replacement_advantage=ROTATION_ADVANTAGE_THRESHOLD + 0.1,
    )
    assert decision.action == "REDUCE"
    assert "SUPERIOR_REPLACEMENT_AVAILABLE" in decision.reason_codes


def test_weak_holding_without_superior_replacement_is_hold():
    decision = decide_holding(
        eligibility(quality_tier="WATCH", quality_score=62, valuation_safety=-5.0),
        current_weight=0.2, risk_contribution=0.2, equal_risk=0.5,
        hard_cap=0.20, current_fit="MODERATE", best_replacement_advantage=0.0,
    )
    assert decision.action == "HOLD"
    # Lower rank alone never forces a sell.


def test_hysteresis_blocks_marginal_rotation():
    assert evaluate_rotation(0.45, 0.50) < ROTATION_ADVANTAGE_THRESHOLD
    assert evaluate_rotation(0.45, 0.62) >= ROTATION_ADVANTAGE_THRESHOLD


def test_opportunity_bands_are_transparent():
    bands = opportunity_bands(eligibility(), "GOOD")
    assert set(bands) == {
        "business_quality_band",
        "valuation_safety_band",
        "portfolio_fit_band",
        "technical_confirmation_band",
        "opportunity_score",
    }
    assert 0.0 <= bands["opportunity_score"] <= 1.0


def test_full_opportunity_score_keeps_quality_and_valuation_separate():
    # A WATCH-tier business cannot be rescued into a top opportunity by a huge
    # margin of safety alone; a high-quality + attractive combination ranks above it.
    watch_huge_mos = full_opportunity_score(eligibility(quality_tier="WATCH", quality_score=60, valuation_safety=15.0), "GOOD")
    high_quality_attractive = full_opportunity_score(eligibility(quality_tier="HIGH_QUALITY", quality_score=85, valuation_safety=7.0), "GOOD")
    assert watch_huge_mos < high_quality_attractive