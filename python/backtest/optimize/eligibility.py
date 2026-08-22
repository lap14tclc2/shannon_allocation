"""Live-deployment eligibility gates for optimizer candidates.

These gates are intentionally OUTSIDE ERC, Shannon, risk targeting and NSGA-II.
They do not change how a candidate is generated or scored during research. They
only answer a later question: is this research candidate stable enough to be
considered for live deployment?
"""

from __future__ import annotations


def assess_live_eligibility(
    train_metrics: dict | None,
    validation_metrics: dict | None,
    recent_metrics: dict | None,
    *,
    min_train_twr_pct: float = 0.0,
    min_validation_p10_twr_pct: float = 0.0,
    min_recent_twr_pct: float = 0.0,
) -> tuple[bool, list[str]]:
    reasons: list[str] = []
    train = train_metrics or {}
    validation = validation_metrics or {}
    recent = recent_metrics or {}

    if not validation:
        reasons.append("validation_failed")

    train_twr = train.get("net_twr_annualized_pct")
    if train_twr is None or train_twr < min_train_twr_pct:
        reasons.append(
            f"train_twr_below_{min_train_twr_pct:g}%"
        )

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

    return not reasons, reasons
