"""Live-deployment eligibility and soft risk/reward quality for optimizer candidates.

Hard gates are reserved for genuinely dangerous evidence: missing validation,
negative OOS tail performance, or a materially negative recent pre-holdout
regime. TRAIN/Recent Calmar and validation return-to-drawdown are deliberately
SOFT quality inputs rather than cliffs. A candidate with Calmar 0.34 should not
be treated as categorically different from one at 0.36.

These rules remain outside ERC, Shannon, volatility targeting and the final
holdout. The final holdout may reject a frozen winner; it never selects one.
"""

from __future__ import annotations

import math


DEFAULT_REFERENCE_TRAIN_CALMAR = 0.35
DEFAULT_REFERENCE_VALIDATION_RETURN_TO_DRAWDOWN = 0.50
DEFAULT_REFERENCE_RECENT_CALMAR = 0.35
DEFAULT_MIN_RECENT_TWR_PCT = -5.0


def _return_to_drawdown(
    return_pct: float | None,
    drawdown_pct: float | None,
    calmar: float | None = None,
) -> float | None:
    """Return return/drawdown quality when enough data exists."""
    if calmar is not None:
        try:
            value = float(calmar)
            return value if math.isfinite(value) else None
        except (TypeError, ValueError):
            pass
    if return_pct is None or drawdown_pct is None:
        return None
    try:
        dd = abs(float(drawdown_pct))
        if dd <= 1e-12:
            return None
        value = float(return_pct) / dd
        return value if math.isfinite(value) else None
    except (TypeError, ValueError):
        return None


def _soft_component(value: float | None, reference: float) -> float:
    """Map a risk/reward ratio to a bounded 0..1 quality component."""
    if value is None or not math.isfinite(float(value)):
        return 0.0
    ref = max(1e-9, float(reference))
    x = max(0.0, float(value)) / ref
    return x / (1.0 + x)


def live_risk_reward_score(
    train_metrics: dict | None,
    validation_metrics: dict | None,
    recent_metrics: dict | None,
    *,
    reference_train_calmar: float = DEFAULT_REFERENCE_TRAIN_CALMAR,
    reference_validation_return_to_drawdown: float = DEFAULT_REFERENCE_VALIDATION_RETURN_TO_DRAWDOWN,
    reference_recent_calmar: float = DEFAULT_REFERENCE_RECENT_CALMAR,
) -> dict:
    """Return explainable soft quality diagnostics on a 0..100 scale."""
    train = train_metrics or {}
    validation = validation_metrics or {}
    recent = recent_metrics or {}

    train_ratio = _return_to_drawdown(
        train.get("net_twr_annualized_pct"),
        train.get("max_drawdown_pct"),
        train.get("calmar"),
    )
    validation_ratio = _return_to_drawdown(
        validation.get("median_net_twr"),
        validation.get("worst_mdd"),
    )
    recent_ratio = _return_to_drawdown(
        recent.get("net_twr_annualized_pct"),
        recent.get("max_drawdown_pct"),
        recent.get("calmar"),
    )

    train_q = _soft_component(train_ratio, reference_train_calmar)
    validation_q = _soft_component(
        validation_ratio, reference_validation_return_to_drawdown
    )
    recent_q = _soft_component(recent_ratio, reference_recent_calmar)

    overall = 100.0 * (0.20 * train_q + 0.45 * validation_q + 0.35 * recent_q)
    return {
        "overall": round(overall, 4),
        "train_calmar": train_ratio,
        "validation_return_to_drawdown": validation_ratio,
        "recent_calmar": recent_ratio,
        "components": {
            "train": round(train_q * 100.0, 4),
            "validation": round(validation_q * 100.0, 4),
            "recent": round(recent_q * 100.0, 4),
        },
        "references": {
            "train_calmar": reference_train_calmar,
            "validation_return_to_drawdown": reference_validation_return_to_drawdown,
            "recent_calmar": reference_recent_calmar,
        },
    }


def assess_live_eligibility(
    train_metrics: dict | None,
    validation_metrics: dict | None,
    recent_metrics: dict | None,
    *,
    min_train_twr_pct: float | None = None,
    min_validation_p10_twr_pct: float = 0.0,
    min_recent_twr_pct: float = DEFAULT_MIN_RECENT_TWR_PCT,
    **_legacy_soft_thresholds,
) -> tuple[bool, list[str]]:
    """Apply only hard pre-holdout deployment gates.

    A legacy value of ``0`` for TRAIN return now means "no TRAIN hard gate".
    Likewise the old zero recent threshold is migrated to the -5% catastrophic
    default. Positive explicit thresholds still work for callers that truly want
    them. Legacy Calmar keyword arguments are accepted and ignored.
    """
    reasons: list[str] = []
    train = train_metrics or {}
    validation = validation_metrics or {}
    recent = recent_metrics or {}

    if not validation:
        reasons.append("validation_failed")

    if min_train_twr_pct is not None and float(min_train_twr_pct) > 0.0:
        train_twr = train.get("net_twr_annualized_pct")
        if train_twr is None or train_twr < min_train_twr_pct:
            reasons.append(f"train_twr_below_{min_train_twr_pct:g}%")

    p10 = validation.get("p10_net_twr")
    if p10 is None or p10 < min_validation_p10_twr_pct:
        reasons.append(
            f"validation_p10_below_{min_validation_p10_twr_pct:g}%"
        )

    effective_recent_floor = (
        DEFAULT_MIN_RECENT_TWR_PCT
        if float(min_recent_twr_pct) == 0.0
        else float(min_recent_twr_pct)
    )
    recent_twr = recent.get("net_twr_annualized_pct")
    if recent_twr is None or recent.get("error") or recent_twr < effective_recent_floor:
        reasons.append(
            f"recent_validation_twr_below_{effective_recent_floor:g}%"
        )

    return not reasons, reasons
