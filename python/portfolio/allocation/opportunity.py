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
    BALANCE_SHEET_REVIEW,
    CASH_PREFERRED,
    CONCENTRATED_THESIS_RISK,
    CORRELATION_HIGH,
    CYCLICAL_EARNINGS,
    DATA_INSUFFICIENT,
    HARD_REJECT,
    NO_SUPERIOR_REPLACEMENT,
    PERMANENT_LOSS_DATA_INSUFFICIENT,
    PORTFOLIO_FIT_IMPROVES,
    PORTFOLIO_FIT_WEAK,
    POSITION_CONCENTRATED,
    QUALITY_DETERIORATING,
    QUALITY_STRONG,
    REVIEW_REQUIRED,
    RISK_CONTRIBUTION_HIGH,
    SUPERIOR_REPLACEMENT_AVAILABLE,
    TECHNICAL_CONFIRMATION,
    TECHNICAL_DETERIORATION,
    THESIS_BROKEN,
    VALUATION_SAFETY_IMPROVES,
    VALUATION_SAFETY_INSUFFICIENT,
    VALUATION_SAFETY_NEGATIVE,
    VALUATION_SAFETY_POSITIVE,
    VOLATILITY_HIGH,
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


def _reduce_target(weight: float, cap: float = 0.05) -> tuple[float, float, float]:
    """Compute a positive partial reduction target (0 < target_mid < weight)."""
    w = max(0.0, float(weight))
    if w <= 0.0:
        return 0.0, 0.0, 0.0
    mid = round(max(0.005, min(w * 0.5, cap)), 6)
    if mid >= w:
        mid = round(w * 0.5, 6)
    if mid <= 0.0:
        mid = round(w * 0.5, 6)
    low = round(mid * 0.5, 6)
    high = max(mid, round(mid * 1.25, 6))
    return low, mid, high


# ---------------------------------------------------------------------------
# Decision gates
# ---------------------------------------------------------------------------
def _build_guidance(
    sizing: Any = None,
    target_min: float | None = None,
    target_mid: float | None = None,
    target_max: float | None = None,
) -> dict[str, Any]:
    if sizing is not None:
        return {
            "tier": getattr(sizing, "conviction_tier", "STARTER"),
            "min_weight": getattr(sizing, "target_min", 0.03),
            "mid_weight": getattr(sizing, "target_mid", 0.04),
            "max_weight": getattr(sizing, "target_max", 0.05),
        }
    return {
        "tier": "STARTER",
        "min_weight": target_min if target_min is not None else 0.03,
        "mid_weight": target_mid if target_mid is not None else 0.04,
        "max_weight": target_max if target_max is not None else 0.05,
    }


