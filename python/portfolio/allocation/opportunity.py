"""Opportunity-cost decision engine — explicit rule gates (no composite score).

V1 uses a deterministic sequence of gates, NOT an unvalidated weighted factor
score. Decision dimensions are kept separate and never collapsed into one
weighted scalar:

    business quality   -> ordinal tier  (EXCEPTIONAL > HIGH_QUALITY > INVESTABLE
                                          > WATCH > LOW_QUALITY)
    valuation safety   -> pp            (actual_mos_pct - required_mos_pct)
    portfolio fit      -> categorical   (GOOD / MODERATE / WEAK / UNAVAILABLE)
    technical signal   -> secondary evidence only (never required, never weighted)

Thresholds below are conservative governance defaults. They are documented
policy choices, NOT empirically calibrated, and must never be described as
expected alpha.

Decision hierarchy:
    A. hard reject / thesis break        -> SELL or REDUCE
    B. fundamental deterioration         -> REDUCE (LOW_QUALITY / INELIGIBLE)
    C. excessive portfolio risk          -> REDUCE (canonical risk thresholds)
    D. normal good holding               -> HOLD
    E. new candidate gates               -> BUY_MORE only if all gates pass
    F. rotation gates                    -> REDUCE/ROTATE only if all gates pass
    otherwise                            -> HOLD / KEEP_CASH

HOLD is the default action. Lower rank alone never forces a trade.
"""
from __future__ import annotations

from .models import AllocationDecision, CandidateOpportunity, EligibilityResult
from .reason_codes import (
    CASH_PREFERRED,
    CORRELATION_HIGH,
    DATA_INSUFFICIENT,
    HARD_REJECT,
    NO_SUPERIOR_REPLACEMENT,
    PORTFOLIO_FIT_IMPROVES,
    PORTFOLIO_FIT_WEAK,
    POSITION_CONCENTRATED,
    QUALITY_DETERIORATING,
    QUALITY_STRONG,
    RISK_CONTRIBUTION_HIGH,
    SUPERIOR_REPLACEMENT_AVAILABLE,
    TECHNICAL_CONFIRMATION,
    TECHNICAL_DETERIORATION,
    VALUATION_SAFETY_IMPROVES,
    VALUATION_SAFETY_INSUFFICIENT,
)

# ---------------------------------------------------------------------------
# Ordinal / categorical references (comparison only, never weighted scalars)
# ---------------------------------------------------------------------------
QUALITY_TIER_ORDER: tuple[str, ...] = (
    "LOW_QUALITY", "WATCH", "INVESTABLE", "HIGH_QUALITY", "EXCEPTIONAL",
)
FIT_ORDER: tuple[str, ...] = ("UNAVAILABLE", "WEAK", "MODERATE", "GOOD")

# ---------------------------------------------------------------------------
# Governance thresholds (conservative defaults, configurable, NOT alpha)
# ---------------------------------------------------------------------------
# Minimum valuation safety (pp) a candidate must clear to be BUY_MORE.
MIN_VALUATION_SAFETY = 0.0
# Material improvement in valuation safety (pp) required to propose a rotation.
# Conservative hysteresis buffer — a policy choice, never an empirical optimum.
VALUATION_SAFETY_REPLACEMENT_DELTA = 10.0

# Risk-contribution "excessive" breach, matching the existing QPort health
# convention: largest contributor > max(45%, 1.5 x equal-risk).
RISK_CONTRIBUTION_BREACH_MULTIPLIER = 1.50
RISK_CONTRIBUTION_ABSOLUTE_BREACH = 0.45
# Nominal weight above which a holding is flagged as concentrated (informational).
POSITION_CONCENTRATED_WEIGHT = 0.40
# Correlation to the rest of the portfolio that marks a candidate as
# concentration-increasing vs concentration-dampening.
HIGH_CORRELATION_THRESHOLD = 0.70


def quality_tier_rank(tier: str | None) -> int:
    """Ordinal rank of a quality tier (comparison only, not a weighted score)."""
    if not tier:
        return -1
    try:
        return QUALITY_TIER_ORDER.index((tier or "").upper())
    except ValueError:
        return -1


def fit_rank(fit: str | None) -> int:
    """Ordinal rank of a portfolio-fit level (categorical comparison)."""
    if not fit:
        return 0
    try:
        return FIT_ORDER.index((fit or "").upper())
    except ValueError:
        return 0


def _dedupe(reasons: list[str]) -> tuple[str, ...]:
    return tuple(dict.fromkeys(reasons))


