"""Opportunity-cost decision engine unit tests (explicit gates, no composite score)."""
from __future__ import annotations

import pytest

from portfolio.allocation.models import CandidateOpportunity, EligibilityResult, PortfolioFitResult, SizingResult
from portfolio.allocation.opportunity import (
    MIN_VALUATION_SAFETY,
    VALUATION_SAFETY_REPLACEMENT_DELTA,
    decide_candidate,
    decide_holding,
    fit_rank,
    holding_is_rotation_eligible,
    quality_tier_rank,
    rotation_gates,
)
from portfolio.allocation.reason_codes import (
    CASH_PREFERRED,
    CORRELATION_HIGH,
    DATA_INSUFFICIENT,
    HARD_REJECT,
    PORTFOLIO_FIT_IMPROVES,
    PORTFOLIO_FIT_WEAK,
    QUALITY_DETERIORATING,
    RISK_CONTRIBUTION_HIGH,
    SUPERIOR_REPLACEMENT_AVAILABLE,
    TECHNICAL_CONFIRMATION,
    TECHNICAL_DETERIORATION,
    VALUATION_SAFETY_IMPROVES,
    VALUATION_SAFETY_INSUFFICIENT,
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
        discovery_score=kwargs.pop("discovery_score", 0.9),
        reason_codes=kwargs.pop("reason_codes", ()),
    )


# ---------------------------------------------------------------------------
# Ordinal helpers — comparison only, never weighted scalars
# ---------------------------------------------------------------------------
def test_quality_tier_rank_is_ordinal():
    assert quality_tier_rank("LOW_QUALITY") < quality_tier_rank("WATCH") < quality_tier_rank("INVESTABLE")
    assert quality_tier_rank("INVESTABLE") < quality_tier_rank("HIGH_QUALITY") < quality_tier_rank("EXCEPTIONAL")
    assert quality_tier_rank(None) == -1
    assert quality_tier_rank("UNKNOWN_TIER") == -1


def test_fit_rank_is_categorical():
    assert fit_rank("UNAVAILABLE") < fit_rank("WEAK") < fit_rank("MODERATE") < fit_rank("GOOD")
    assert fit_rank(None) == 0


# ---------------------------------------------------------------------------
# decide_candidate gates
# ---------------------------------------------------------------------------
def test_excellent_attractive_good_fit_buys_more():
    decision = decide_candidate(candidate(), cash_weight=0.30, rotation_funded=False)
    assert decision.action == "BUY_MORE"
    assert decision.target_mid == 0.15


def test_candidate_insufficient_cash_is_watch():
    decision = decide_candidate(candidate(sizing=sizing("VNM", "NORMAL")), cash_weight=0.01, rotation_funded=False)
    assert decision.action == "WATCH"
    assert CASH_PREFERRED in decision.reason_codes


def test_candidate_insufficient_cash_but_rotation_funded_buys():
    decision = decide_candidate(candidate(sizing=sizing("VNM", "NORMAL")), cash_weight=0.01, rotation_funded=True)
    assert decision.action == "BUY_MORE"


def test_candidate_weak_fit_is_watch_and_capped():
    from portfolio.allocation.sizing import sizing_for

    capped = sizing_for(
        {"symbol": "VNM", "quality_tier": "HIGH_QUALITY", "quality_score": 85, "hard_rejects": [],
         "valuation_status": "ATTRACTIVE", "actual_mos_pct": 30.0, "required_mos_pct": 25.0},
        fit="WEAK",
    )
    decision = decide_candidate(candidate(portfolio_fit=fit(level="WEAK"), sizing=capped), cash_weight=0.50, rotation_funded=False)
    assert decision.action == "WATCH"
    assert PORTFOLIO_FIT_WEAK in decision.reason_codes
    assert CORRELATION_HIGH in decision.reason_codes
    assert decision.target_max <= 0.05


def test_candidate_unavailable_risk_is_watch_not_buy():
    decision = decide_candidate(candidate(portfolio_fit=fit(level="UNAVAILABLE", risk_available=False)), cash_weight=0.50, rotation_funded=False)
    assert decision.action == "WATCH"
    assert DATA_INSUFFICIENT in decision.reason_codes


def test_candidate_negative_valuation_safety_is_watch():
    decision = decide_candidate(candidate(eligibility=dict(status="INVESTABLE", valuation_safety=-12.0)), cash_weight=0.50, rotation_funded=False)
    assert decision.action == "WATCH"
    assert VALUATION_SAFETY_INSUFFICIENT in decision.reason_codes


