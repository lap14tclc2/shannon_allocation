"""Opportunity-cost decision engine (conservative, hysteresis-guarded).

V1 must NOT use expected alpha or Kelly. Decision components are kept
transparent:

    business_quality_band
    valuation_safety_band
    portfolio_fit_band
    technical_confirmation_band

Decision hierarchy:
    1. hard reject / thesis broken            -> SELL or REDUCE
    2. excessive concentration / risk          -> REDUCE
    3. good holding + no superior replacement  -> HOLD
    4. investable candidate + cash + good fit  -> BUY_MORE
    5. weak holding + materially superior candidate -> REDUCE/ROTATE
    6. otherwise                               -> HOLD / KEEP_CASH

Hysteresis: small score/rank changes never create trades.
"""
from __future__ import annotations

from .models import AllocationDecision, CandidateOpportunity, EligibilityResult
from .reason_codes import (
    CASH_PREFERRED,
    CORRELATION_HIGH,
    DATA_INSUFFICIENT,
    HARD_REJECT,
    NO_SUPERIOR_REPLACEMENT,
    POSITION_CONCENTRATED,
    QUALITY_DETERIORATING,
    RISK_CONTRIBUTION_HIGH,
    SUPERIOR_REPLACEMENT_AVAILABLE,
    VALUATION_SAFETY_NEGATIVE,
)

# Weighting of the transparent opportunity bands (sums to 1.0).
QUALITY_WEIGHT = 0.45
VALUATION_WEIGHT = 0.30
FIT_WEIGHT = 0.20
TECHNICAL_WEIGHT = 0.05

# Hysteresis: a replacement must beat a weak holding by at least this much
# (in opportunity-score delta) before a rotation is proposed.
ROTATION_ADVANTAGE_THRESHOLD = 0.15
# A holding with full opportunity score below this is considered weak.
WEAK_HOLDING_SCORE = 0.50
# Risk-contribution "excessive" breach, matching the existing QPort health
# convention: largest contributor > max(45%, 1.5 x equal-risk) flags a
# RISK_CONCENTRATION warning. High-but-not-excessive contributions are
# informational only and never force a trade.
RISK_CONTRIBUTION_BREACH_MULTIPLIER = 1.50
RISK_CONTRIBUTION_ABSOLUTE_BREACH = 0.45
# Nominal weight above which a holding is flagged as concentrated (informational).
POSITION_CONCENTRATED_WEIGHT = 0.40
# Correlation to the rest of the portfolio that marks a candidate as
# concentration-dampening vs concentration-increasing.
HIGH_CORRELATION_THRESHOLD = 0.70

QUALITY_TIER_BAND = {
    "EXCEPTIONAL": 1.0,
    "HIGH_QUALITY": 0.8,
    "INVESTABLE": 0.6,
    "WATCH": 0.4,
    "LOW_QUALITY": 0.1,
}


def quality_band(tier: str | None) -> float:
    return QUALITY_TIER_BAND.get((tier or "").upper(), 0.0)


def valuation_safety_band(safety: float | None) -> float:
    if safety is None:
        return 0.0
    if safety >= 10.0:
        return 1.0
    if safety >= 0.0:
        return 0.6
    if safety >= -10.0:
        return 0.3
    return 0.0


def fit_band(fit: str | None) -> float:
    mapping = {"GOOD": 1.0, "MODERATE": 0.6, "WEAK": 0.2}
    if fit is None or fit == "UNAVAILABLE":
        return 0.0
    return mapping.get(fit, 0.0)


def full_opportunity_score(
    eligibility: EligibilityResult,
    fit: str | None,
    technical_band: float = 0.5,
) -> float:
    """Transparent weighted combination of the four opportunity bands."""
    q = quality_band(eligibility.quality_tier)
    v = valuation_safety_band(eligibility.valuation_safety)
    f = fit_band(fit)
    t = max(0.0, min(1.0, float(technical_band)))
    return round(
        QUALITY_WEIGHT * q + VALUATION_WEIGHT * v + FIT_WEIGHT * f + TECHNICAL_WEIGHT * t,
        4,
    )


def opportunity_bands(
    eligibility: EligibilityResult,
    fit: str | None,
    technical_band: float = 0.5,
) -> dict[str, float | None]:
    return {
        "business_quality_band": quality_band(eligibility.quality_tier),
        "valuation_safety_band": valuation_safety_band(eligibility.valuation_safety),
        "portfolio_fit_band": fit_band(fit),
        "technical_confirmation_band": max(0.0, min(1.0, float(technical_band))),
        "opportunity_score": full_opportunity_score(eligibility, fit, technical_band),
    }