# ---------------------------------------------------------------------------
# Decision gates
# ---------------------------------------------------------------------------
def decide_holding(
    eligibility: EligibilityResult,
    *,
    current_weight: float,
    risk_contribution: float | None,
    equal_risk: float | None,
    target_min: float | None = None,
    target_mid: float | None = None,
    target_max: float | None = None,
    hard_cap: float = 0.20,
    current_fit: str = "UNAVAILABLE",
    technical: bool | None = None,
) -> AllocationDecision:
    """Advisory decision for a current holding — explicit gates, no score.

    A. hard reject   -> SELL
    B. LOW_QUALITY   -> REDUCE (fundamental deterioration)
    C. excessive risk contribution -> REDUCE (canonical thresholds)
    D. otherwise     -> HOLD (default; no composite score required)
    """
    weight = max(0.0, float(current_weight))
    rc = risk_contribution if risk_contribution is not None else None
    reasons = list(eligibility.reason_codes)
    bands = {
        "business_quality_tier": eligibility.quality_tier,
        "valuation_safety_pp": eligibility.valuation_safety,
        "portfolio_fit": current_fit,
        "technical_confirmation": technical,
    }

    # A. Hard reject / thesis break -> SELL.
    if eligibility.hard_rejects:
        reasons.append(HARD_REJECT)
        return AllocationDecision(
            symbol=eligibility.symbol, action="SELL", kind="HOLDING",
            current_weight=weight, target_min=0.0, target_mid=0.0, target_max=0.0,
            confidence="HIGH", reason_codes=_dedupe(reasons), bands=bands,
        )

    # B. Fundamental deterioration -> REDUCE.
    if eligibility.status == "INELIGIBLE":
        reasons.append(QUALITY_DETERIORATING)
        return AllocationDecision(
            symbol=eligibility.symbol, action="REDUCE", kind="HOLDING",
            current_weight=weight, target_min=0.0, target_mid=0.0,
            target_max=min(weight, 0.05), confidence="MEDIUM",
            reason_codes=_dedupe(reasons), bands=bands,
        )

    # C. Excessive risk contribution (canonical QPort health convention) -> REDUCE.
    #    Nominal weight > hard_cap alone is informational (POSITION_CONCENTRATED)
    #    and never forces a trade by itself.
    risk_breach = bool(
        rc is not None and equal_risk is not None and equal_risk > 0
        and rc > max(RISK_CONTRIBUTION_ABSOLUTE_BREACH, RISK_CONTRIBUTION_BREACH_MULTIPLIER * equal_risk)
    )
    if weight >= POSITION_CONCENTRATED_WEIGHT:
        reasons.append(POSITION_CONCENTRATED)
    if risk_breach:
        reasons.append(RISK_CONTRIBUTION_HIGH)
        reduce_target = max(0.0, min(weight, 0.25))
        return AllocationDecision(
            symbol=eligibility.symbol, action="REDUCE", kind="HOLDING",
            current_weight=weight, target_min=0.0, target_mid=reduce_target,
            target_max=reduce_target, confidence="MEDIUM",
            reason_codes=_dedupe(reasons), bands=bands,
        )

    # D. Normal good holding -> HOLD (default). No score threshold required.
    if eligibility.quality_tier in ("EXCEPTIONAL", "HIGH_QUALITY"):
        reasons.append(QUALITY_STRONG)
    if eligibility.status == "INVESTABLE":
        reasons.append(NO_SUPERIOR_REPLACEMENT)
    if technical is False:
        reasons.append(TECHNICAL_DETERIORATION)
    elif technical is True:
        reasons.append(TECHNICAL_CONFIRMATION)
    return AllocationDecision(
        symbol=eligibility.symbol, action="HOLD", kind="HOLDING",
        current_weight=weight, target_min=target_min,
        target_mid=target_mid, target_max=target_max,
        confidence="MEDIUM", reason_codes=_dedupe(reasons), bands=bands,
    )


