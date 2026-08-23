from __future__ import annotations

import math
from datetime import date


def drawdown_from_twr_indices(indices: list[float]) -> tuple[float | None, float | None]:
    if not indices:
        return None, None
    peak = float(indices[0])
    current = 0.0
    worst = 0.0
    for value in indices:
        value = float(value)
        peak = max(peak, value)
        dd = value / peak - 1.0 if peak > 0 else 0.0
        current = dd
        worst = min(worst, dd)
    return current, worst


def annualized_volatility(returns: list[float], lookback: int, annualization: int = 252) -> float | None:
    clean = [float(x) for x in returns[-lookback:] if x is not None and math.isfinite(float(x))]
    if len(clean) < max(20, min(lookback, 60) // 2):
        return None
    mean = sum(clean) / len(clean)
    var = sum((x - mean) ** 2 for x in clean) / max(1, len(clean) - 1)
    return math.sqrt(max(0.0, var)) * math.sqrt(annualization)


def _year_fraction(a: date, b: date) -> float:
    return (b - a).days / 365.25


def xnpv(rate: float, cashflows: list[tuple[date, float]]) -> float:
    if rate <= -1.0:
        return float("inf")
    d0 = cashflows[0][0]
    return sum(amount / ((1.0 + rate) ** _year_fraction(d0, d)) for d, amount in cashflows)


def xirr(cashflows: list[tuple[date, float]]) -> float | None:
    """Dependency-free XIRR by bracket expansion + bisection.

    Returns decimal annual rate. There must be at least one positive and one
    negative cash flow. Multiple-root cases remain inherently ambiguous; the
    first sign-changing bracket around ordinary investment rates is used.
    """
    if len(cashflows) < 2:
        return None
    flows = sorted(cashflows, key=lambda x: x[0])
    if not any(v < 0 for _, v in flows) or not any(v > 0 for _, v in flows):
        return None

    brackets = [
        (-0.9999, -0.9), (-0.9, -0.5), (-0.5, 0.0), (0.0, 0.25),
        (0.25, 0.75), (0.75, 2.0), (2.0, 10.0), (10.0, 100.0),
    ]
    for lo, hi in brackets:
        try:
            flo = xnpv(lo, flows)
            fhi = xnpv(hi, flows)
        except (OverflowError, ZeroDivisionError):
            continue
        if not (math.isfinite(flo) and math.isfinite(fhi)):
            continue
        if abs(flo) < 1e-9:
            return lo
        if abs(fhi) < 1e-9:
            return hi
        if flo * fhi > 0:
            continue
        for _ in range(160):
            mid = (lo + hi) / 2.0
            fm = xnpv(mid, flows)
            if abs(fm) < 1e-8:
                return mid
            if flo * fm <= 0:
                hi, fhi = mid, fm
            else:
                lo, flo = mid, fm
        return (lo + hi) / 2.0
    return None


def period_returns(snapshots: list[dict]) -> dict:
    """Return TWR-based daily/MTD/YTD/since-inception performance."""
    if not snapshots:
        return {"daily": None, "mtd": None, "ytd": None, "since_inception": None}
    rows = sorted(snapshots, key=lambda x: x["snapshot_date"])
    last = rows[-1]
    last_date = date.fromisoformat(last["snapshot_date"])

    def factor_for(predicate):
        factor = 1.0
        found = False
        for r in rows:
            d = date.fromisoformat(r["snapshot_date"])
            if predicate(d):
                ret = r.get("daily_return")
                if ret is not None:
                    factor *= 1.0 + float(ret)
                    found = True
        return factor - 1.0 if found else None

    inception = None
    if rows[-1].get("twr_index") is not None:
        inception = float(rows[-1]["twr_index"]) - 1.0
    return {
        "daily": last.get("daily_return"),
        "mtd": factor_for(lambda d: d.year == last_date.year and d.month == last_date.month),
        "ytd": factor_for(lambda d: d.year == last_date.year),
        "since_inception": inception,
    }