def decide_holding(
    eligibility: EligibilityResult,
    *,
    current_weight: float,
    risk_contribution: float | None,
    equal_risk: float | None,
    sizing: Any = None,
    target_min: float | None = None,
    target_mid: float | None = None,
    target_max: float | None = None,
    hard_cap: float = 0.20,
    current_fit: str = "UNAVAILABLE",
    technical: bool | None = None,
    risk_actionable: bool = True,
    permanent_loss_context: dict[str, Any] | None = None,
) -> AllocationDecision:
    """Advisory decision for a current holding — Buffett-first precedence.

    Hierarchy:
    1. THESIS STATUS / DESTRUCTIVE HARD REJECT -> SELL (target 0%)
    2. CONFIRMED FUNDAMENTAL DETERIORATION / SEVERE PERMANENT LOSS -> REDUCE (target > 0)
    3. REVIEW SIGNALS (Concentration, RC breach, UNKNOWN risk data, MOS shortfall) -> HOLD + REVIEW_REQUIRED
    4. NORMAL INTACT HOLDING -> HOLD (default, target = current_weight)

    Market risk metrics (volatility, correlation, risk contribution) refine sizing
    and review priority. They CANNOT trigger standalone REDUCE actions.
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
    guidance = _build_guidance(sizing, target_min, target_mid, target_max)

    perm_loss = permanent_loss_context or {}
    perm_severity = perm_loss.get("severity") or "UNKNOWN"
    perm_evidence_strength = perm_loss.get("evidence_strength") or "INSUFFICIENT"
    perm_thesis_status = perm_loss.get("thesis_status") or "UNKNOWN"
    perm_balance_sheet = perm_loss.get("balance_sheet") or "UNKNOWN"
    perm_earnings = perm_loss.get("earnings_durability") or "UNKNOWN"

    is_concentrated = (weight >= POSITION_CONCENTRATED_WEIGHT) or (weight >= hard_cap)
    risk_breach = bool(
        risk_actionable
        and rc is not None and equal_risk is not None and equal_risk > 0
        and rc > max(RISK_CONTRIBUTION_ABSOLUTE_BREACH, RISK_CONTRIBUTION_BREACH_MULTIPLIER * equal_risk)
    )

    if is_concentrated:
        reasons.extend([POSITION_CONCENTRATED, CONCENTRATED_THESIS_RISK])
    if risk_breach:
        reasons.append(RISK_CONTRIBUTION_HIGH)
    if perm_earnings == "CYCLICAL":
        reasons.append(CYCLICAL_EARNINGS)
    if perm_balance_sheet in ("HIGH_RISK", "ATTENTION"):
        reasons.append(BALANCE_SHEET_REVIEW)
    if perm_severity == "UNKNOWN" or eligibility.data_quality in ("DATA_INSUFFICIENT", "WATCH"):
        reasons.append(PERMANENT_LOSS_DATA_INSUFFICIENT)

    # Gate 1: Destructive hard reject / thesis break -> SELL (target 0%).
    is_thesis_broken = (
        bool(eligibility.hard_rejects)
        or perm_thesis_status == "BROKEN"
        or (THESIS_BROKEN in eligibility.reason_codes)
    )
    if is_thesis_broken:
        reasons.extend([HARD_REJECT, THESIS_BROKEN])
        return AllocationDecision(
            symbol=eligibility.symbol, action="SELL", kind="HOLDING",
            current_weight=weight, post_action_target_weight=0.0,
            target_min=0.0, target_mid=0.0, target_max=0.0,
            confidence="HIGH", reason_codes=_dedupe(reasons), bands=bands,
            new_position_guidance=guidance,
        )

    # Gate 2: Confirmed fundamental deterioration or severe confirmed permanent loss -> REDUCE (target > 0).
    is_deteriorating_quality = (
        eligibility.quality_tier == "LOW_QUALITY"
        or (eligibility.status == "INELIGIBLE" and not eligibility.hard_rejects)
        or (QUALITY_DETERIORATING in eligibility.reason_codes)
    )
    is_confirmed_severe_permanent_loss = (
        (perm_severity == "HIGH" and perm_evidence_strength == "CONFIRMED")
        or (perm_severity == "ELEVATED" and perm_evidence_strength == "CONFIRMED" and perm_thesis_status in ("WATCH", "DETERIORATING"))
    )
    is_concentrated_deteriorating = (
        is_concentrated and (
            perm_thesis_status in ("DETERIORATING", "BROKEN")
            or (QUALITY_DETERIORATING in eligibility.reason_codes)
            or eligibility.quality_tier == "LOW_QUALITY"
        )
    )
    is_hard_cap_governance_breach = (
        is_concentrated and weight > (hard_cap * 1.5) and risk_breach
        and (eligibility.valuation_safety is not None and eligibility.valuation_safety < -10.0)
    )

    if is_deteriorating_quality or is_confirmed_severe_permanent_loss or is_concentrated_deteriorating or is_hard_cap_governance_breach:
        if is_deteriorating_quality:
            reasons.append(QUALITY_DETERIORATING)
        low, mid, high = _reduce_target(weight, cap=min(0.15, hard_cap * 0.75))
        return AllocationDecision(
            symbol=eligibility.symbol, action="REDUCE", kind="HOLDING",
            current_weight=weight, post_action_target_weight=mid,
            target_min=low, target_mid=mid, target_max=high, confidence="MEDIUM",
            reason_codes=_dedupe(reasons), bands=bands,
            new_position_guidance=guidance,
        )

    # Gate 3: Review Signals (Concentration, RC breach, indicative permanent loss, UNKNOWN risk data) -> HOLD + REVIEW_REQUIRED.
    requires_review = (
        is_concentrated
        or risk_breach
        or (perm_severity in ("ELEVATED", "HIGH"))
        or (eligibility.status == "WATCHLIST")
        or (DATA_INSUFFICIENT in eligibility.reason_codes)
        or (eligibility.valuation_confidence == "LOW")
        or (eligibility.valuation_safety is not None and eligibility.valuation_safety < 0.0)
        or (not risk_actionable)
    )
    if requires_review:
        reasons.append(REVIEW_REQUIRED)
        if eligibility.valuation_safety is not None and eligibility.valuation_safety > 0.0:
            reasons.append(VALUATION_SAFETY_POSITIVE)
        elif eligibility.valuation_safety is not None and eligibility.valuation_safety < 0.0:
            reasons.append(VALUATION_SAFETY_NEGATIVE)
        if NO_SUPERIOR_REPLACEMENT not in reasons:
            reasons.append(NO_SUPERIOR_REPLACEMENT)

        return AllocationDecision(
            symbol=eligibility.symbol, action="HOLD", kind="HOLDING",
            current_weight=weight, post_action_target_weight=weight,
            target_min=None, target_mid=weight, target_max=None,
            confidence="MEDIUM" if (eligibility.valuation_confidence or "MEDIUM") != "LOW" else "LOW",
            reason_codes=_dedupe(reasons), bands=bands,
            new_position_guidance=guidance,
        )

    # Gate 4: Normal intact holding -> HOLD (default).
    if eligibility.quality_tier in ("EXCEPTIONAL", "HIGH_QUALITY"):
        reasons.append(QUALITY_STRONG)
    if eligibility.status == "INVESTABLE":
        reasons.append(NO_SUPERIOR_REPLACEMENT)
    if eligibility.valuation_safety is not None and eligibility.valuation_safety >= 0.0:
        reasons.append(VALUATION_SAFETY_POSITIVE)
    if technical is False:
        reasons.append(TECHNICAL_DETERIORATION)
    elif technical is True:
        reasons.append(TECHNICAL_CONFIRMATION)

    return AllocationDecision(
        symbol=eligibility.symbol, action="HOLD", kind="HOLDING",
        current_weight=weight, post_action_target_weight=weight,
        target_min=None, target_mid=weight, target_max=None,
        confidence=eligibility.valuation_confidence or "MEDIUM",
        reason_codes=_dedupe(reasons), bands=bands,
        new_position_guidance=guidance,
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
    guidance = _build_guidance(sizing)

    if eligibility.status != "INVESTABLE":
        reasons.append(DATA_INSUFFICIENT)
        return AllocationDecision(
            symbol=eligibility.symbol, action="WATCH", kind="CANDIDATE",
            current_weight=0.0, post_action_target_weight=None,
            target_min=sizing.target_min if sizing else None,
            target_mid=sizing.target_mid if sizing else None,
            target_max=sizing.target_max if sizing else None,
            confidence="LOW", reason_codes=_dedupe(reasons), bands=bands,
            new_position_guidance=guidance,
        )

    if fit is None or fit_level == "UNAVAILABLE":
        reasons.append(DATA_INSUFFICIENT)
        return AllocationDecision(
            symbol=eligibility.symbol, action="WATCH", kind="CANDIDATE",
            current_weight=0.0, post_action_target_weight=None,
            target_min=sizing.target_min if sizing else None,
            target_mid=sizing.target_mid if sizing else None,
            target_max=sizing.target_max if sizing else None,
            confidence="LOW", reason_codes=_dedupe(reasons), bands=bands,
            new_position_guidance=guidance,
        )

    if fit_level == "WEAK":
        reasons.append(PORTFOLIO_FIT_WEAK)
        reasons.extend(code for code in (CORRELATION_HIGH, RISK_CONTRIBUTION_HIGH) if code not in reasons)
        return AllocationDecision(
            symbol=eligibility.symbol, action="WATCH", kind="CANDIDATE",
            current_weight=0.0, post_action_target_weight=None,
            target_min=sizing.target_min if sizing else None,
            target_mid=sizing.target_mid if sizing else None,
            target_max=sizing.target_max if sizing else None,
            confidence="LOW", reason_codes=_dedupe(reasons), bands=bands,
            new_position_guidance=guidance,
        )

    if sizing is None or sizing.target_mid <= 0:
        reasons.append(DATA_INSUFFICIENT)
        return AllocationDecision(
            symbol=eligibility.symbol, action="WATCH", kind="CANDIDATE",
            current_weight=0.0, post_action_target_weight=None,
            target_min=None, target_mid=None, target_max=None,
            confidence="LOW", reason_codes=_dedupe(reasons), bands=bands,
            new_position_guidance=guidance,
        )

    # Valuation data must be available and meet the configured V1 rule.
    if eligibility.valuation_safety is None:
        reasons.extend((VALUATION_SAFETY_INSUFFICIENT, DATA_INSUFFICIENT))
        return AllocationDecision(
            symbol=eligibility.symbol, action="WATCH", kind="CANDIDATE",
            current_weight=0.0, post_action_target_weight=None,
            target_min=sizing.target_min, target_mid=sizing.target_mid,
            target_max=sizing.target_max, confidence="LOW",
            reason_codes=_dedupe(reasons), bands=bands,
            new_position_guidance=guidance,
        )
    if eligibility.valuation_safety < min_valuation_safety:
        reasons.append(VALUATION_SAFETY_INSUFFICIENT)
        return AllocationDecision(
            symbol=eligibility.symbol, action="WATCH", kind="CANDIDATE",
            current_weight=0.0, post_action_target_weight=None,
            target_min=sizing.target_min, target_mid=sizing.target_mid,
            target_max=sizing.target_max, confidence="LOW",
            reason_codes=_dedupe(reasons), bands=bands,
            new_position_guidance=guidance,
        )

    # Cash must cover at least the starter size (unless rotation funds it).
    if not rotation_funded and cash_weight is not None and cash_weight < sizing.target_min:
        reasons.append(CASH_PREFERRED)
        return AllocationDecision(
            symbol=eligibility.symbol, action="WATCH", kind="CANDIDATE",
            current_weight=0.0, post_action_target_weight=None,
            target_min=sizing.target_min, target_mid=sizing.target_mid,
            target_max=sizing.target_max, confidence="MEDIUM",
            reason_codes=_dedupe(reasons), bands=bands,
            new_position_guidance=guidance,
        )

    # Technical is secondary evidence only: positive adds confirmation, negative
    # downgrades BUY_MORE to WATCH. It can never override eligibility.
    if technical is False:
        reasons.append(TECHNICAL_DETERIORATION)
        return AllocationDecision(
            symbol=eligibility.symbol, action="WATCH", kind="CANDIDATE",
            current_weight=0.0, post_action_target_weight=None,
            target_min=sizing.target_min, target_mid=sizing.target_mid,
            target_max=sizing.target_max, confidence="MEDIUM",
            reason_codes=_dedupe(reasons), bands=bands,
            new_position_guidance=guidance,
        )
    if technical is True:
        reasons.append(TECHNICAL_CONFIRMATION)

    confidence = "HIGH" if fit_level == "GOOD" and eligibility.valuation_confidence in ("HIGH", None) else "MEDIUM"
    return AllocationDecision(
        symbol=eligibility.symbol, action="BUY_MORE", kind="CANDIDATE",
        current_weight=0.0, post_action_target_weight=sizing.target_mid,
        target_min=sizing.target_min, target_mid=sizing.target_mid,
        target_max=sizing.target_max, confidence=confidence,
        reason_codes=_dedupe(reasons), bands=bands,
        new_position_guidance=guidance,
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