def _dedupe(reasons: list[str]) -> tuple[str, ...]:
    return tuple(dict.fromkeys(reasons))


def decide_holding(
    eligibility: EligibilityResult,
    *,
    current_weight: float,
    risk_contribution: float | None,
    equal_risk: float | None,
    target_min: float | None = None,
    target_mid: float | None = None,
    target_max: float | None = None,
    hard_cap: float,
    current_fit: str,
    best_replacement_advantage: float = 0.0,
) -> AllocationDecision:
    """Advisory decision for a current holding."""
    reasons = list(eligibility.reason_codes)
    confidence = "MEDIUM"
    weight = max(0.0, float(current_weight))
    rc = risk_contribution if risk_contribution is not None else None
    bands = opportunity_bands(eligibility, current_fit)
    score = bands["opportunity_score"]

    # 1. Hard reject / thesis broken -> SELL.
    if eligibility.hard_rejects:
        reasons.append(HARD_REJECT)
        return AllocationDecision(
            symbol=eligibility.symbol, action="SELL", kind="HOLDING",
            current_weight=weight, target_min=0.0, target_mid=0.0, target_max=0.0,
            confidence="HIGH", reason_codes=_dedupe(reasons), bands=bands,
        )

    # 1b. LOW_QUALITY (no hard reject) -> REDUCE.
    if eligibility.status == "INELIGIBLE":
        reasons.append(QUALITY_DETERIORATING)
        return AllocationDecision(
            symbol=eligibility.symbol, action="REDUCE", kind="HOLDING",
            current_weight=weight, target_min=0.0, target_mid=0.0,
            target_max=min(weight, 0.05), confidence="MEDIUM",
            reason_codes=_dedupe(reasons), bands=bands,
        )

    # 2. Excessive risk contribution (matching QPort health convention) -> REDUCE.
    #    Nominal weight > hard_cap alone does NOT force a sell; it is flagged
    #    as informational POSITION_CONCENTRATED (the plan's example holds a 28%
    #    position as HOLD with RISK_CONTRIBUTION_HIGH listed as a reason).
    risk_breach = False
    if rc is not None and equal_risk is not None and equal_risk > 0:
        risk_breach = rc > max(RISK_CONTRIBUTION_ABSOLUTE_BREACH, RISK_CONTRIBUTION_BREACH_MULTIPLIER * equal_risk)
    if weight >= POSITION_CONCENTRATED_WEIGHT:
        reasons.append(POSITION_CONCENTRATED)
    if risk_breach:
        reasons.append(RISK_CONTRIBUTION_HIGH)
    if risk_breach:
        reduce_target = max(0.0, min(weight, 0.25))
        return AllocationDecision(
            symbol=eligibility.symbol, action="REDUCE", kind="HOLDING",
            current_weight=weight, target_min=0.0, target_mid=reduce_target,
            target_max=reduce_target, confidence="MEDIUM",
            reason_codes=_dedupe(reasons), bands=bands,
        )

    # 3. Good holding + no materially better replacement -> HOLD.
    if score >= WEAK_HOLDING_SCORE and best_replacement_advantage < ROTATION_ADVANTAGE_THRESHOLD:
        reasons.append(NO_SUPERIOR_REPLACEMENT)
        return AllocationDecision(
            symbol=eligibility.symbol, action="HOLD", kind="HOLDING",
            current_weight=weight, target_min=target_min,
            target_mid=target_mid, target_max=target_max,
            confidence="MEDIUM", reason_codes=_dedupe(reasons), bands=bands,
        )

    # 5. Weak holding + materially superior candidate -> REDUCE/ROTATE.
    if best_replacement_advantage >= ROTATION_ADVANTAGE_THRESHOLD:
        reasons.append(SUPERIOR_REPLACEMENT_AVAILABLE)
        return AllocationDecision(
            symbol=eligibility.symbol, action="REDUCE", kind="HOLDING",
            current_weight=weight, target_min=0.0, target_mid=0.0,
            target_max=0.0, confidence="MEDIUM",
            reason_codes=_dedupe(reasons), bands=bands,
        )

    # 6. Otherwise -> HOLD (lower rank alone never forces a sell).
    return AllocationDecision(
        symbol=eligibility.symbol, action="HOLD", kind="HOLDING",
        current_weight=weight, target_min=None, target_mid=None, target_max=None,
        confidence="LOW", reason_codes=_dedupe(reasons), bands=bands,
    )


