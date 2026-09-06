"""Buffett Core eligibility adapter.

Translates canonical value-engine outputs into a clean portfolio-eligibility
verdict without double-counting Quality and Valuation.

Core derived field:

    valuation_safety = actual_mos_pct - required_mos_pct

Rules:
- any hard reject -> INELIGIBLE (overrides momentum/technical strength);
- LOW_QUALITY tier -> INELIGIBLE;
- WATCH tier or missing public valuation -> WATCHLIST (never investable);
- quality and valuation are retained separately;
- low valuation confidence can never become a high-confidence BUY.
"""
from __future__ import annotations

from .models import EligibilityResult
from .reason_codes import (
    DATA_INSUFFICIENT,
    HARD_REJECT,
    QUALITY_DETERIORATING,
    QUALITY_STRONG,
    VALUATION_ATTRACTIVE,
    VALUATION_CONFIDENCE_LOW,
    VALUATION_EXPENSIVE,
    VALUATION_FAIR,
    VALUATION_SAFETY_NEGATIVE,
    VALUATION_SAFETY_POSITIVE,
)

_INVESTABLE_TIERS = frozenset({"EXCEPTIONAL", "HIGH_QUALITY", "INVESTABLE"})
_STRONG_QUALITY_TIERS = frozenset({"EXCEPTIONAL", "HIGH_QUALITY"})
_ATTRACTIVE_STATUSES = frozenset({
    "HIGH_CONVICTION_VALUE", "ATTRACTIVE", "DEEP_VALUE", "UNDERVALUED",
})
_FAIR_STATUSES = frozenset({"FAIRLY_VALUED", "FAIR_VALUE", "WATCH"})
_EXPENSIVE_STATUSES = frozenset({"OVERVALUED", "GROWTH_PRICED_IN"})


def _number(value) -> float | None:
    if value is None or value == "":
        return None
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        return None
    return parsed if parsed == parsed else None


def signal_from_screener_item(item: dict) -> dict:
    """Build a normalized valuation signal from a canonical screener item.

    Screener items already mirror the canonical ValuationReport (public IV/MOS/
    required MOS/quality tier/hard rejects), so reusing them here keeps one
    source of truth for valuation.
    """
    return {
        "symbol": str(item.get("symbol") or "").upper(),
        "quality_tier": item.get("tier") or item.get("quality_tier"),
        "quality_score": item.get("total_score") or item.get("quality_score"),
        "hard_rejects": list(item.get("hard_rejects") or []),
        "valuation_status": item.get("valuation_status"),
        "actual_mos_pct": _number(item.get("margin_of_safety") or item.get("actual_mos_pct")),
        "required_mos_pct": _number(item.get("required_mos") or item.get("required_mos_pct")),
        "valuation_confidence": item.get("valuation_confidence"),
        "data_status": item.get("data_status"),
        "model_status": item.get("model_status"),
    }


def _valuation_reason_codes(valuation_status: str | None) -> list[str]:
    status = (valuation_status or "").upper()
    if status in _ATTRACTIVE_STATUSES:
        return [VALUATION_ATTRACTIVE]
    if status in _FAIR_STATUSES:
        return [VALUATION_FAIR]
    if status in _EXPENSIVE_STATUSES:
        return [VALUATION_EXPENSIVE]
    return []


