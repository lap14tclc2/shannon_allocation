"""Opportunity-cost decision engine unit tests (explicit gates, no composite score)."""
from __future__ import annotations

import pytest

from portfolio.allocation.eligibility import eligibility_from_signal
from portfolio.allocation.models import (
    AllocationDecision,
    CandidateOpportunity,
    EligibilityResult,
    PortfolioFitResult,
    SizingResult,
)
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
    assert decision.action == "HOLD"
    assert "REVIEW_REQUIRED" in decision.reason_codes
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
    assert decision.post_action_target_weight == 0.28
    assert decision.new_position_guidance["mid_weight"] == 0.15


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


# ---------------------------------------------------------------------------
# Semantic Invariant & Matrix Tests (TASK-20260906-100)
# ---------------------------------------------------------------------------

def test_reduce_cannot_have_zero_target():
    """Requirement 1: REDUCE can never target 0%."""
    import pytest
    with pytest.raises(ValueError, match="REDUCE decision.*cannot target <= 0%"):
        AllocationDecision(
            symbol="REE",
            action="REDUCE",
            current_weight=0.10,
            target_min=0.0,
            target_mid=0.0,
            target_max=0.0,
        )


def test_sell_must_have_zero_target():
    """Requirement 2: SELL must have target_mid == 0."""
    import pytest
    with pytest.raises(ValueError, match="SELL decision.*must target 0%"):
        AllocationDecision(
            symbol="FRT",
            action="SELL",
            current_weight=0.10,
            target_min=0.05,
            target_mid=0.05,
            target_max=0.05,
        )
    valid_sell = AllocationDecision(
        symbol="FRT",
        action="SELL",
        current_weight=0.10,
        target_min=0.0,
        target_mid=0.0,
        target_max=0.0,
    )
    assert valid_sell.target_mid == 0.0


def test_data_insufficient_alone_produces_hold_review():
    """Requirement 3: DATA_INSUFFICIENT alone on existing holding -> HOLD/REVIEW."""
    sig = {
        "symbol": "GAS",
        "quality_tier": "WATCH",
        "hard_rejects": ["DATA_INSUFFICIENT"],
    }
    elig = eligibility_from_signal(sig)
    dec = decide_holding(elig, current_weight=0.15, risk_contribution=None, equal_risk=None)
    assert dec.action == "HOLD"
    assert dec.target_mid == 0.15
    assert "REVIEW_REQUIRED" in dec.reason_codes
    assert "DATA_INSUFFICIENT" in dec.reason_codes


def test_missing_public_valuation_alone_produces_hold_review():
    """Requirement 4: Missing public valuation alone -> HOLD/REVIEW."""
    sig = {
        "symbol": "GAS",
        "quality_tier": "HIGH_QUALITY",
        "actual_mos_pct": None,
        "required_mos_pct": None,
    }
    elig = eligibility_from_signal(sig)
    dec = decide_holding(elig, current_weight=0.10, risk_contribution=None, equal_risk=None)
    assert dec.action == "HOLD"
    assert dec.target_mid == 0.10
    assert "REVIEW_REQUIRED" in dec.reason_codes


def test_low_valuation_confidence_alone_produces_hold_review():
    """Requirement 5: LOW valuation confidence alone -> HOLD/REVIEW."""
    sig = {
        "symbol": "KSV",
        "quality_tier": "INVESTABLE",
        "actual_mos_pct": 20.0,
        "required_mos_pct": 15.0,
        "valuation_confidence": "LOW",
    }
    elig = eligibility_from_signal(sig)
    dec = decide_holding(elig, current_weight=0.08, risk_contribution=None, equal_risk=None)
    assert dec.action == "HOLD"
    assert dec.target_mid == 0.08
    assert "REVIEW_REQUIRED" in dec.reason_codes


def test_low_quality_confirmed_produces_reduce_positive():
    """Requirement 6: LOW_QUALITY confirmed -> REDUCE with positive target."""
    sig = {
        "symbol": "REE",
        "quality_tier": "LOW_QUALITY",
        "quality_score": 45,
    }
    elig = eligibility_from_signal(sig)
    dec = decide_holding(elig, current_weight=0.12, risk_contribution=None, equal_risk=None)
    assert dec.action == "REDUCE"
    assert dec.target_mid is not None
    assert dec.target_mid > 0.0
    assert dec.target_mid < 0.12


def test_solvency_risk_produces_sell():
    """Requirement 7: SOLVENCY_RISK -> SELL with 0% target."""
    sig = {
        "symbol": "FRT",
        "quality_tier": "INVESTABLE",
        "hard_rejects": ["SOLVENCY_RISK"],
    }
    elig = eligibility_from_signal(sig)
    dec = decide_holding(elig, current_weight=0.10, risk_contribution=None, equal_risk=None)
    assert dec.action == "SELL"
    assert dec.target_mid == 0.0


