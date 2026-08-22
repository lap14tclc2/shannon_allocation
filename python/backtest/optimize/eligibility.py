"""Live-deployment eligibility gates for optimizer candidates.

These gates are intentionally OUTSIDE ERC, Shannon, risk targeting and NSGA-II.
They do not change how a candidate is generated or scored during research. They
only answer a later question: is this research candidate stable enough to be
considered for live deployment?

The policy deliberately avoids a hard required CAGR. A hard historical return
target encourages the search to fit noise. Instead, live promotion requires
positive pre-holdout growth plus a minimum return-to-drawdown quality across
TRAIN, rolling OOS validation and the recent pre-holdout regime.
"""

from __future__ import annotations


# Production defaults. These are intentionally modest: they reject combinations
# that accept large drawdowns for tiny returns without forcing the optimizer to
# manufacture a 20%+ historical CAGR.
DEFAULT_MIN_TRAIN_CALMAR = 0.35
DEFAULT_MIN_VALIDATION_RETURN_TO_DRAWDOWN = 0.50
DEFAULT_MIN_RECENT_CALMAR = 0.35


def _return_to_drawdown(
    return_pct: float | None,
    drawdown_pct: float | None,
    calmar: float | None = None,
) -> float | None:
    """Return a positive return/drawdown ratio when enough data exists.

    Prefer the simulator's Calmar value when available. For aggregate validation
    windows there is no single Calmar metric, so median OOS return divided by the
    absolute worst OOS drawdown is used as a deliberately conservative proxy.
    """
    if calmar is not None:
        try:
            return float(calmar)
        except (TypeError, ValueError):
            pass
    if return_pct is None or drawdown_pct is None:
        return None
    try:
        dd = abs(float(drawdown_pct))
        if dd <= 1e-12:
            return None
        return float(return_pct) / dd
    except (TypeError, ValueError):
        return None


def assess_live_eligibility(
    train_metrics: dict | None,
    validation_metrics: dict | None,
    recent_metrics: dict | None,
    *,
    min_train_twr_pct: float = 0.0,
    min_validation_p10_twr_pct: float = 0.0,
    min_recent_twr_pct: float = 0.0,
    min_train_calmar: float = DEFAULT_MIN_TRAIN_CALMAR,
    min_validation_return_to_drawdown: float = DEFAULT_MIN_VALIDATION_RETURN_TO_DRAWDOWN,
    min_recent_calmar: float = DEFAULT_MIN_RECENT_CALMAR,
) -> tuple[bool, list[str]]:
    reasons: list[str] = []
    train = train_metrics or {}
    validation = validation_metrics or {}
    recent = recent_metrics or {}

    if not validation:
        reasons.append("validation_failed")

    train_twr = train.get("net_twr_annualized_pct")
    if train_twr is None or train_twr < min_train_twr_pct:
        reasons.append(f"train_twr_below_{min_train_twr_pct:g}%")

    p10 = validation.get("p10_net_twr")
    if p10 is None or p10 < min_validation_p10_twr_pct:
        reasons.append(
            f"validation_p10_below_{min_validation_p10_twr_pct:g}%"
        )

    recent_twr = recent.get("net_twr_annualized_pct")
    if recent_twr is None or recent.get("error") or recent_twr < min_recent_twr_pct:
        reasons.append(
            f"recent_validation_twr_below_{min_recent_twr_pct:g}%"
        )

    # Risk/reward gates. Missing ratio data is not treated as an automatic failure
    # so older experiment fixtures remain readable; real simulator metrics always
    # provide the required MDD/Calmar fields.
    train_ratio = _return_to_drawdown(
        train_twr,
        train.get("max_drawdown_pct"),
        train.get("calmar"),
    )
    if train_ratio is not None and train_ratio < min_train_calmar:
        reasons.append(f"train_calmar_below_{min_train_calmar:g}")

    validation_ratio = _return_to_drawdown(
        validation.get("median_net_twr"),
        validation.get("worst_mdd"),
    )
    if (
        validation_ratio is not None
        and validation_ratio < min_validation_return_to_drawdown
    ):
        reasons.append(
            "validation_return_to_drawdown_below_"
            f"{min_validation_return_to_drawdown:g}"
        )

    recent_ratio = _return_to_drawdown(
        recent_twr,
        recent.get("max_drawdown_pct"),
        recent.get("calmar"),
    )
    if recent_ratio is not None and recent_ratio < min_recent_calmar:
        reasons.append(f"recent_calmar_below_{min_recent_calmar:g}")

    return not reasons, reasons