def eligibility_from_signal(signal: dict) -> EligibilityResult:
    """Deterministically map a value-engine signal to an EligibilityResult."""
    symbol = str(signal.get("symbol") or "?").upper()
    hard_rejects = tuple(str(code).upper() for code in (signal.get("hard_rejects") or []) if code)
    quality_tier = str(signal.get("quality_tier") or "").upper() or None
    quality_score = _number(signal.get("quality_score"))
    valuation_status = signal.get("valuation_status")
    actual_mos = _number(signal.get("actual_mos_pct"))
    required_mos = _number(signal.get("required_mos_pct"))
    confidence = str(signal.get("valuation_confidence") or "").upper() or None

    valuation_safety = (
        round(actual_mos - required_mos, 4)
        if actual_mos is not None and required_mos is not None
        else None
    )

    # 1. Hard rejects always override momentum/technical strength.
    if hard_rejects:
        reasons = [HARD_REJECT]
        if DATA_INSUFFICIENT in hard_rejects:
            reasons.append(DATA_INSUFFICIENT)
        return EligibilityResult(
            symbol=symbol,
            status="INELIGIBLE",
            hard_rejects=hard_rejects,
            quality_tier=quality_tier,
            quality_score=int(quality_score) if quality_score is not None else None,
            valuation_status=valuation_status,
            valuation_confidence=confidence,
            valuation_safety=valuation_safety,
            actual_mos_pct=actual_mos,
            required_mos_pct=required_mos,
            reason_codes=tuple(dict.fromkeys(reasons)),
            data_quality="HARD_REJECT",
        )

    # 2. LOW_QUALITY is never investable, regardless of MOS.
    if quality_tier == "LOW_QUALITY":
        return EligibilityResult(
            symbol=symbol,
            status="INELIGIBLE",
            hard_rejects=(),
            quality_tier=quality_tier,
            quality_score=int(quality_score) if quality_score is not None else None,
            valuation_status=valuation_status,
            valuation_confidence=confidence,
            valuation_safety=valuation_safety,
            actual_mos_pct=actual_mos,
            required_mos_pct=required_mos,
            reason_codes=(QUALITY_DETERIORATING,),
            data_quality="LOW_QUALITY",
        )

    # 3. Missing quality/data -> cannot conclude investable.
    if quality_tier is None or quality_tier not in _INVESTABLE_TIERS:
        reasons = [DATA_INSUFFICIENT]
        if quality_tier == "WATCH":
            reasons = [DATA_INSUFFICIENT]
        return EligibilityResult(
            symbol=symbol,
            status="WATCHLIST",
            hard_rejects=(),
            quality_tier=quality_tier,
            quality_score=int(quality_score) if quality_score is not None else None,
            valuation_status=valuation_status,
            valuation_confidence=confidence,
            valuation_safety=valuation_safety,
            actual_mos_pct=actual_mos,
            required_mos_pct=required_mos,
            reason_codes=tuple(dict.fromkeys(reasons)),
            data_quality="DATA_INSUFFICIENT" if quality_tier is None else "WATCH",
        )

    # 4. Investable tier requires a published valuation (public MOS).
    if actual_mos is None or required_mos is None:
        reasons = [VALUATION_CONFIDENCE_LOW, DATA_INSUFFICIENT]
        return EligibilityResult(
            symbol=symbol,
            status="WATCHLIST",
            hard_rejects=(),
            quality_tier=quality_tier,
            quality_score=int(quality_score) if quality_score is not None else None,
            valuation_status=valuation_status,
            valuation_confidence=confidence,
            valuation_safety=None,
            actual_mos_pct=actual_mos,
            required_mos_pct=required_mos,
            reason_codes=tuple(dict.fromkeys(reasons)),
            data_quality="NO_PUBLIC_VALUATION",
        )

    reasons: list[str] = []
    if quality_tier in _STRONG_QUALITY_TIERS:
        reasons.append(QUALITY_STRONG)
    reasons.extend(_valuation_reason_codes(valuation_status))
    if valuation_safety is not None and valuation_safety > 0:
        reasons.append(VALUATION_SAFETY_POSITIVE)
    elif valuation_safety is not None and valuation_safety < 0:
        reasons.append(VALUATION_SAFETY_NEGATIVE)
    if confidence == "LOW":
        reasons.append(VALUATION_CONFIDENCE_LOW)

    return EligibilityResult(
        symbol=symbol,
        status="INVESTABLE",
        hard_rejects=(),
        quality_tier=quality_tier,
        quality_score=int(quality_score) if quality_score is not None else None,
        valuation_status=valuation_status,
        valuation_confidence=confidence,
        valuation_safety=valuation_safety,
        actual_mos_pct=actual_mos,
        required_mos_pct=required_mos,
        reason_codes=tuple(dict.fromkeys(reasons)),
        data_quality="OK",
    )