def test_accounting_unreliable_produces_sell():
    """Requirement 8: ACCOUNTING_UNRELIABLE -> SELL with 0% target."""
    sig = {
        "symbol": "FRT",
        "quality_tier": "HIGH_QUALITY",
        "hard_rejects": ["ACCOUNTING_UNRELIABLE"],
    }
    elig = eligibility_from_signal(sig)
    dec = decide_holding(elig, current_weight=0.10, risk_contribution=None, equal_risk=None)
    assert dec.action == "SELL"
    assert dec.target_mid == 0.0


def test_excessive_risk_contribution_produces_reduce_positive():
    """Requirement 9: Excessive risk contribution -> HOLD + REVIEW, not REDUCE."""
    sig = {
        "symbol": "VGI",
        "quality_tier": "HIGH_QUALITY",
        "actual_mos_pct": 25.0,
        "required_mos_pct": 15.0,
    }
    elig = eligibility_from_signal(sig)
    dec = decide_holding(
        elig,
        current_weight=0.35,
        risk_contribution=0.50,
        equal_risk=0.20,
    )
    assert dec.action == "HOLD"
    assert dec.target_mid == 0.35
    assert "REVIEW_REQUIRED" in dec.reason_codes
    assert "RISK_CONTRIBUTION_HIGH" in dec.reason_codes


def test_reported_symbols_synthetic_fixtures_regression():
    """Requirement 21: Regression fixtures for reported symbols (FRT, VJC, KSV, REE, GAS)."""
    cases = [
        # 1. Thesis break (FRT) -> SELL 0%
        (
            {"symbol": "FRT", "quality_tier": "INVESTABLE", "hard_rejects": ["SOLVENCY_RISK"]},
            0.10, "SELL", 0.0,
        ),
        # 2. Missing data (VJC) -> HOLD / REVIEW
        (
            {"symbol": "VJC", "quality_tier": "WATCH", "hard_rejects": ["DATA_INSUFFICIENT"]},
            0.08, "HOLD", 0.08,
        ),
        # 3. Low confidence (KSV) -> HOLD / REVIEW
        (
            {"symbol": "KSV", "quality_tier": "INVESTABLE", "actual_mos_pct": 15.0, "required_mos_pct": 10.0, "valuation_confidence": "LOW"},
            0.05, "HOLD", 0.05,
        ),
        # 4. Confirmed Low Quality (REE) -> REDUCE > 0
        (
            {"symbol": "REE", "quality_tier": "LOW_QUALITY", "quality_score": 40},
            0.12, "REDUCE", "POSITIVE",
        ),
        # 5. Data Insufficient (GAS) -> HOLD / REVIEW
        (
            {"symbol": "GAS", "quality_tier": None, "hard_rejects": ["DATA_INSUFFICIENT"]},
            0.15, "HOLD", 0.15,
        ),
    ]

    for sig, weight, expected_action, expected_target_type in cases:
        elig = eligibility_from_signal(sig)
        dec = decide_holding(elig, current_weight=weight, risk_contribution=None, equal_risk=None)
        assert dec.action == expected_action
        if expected_target_type == 0.0:
            assert dec.target_mid == 0.0
        elif expected_target_type == "POSITIVE":
            assert dec.target_mid is not None and 0.0 < dec.target_mid < weight
        elif isinstance(expected_target_type, float):
            assert dec.target_mid == expected_target_type
            assert "REVIEW_REQUIRED" in dec.reason_codes


def test_reduce_small_holding_weight_never_targets_zero():
    """Verify that REDUCE on tiny holding weights (e.g. HHV) never produces target_mid <= 0.0."""
    sig = {"symbol": "HHV", "quality_tier": "LOW_QUALITY", "quality_score": 35}
    elig = eligibility_from_signal(sig)
    for small_w in (0.001, 0.0001, 0.00005):
        dec = decide_holding(elig, current_weight=small_w, risk_contribution=None, equal_risk=None)
        assert dec.action == "REDUCE"
        assert dec.target_mid is not None
        assert 0.0 < dec.target_mid < small_w
        assert 0.0 < dec.target_min <= dec.target_mid <= dec.target_max


def test_circle_of_competence_fail_does_not_sell():
    """Invariant: CIRCLE_OF_COMPETENCE_FAIL is non-destructive evidence and must NOT cause SELL."""
    sig = {
        "symbol": "TECH_STARTUP",
        "quality_tier": "WATCH",
        "hard_rejects": ["CIRCLE_OF_COMPETENCE_FAIL"],
    }
    elig = eligibility_from_signal(sig)
    dec = decide_holding(elig, current_weight=0.10, risk_contribution=None, equal_risk=None)
    assert dec.action != "SELL"
    assert dec.action == "HOLD"
    assert dec.target_mid == 0.10