def decide_candidate(
    candidate: CandidateOpportunity,
    *,
    cash_weight: float,
    rotation_funded: bool = False,
) -> AllocationDecision:
    """Advisory decision for a research candidate (BUY_MORE / WATCH)."""
    eligibility = candidate.eligibility
    reasons = list(candidate.reason_codes)
    fit = candidate.portfolio_fit
    sizing = candidate.sizing
    fit_level = fit.fit if fit else "UNAVAILABLE"
    bands = opportunity_bands(eligibility, fit_level)
    score = bands["opportunity_score"]

    if eligibility.status != "INVESTABLE":
        reasons.append(DATA_INSUFFICIENT)
        return AllocationDecision(
            symbol=eligibility.symbol, action="WATCH", kind="CANDIDATE",
            current_weight=0.0, target_min=None, target_mid=None, target_max=None,
            confidence="LOW", reason_codes=_dedupe(reasons), bands=bands,
        )

    if fit is None or fit_level == "UNAVAILABLE":
        reasons.append(DATA_INSUFFICIENT)
        return AllocationDecision(
            symbol=eligibility.symbol, action="WATCH", kind="CANDIDATE",
            current_weight=0.0, target_min=None, target_mid=None, target_max=None,
            confidence="LOW", reason_codes=_dedupe(reasons), bands=bands,
        )

    if fit_level == "WEAK":
        reasons.extend(code for code in (CORRELATION_HIGH, RISK_CONTRIBUTION_HIGH) if code not in reasons)
        reasons.append(DATA_INSUFFICIENT if fit.risk_available is False else None)
        reasons = [r for r in reasons if r is not None]
        return AllocationDecision(
            symbol=eligibility.symbol, action="WATCH", kind="CANDIDATE",
            current_weight=0.0,
            target_min=sizing.target_min if sizing else None,
            target_mid=sizing.target_mid if sizing else None,
            target_max=sizing.target_max if sizing else None,
            confidence="LOW", reason_codes=_dedupe(reasons), bands=bands,
        )

    if sizing is None or sizing.target_mid <= 0:
        reasons.append(DATA_INSUFFICIENT)
        return AllocationDecision(
            symbol=eligibility.symbol, action="WATCH", kind="CANDIDATE",
            current_weight=0.0, target_min=None, target_mid=None, target_max=None,
            confidence="LOW", reason_codes=_dedupe(reasons), bands=bands,
        )

    # Attractive-enough valuation required to commit new capital.
    if eligibility.valuation_safety is not None and eligibility.valuation_safety < 0:
        reasons.append(VALUATION_SAFETY_NEGATIVE)
        return AllocationDecision(
            symbol=eligibility.symbol, action="WATCH", kind="CANDIDATE",
            current_weight=0.0, target_min=sizing.target_min, target_mid=sizing.target_mid,
            target_max=sizing.target_max, confidence="LOW",
            reason_codes=_dedupe(reasons), bands=bands,
        )

    # Cash must cover at least the starter size (unless rotation funds it).
    if not rotation_funded and cash_weight is not None and cash_weight < sizing.target_min:
        reasons.append(CASH_PREFERRED)
        return AllocationDecision(
            symbol=eligibility.symbol, action="WATCH", kind="CANDIDATE",
            current_weight=0.0, target_min=sizing.target_min, target_mid=sizing.target_mid,
            target_max=sizing.target_max, confidence="MEDIUM",
            reason_codes=_dedupe(reasons), bands=bands,
        )

    confidence = "HIGH" if fit_level == "GOOD" and eligibility.valuation_confidence in ("HIGH", None) else "MEDIUM"
    return AllocationDecision(
        symbol=eligibility.symbol, action="BUY_MORE", kind="CANDIDATE",
        current_weight=0.0, target_min=sizing.target_min, target_mid=sizing.target_mid,
        target_max=sizing.target_max, confidence=confidence,
        reason_codes=_dedupe(reasons), bands=bands,
    )


def evaluate_rotation(
    holding_score: float,
    candidate_score: float,
) -> float:
    """Return the replacement advantage (candidate - holding).

    Rotation is proposed only when the advantage clears the hysteresis
    threshold AND the holding is weak (checked by the caller).
    """
    return round(candidate_score - holding_score, 4)