def test_candidate_missing_valuation_safety_is_watch():
    decision = decide_candidate(candidate(eligibility=dict(status="INVESTABLE", valuation_safety=None)), cash_weight=0.50, rotation_funded=False)
    assert decision.action == "WATCH"
    assert VALUATION_SAFETY_INSUFFICIENT in decision.reason_codes
    assert DATA_INSUFFICIENT in decision.reason_codes


def test_candidate_below_min_valuation_safety_is_watch():
    decision = decide_candidate(
        candidate(eligibility=dict(status="INVESTABLE", valuation_safety=MIN_VALUATION_SAFETY - 0.5)),
        cash_weight=0.50, rotation_funded=False,
    )
    assert decision.action == "WATCH"


def test_candidate_technical_deterioration_downgrades_buy_to_watch():
    decision = decide_candidate(candidate(), cash_weight=0.30, rotation_funded=False, technical=False)
    assert decision.action == "WATCH"
    assert TECHNICAL_DETERIORATION in decision.reason_codes


def test_candidate_technical_confirmation_only_adds_reason():
    decision = decide_candidate(candidate(), cash_weight=0.30, rotation_funded=False, technical=True)
    assert decision.action == "BUY_MORE"
    assert TECHNICAL_CONFIRMATION in decision.reason_codes


def test_technical_cannot_override_eligibility():
    # Even with positive technical confirmation, an ineligible candidate stays WATCH.
    opp = candidate(eligibility=dict(status="INELIGIBLE", hard_rejects=("ACCOUNTING_UNRELIABLE",), quality_tier="HIGH_QUALITY"))
    decision = decide_candidate(opp, cash_weight=0.50, rotation_funded=False, technical=True)
    assert decision.action == "WATCH"


# ---------------------------------------------------------------------------
# decide_holding gates
# ---------------------------------------------------------------------------
def test_hard_reject_holding_is_sell():
    decision = decide_holding(
        eligibility(status="INELIGIBLE", hard_rejects=("SOLVENCY_RISK",)),
        current_weight=0.3, risk_contribution=0.2, equal_risk=0.5,
        hard_cap=0.20, current_fit="MODERATE",
    )
    assert decision.action == "SELL"
    assert HARD_REJECT in decision.reason_codes


def test_low_quality_holding_is_reduce():
    decision = decide_holding(
        eligibility(status="INELIGIBLE", quality_tier="LOW_QUALITY", valuation_safety=None),
        current_weight=0.3, risk_contribution=0.2, equal_risk=0.5,
        hard_cap=0.20, current_fit="MODERATE",
    )
    assert decision.action == "REDUCE"
    assert QUALITY_DETERIORATING in decision.reason_codes


def test_excessive_risk_contribution_is_reduce():
    decision = decide_holding(
        eligibility(),
        current_weight=0.5, risk_contribution=0.80, equal_risk=0.5,
        hard_cap=0.20, current_fit="WEAK",
    )
    assert decision.action == "REDUCE"
    assert RISK_CONTRIBUTION_HIGH in decision.reason_codes


def test_high_quality_holding_is_hold_when_no_explicit_rule_triggers():
    decision = decide_holding(
        eligibility(),
        current_weight=0.28, risk_contribution=0.41, equal_risk=0.5,
        target_min=0.12, target_mid=0.15, target_max=0.18,
        hard_cap=0.20, current_fit="GOOD",
    )
    assert decision.action == "HOLD"
    assert "NO_SUPERIOR_REPLACEMENT" in decision.reason_codes
    assert decision.target_mid == 0.15


def test_lower_rank_holding_not_reduced_solely_due_to_rank():
    # A WATCH-tier holding with modest weight and non-excessive risk stays HOLD
    # when no candidate rotation gate passes (rank alone never sells).
    decision = decide_holding(
        eligibility(quality_tier="WATCH", quality_score=62, valuation_safety=-5.0),
        current_weight=0.2, risk_contribution=0.2, equal_risk=0.5,
        hard_cap=0.20, current_fit="MODERATE",
    )
    assert decision.action == "HOLD"