def decide_candidate(
    candidate: CandidateOpportunity,
    *,
    cash_weight: float,
    rotation_funded: bool = False,
    technical: bool | None = None,
    min_valuation_safety: float = MIN_VALUATION_SAFETY,
) -> AllocationDecision:
    """Advisory decision for a research candidate — explicit gates, no score.

    BUY_MORE only if ALL gates pass:
      - eligibility == INVESTABLE (no hard reject)
      - portfolio fit is GOOD or MODERATE (never WEAK / UNAVAILABLE)
      - valuation safety data available and meets the configured V1 rule
      - cash available OR the position is funded by a valid rotation
    Technical confirmation may only downgrade BUY_MORE -> WATCH (secondary).
    """
    eligibility = candidate.eligibility
    reasons = list(candidate.reason_codes)
    fit = candidate.portfolio_fit
    sizing = candidate.sizing
    fit_level = fit.fit if fit else "UNAVAILABLE"
    bands = {
        "business_quality_tier": eligibility.quality_tier,
        "valuation_safety_pp": eligibility.valuation_safety,
        "portfolio_fit": fit_level,
        "technical_confirmation": technical,
    }

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
        reasons.append(PORTFOLIO_FIT_WEAK)
        reasons.extend(code for code in (CORRELATION_HIGH, RISK_CONTRIBUTION_HIGH) if code not in reasons)
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

    # Valuation data must be available and meet the configured V1 rule.
    if eligibility.valuation_safety is None:
        reasons.extend((VALUATION_SAFETY_INSUFFICIENT, DATA_INSUFFICIENT))
        return AllocationDecision(
            symbol=eligibility.symbol, action="WATCH", kind="CANDIDATE",
            current_weight=0.0, target_min=sizing.target_min, target_mid=sizing.target_mid,
            target_max=sizing.target_max, confidence="LOW",
            reason_codes=_dedupe(reasons), bands=bands,
        )
    if eligibility.valuation_safety < min_valuation_safety:
        reasons.append(VALUATION_SAFETY_INSUFFICIENT)
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

    # Technical is secondary evidence only: positive adds confirmation, negative
    # downgrades BUY_MORE to WATCH. It can never override eligibility.
    if technical is False:
        reasons.append(TECHNICAL_DETERIORATION)
        return AllocationDecision(
            symbol=eligibility.symbol, action="WATCH", kind="CANDIDATE",
            current_weight=0.0, target_min=sizing.target_min, target_mid=sizing.target_mid,
            target_max=sizing.target_max, confidence="MEDIUM",
            reason_codes=_dedupe(reasons), bands=bands,
        )
    if technical is True:
        reasons.append(TECHNICAL_CONFIRMATION)

    confidence = "HIGH" if fit_level == "GOOD" and eligibility.valuation_confidence in ("HIGH", None) else "MEDIUM"
    return AllocationDecision(
        symbol=eligibility.symbol, action="BUY_MORE", kind="CANDIDATE",
        current_weight=0.0, target_min=sizing.target_min, target_mid=sizing.target_mid,
        target_max=sizing.target_max, confidence=confidence,
        reason_codes=_dedupe(reasons), bands=bands,
    )


# ---------------------------------------------------------------------------
# Rotation gates (explicit, no composite score)
# ---------------------------------------------------------------------------
def holding_is_rotation_eligible(eligibility: EligibilityResult) -> bool:
    """Explicit weakness rules that make a holding a rotation candidate.

    NOT a composite score. A holding qualifies only when at least one explicit
    rule applies:
      - quality tier is WATCH or LOW_QUALITY (fundamentally weak)
      - eligibility is not INVESTABLE (data insufficient / watchlist)
      - no public valuation (valuation_safety is None)
    Hard-reject and LOW_QUALITY holdings are already handled by gates A/B and
    are intentionally excluded here (they are SELL/REDUCE regardless).
    """
    if eligibility.hard_rejects:
        return False
    if eligibility.status == "INELIGIBLE":
        return False
    if eligibility.quality_tier in ("WATCH", "LOW_QUALITY"):
        return True
    if eligibility.status != "INVESTABLE":
        return True
    if eligibility.valuation_safety is None:
        return True
    return False


def rotation_gates(
    holding_eligibility: EligibilityResult,
    *,
    holding_fit: str,
    candidate: CandidateOpportunity,
    replacement_delta: float = VALUATION_SAFETY_REPLACEMENT_DELTA,
    min_valuation_safety: float = MIN_VALUATION_SAFETY,
) -> tuple[bool, tuple[str, ...]]:
    """Explicit rotation gates. Rotation is proposed only if ALL pass.

    Gates:
      1. holding is genuinely weaker (explicit rules, not a score)
      2. candidate is INVESTABLE
      3. candidate quality tier is not worse than holding (ordinal)
      4. candidate valuation safety is materially better than the holding
         (delta >= ``replacement_delta``), or, when the holding has no public
         valuation, meets the configured minimum
      5. candidate portfolio fit is not WEAK / UNAVAILABLE
    The delta threshold doubles as the transaction-cost / hysteresis buffer.
    Returns (passed, reason_codes).
    """
    holding = holding_eligibility
    cand = candidate.eligibility

    if not holding_is_rotation_eligible(holding):
        return False, ()

    if cand.status != "INVESTABLE" or cand.hard_rejects:
        return False, ()

    # Ordinal quality comparison: candidate must not be worse.
    if quality_tier_rank(cand.quality_tier) < quality_tier_rank(holding.quality_tier):
        return False, ()

    # Valuation safety: data must exist and be materially better.
    if cand.valuation_safety is None:
        return False, ()
    if holding.valuation_safety is not None:
        delta = cand.valuation_safety - holding.valuation_safety
        if delta < replacement_delta:
            return False, ()
    else:
        if cand.valuation_safety < min_valuation_safety:
            return False, ()

    # Portfolio fit must not be WEAK / UNAVAILABLE.
    cand_fit = candidate.portfolio_fit.fit if candidate.portfolio_fit else "UNAVAILABLE"
    if fit_rank(cand_fit) < fit_rank("MODERATE"):
        return False, ()

    reasons = [SUPERIOR_REPLACEMENT_AVAILABLE, VALUATION_SAFETY_IMPROVES]
    if fit_rank(cand_fit) > fit_rank(holding_fit or "UNAVAILABLE"):
        reasons.append(PORTFOLIO_FIT_IMPROVES)
    return True, tuple(dict.fromkeys(reasons))