"""Conservative position sizing bands (V1 governance defaults).

Thorp Overlay sizing — NOT Kelly. Reference governance defaults:

    starter         3-5%
    normal          7-12%
    high conviction 12-18%
    hard cap        configurable, default 20%

Final target conceptually follows:

    target_weight = min(conviction_weight, risk_cap)

ERC is a risk reference only, never a mandatory target allocation.
"""
from __future__ import annotations

from .eligibility import eligibility_from_signal, signal_from_screener_item
from .models import SizingResult
from .reason_codes import DATA_INSUFFICIENT, RISK_CONTRIBUTION_HIGH

DEFAULT_HARD_CAP = 0.20
MAX_HARD_CAP = 0.30

CONVICTION_BANDS: dict[str, tuple[float, float, float]] = {
    "STARTER": (0.03, 0.04, 0.05),
    "NORMAL": (0.07, 0.10, 0.12),
    "HIGH_CONVICTION": (0.12, 0.15, 0.18),
}

FIT_CAP_MULTIPLIER: dict[str, float] = {
    "GOOD": 1.0,       # full conviction band allowed
    "MODERATE": 0.6,   # cap to normal-ish
    "WEAK": 0.25,      # cap to starter-ish
    "UNAVAILABLE": 0.5,  # missing risk history degrades safely (never zero risk)
}


def _number(value) -> float | None:
    if value is None or value == "":
        return None
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        return None
    return parsed if parsed == parsed else None


def conviction_tier_for(signal: dict) -> str:
    """Derive the conviction tier from Quality + Valuation safety only.

    Portfolio fit is applied later as a risk cap (``min(conviction, risk_cap)``).
    """
    eligibility = eligibility_from_signal(signal)
    if eligibility.status != "INVESTABLE":
        return "STARTER"
    quality_tier = eligibility.quality_tier or ""
    safety = eligibility.valuation_safety
    if quality_tier in ("EXCEPTIONAL", "HIGH_QUALITY") and safety is not None and safety >= 0.0:
        return "HIGH_CONVICTION"
    if safety is not None and safety >= 0.0:
        return "NORMAL"
    return "STARTER"


def conviction_mid(tier: str) -> float:
    return CONVICTION_BANDS.get(tier, CONVICTION_BANDS["STARTER"])[1]


def bands_for_tier(tier: str) -> tuple[float, float, float]:
    return CONVICTION_BANDS.get(tier, CONVICTION_BANDS["STARTER"])


def risk_cap_for_fit(fit: str, hard_cap: float = DEFAULT_HARD_CAP) -> float:
    """Reduce the hard cap based on portfolio-fit evidence.

    A WEAK fit (high correlation / high risk contribution) or an UNAVAILABLE
    fit (missing risk history) reduces the allowed exposure. We never assume
    zero risk when history is missing.
    """
    multiplier = FIT_CAP_MULTIPLIER.get(fit, FIT_CAP_MULTIPLIER["MODERATE"])
    return round(max(0.02, hard_cap * multiplier), 4)


def sizing_for(
    signal: dict,
    *,
    fit: str = "UNAVAILABLE",
    hard_cap: float = DEFAULT_HARD_CAP,
) -> SizingResult:
    """Deterministic final sizing for a security.

    ``fit`` is the portfolio-fit verdict from the canonical risk simulation
    (service.py). When unavailable, the cap degrades safely instead of assuming
    the position is risk-free.
    """
    hard_cap = min(max(float(hard_cap), 0.05), MAX_HARD_CAP)
    symbol = str(signal.get("symbol") or "?").upper()
    tier = conviction_tier_for(signal)
    low, mid, high = bands_for_tier(tier)
    risk_cap = risk_cap_for_fit(fit, hard_cap)
    target_mid = min(mid, risk_cap)

    reasons: list[str] = []
    if fit == "UNAVAILABLE":
        reasons.append(DATA_INSUFFICIENT)
    if fit == "WEAK":
        reasons.append(RISK_CONTRIBUTION_HIGH)

    return SizingResult(
        symbol=symbol,
        conviction_tier=tier,
        target_min=round(low, 4),
        target_mid=round(target_mid, 4),
        target_max=round(min(high, risk_cap), 4),
        risk_cap=round(risk_cap, 4),
        reason_codes=tuple(dict.fromkeys(reasons)),
    )