# ---------------------------------------------------------------------------
# rotation gates
# ---------------------------------------------------------------------------
def test_rotation_gates_pass_for_weak_holding_and_superior_candidate():
    holding = eligibility(quality_tier="WATCH", quality_score=62, valuation_safety=-15.0)
    superior = candidate(eligibility=dict(quality_tier="EXCEPTIONAL", quality_score=92, valuation_safety=17.0))
    passed, reasons = rotation_gates(holding, holding_fit="MODERATE", candidate=superior)
    assert passed is True
    assert SUPERIOR_REPLACEMENT_AVAILABLE in reasons
    assert VALUATION_SAFETY_IMPROVES in reasons


def test_rotation_requires_material_valuation_improvement():
    holding = eligibility(quality_tier="WATCH", quality_score=62, valuation_safety=-5.0)
    marginal = candidate(eligibility=dict(quality_tier="HIGH_QUALITY", valuation_safety=-2.0))
    passed, _ = rotation_gates(holding, holding_fit="MODERATE", candidate=marginal)
    assert passed is False  # delta 3 pp < 10 pp hysteresis buffer


def test_rotation_requires_all_gates():
    holding = eligibility(quality_tier="WATCH", quality_score=62, valuation_safety=-15.0)
    # Candidate fit WEAK -> no rotation even with much better valuation.
    weak_fit = candidate(portfolio_fit=fit(level="WEAK"), eligibility=dict(valuation_safety=17.0))
    assert rotation_gates(holding, holding_fit="MODERATE", candidate=weak_fit)[0] is False
    # Candidate quality worse (ordinal) -> no rotation.
    worse_quality = candidate(eligibility=dict(quality_tier="LOW_QUALITY", quality_score=40, valuation_safety=17.0))
    assert rotation_gates(holding, holding_fit="MODERATE", candidate=worse_quality)[0] is False
    # Candidate not investable -> no rotation.
    not_investable = candidate(eligibility=dict(status="WATCHLIST", quality_tier="WATCH", valuation_safety=17.0))
    assert rotation_gates(holding, holding_fit="MODERATE", candidate=not_investable)[0] is False


def test_rotation_never_rotates_a_good_holding():
    holding = eligibility(quality_tier="HIGH_QUALITY", quality_score=85, valuation_safety=7.0)
    superior = candidate(eligibility=dict(quality_tier="EXCEPTIONAL", quality_score=92, valuation_safety=40.0))
    passed, _ = rotation_gates(holding, holding_fit="GOOD", candidate=superior)
    assert passed is False  # good holding is not rotation-eligible


def test_rotation_improves_portfolio_fit_reason_added_when_better():
    holding = eligibility(quality_tier="WATCH", quality_score=62, valuation_safety=-15.0)
    superior = candidate(
        portfolio_fit=fit(level="GOOD"),
        eligibility=dict(quality_tier="EXCEPTIONAL", quality_score=92, valuation_safety=17.0),
    )
    _, reasons = rotation_gates(holding, holding_fit="MODERATE", candidate=superior)
    assert PORTFOLIO_FIT_IMPROVES in reasons


def test_holding_without_public_valuation_can_be_rotated_with_qualified_candidate():
    holding = eligibility(quality_tier="HIGH_QUALITY", quality_score=85, valuation_safety=None, status="WATCHLIST")
    assert holding_is_rotation_eligible(holding) is True
    qualified = candidate(eligibility=dict(valuation_safety=20.0))
    passed, reasons = rotation_gates(holding, holding_fit="MODERATE", candidate=qualified)
    assert passed is True
    assert VALUATION_SAFETY_IMPROVES in reasons


def test_holding_is_rotation_eligible_explicit_rules():
    assert holding_is_rotation_eligible(eligibility(quality_tier="WATCH")) is True
    assert holding_is_rotation_eligible(eligibility(quality_tier="LOW_QUALITY")) is True
    assert holding_is_rotation_eligible(eligibility(valuation_safety=None)) is True
    assert holding_is_rotation_eligible(eligibility(quality_tier="HIGH_QUALITY", valuation_safety=7.0)) is False
    assert holding_is_rotation_eligible(eligibility(status="INELIGIBLE", quality_tier="LOW_QUALITY")) is False


def test_bands_expose_separate_dimensions_not_a_composite():
    decision = decide_candidate(candidate(), cash_weight=0.30, rotation_funded=False)
    bands = decision.bands
    assert "business_quality_tier" in bands
    assert "valuation_safety_pp" in bands
    assert "portfolio_fit" in bands
    assert "technical_confirmation" in bands
    assert "opportunity_score" not in bands
    assert bands["business_quality_tier"] == "HIGH_QUALITY"