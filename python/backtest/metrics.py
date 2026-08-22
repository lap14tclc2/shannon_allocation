"""Performance metrics for a single portfolio simulation.

All strategy metrics are measured from the actual investment start (first
allocation date), excluding the ERC warm-up period when the portfolio sat in cash.

Return convention (fractions unless noted):
  - time_weighted_return : TWR total, external deposits removed
  - twr_annualized       : annualized TWR
  - xirr                 : investor money-weighted annualized return
  - sortino / calmar     : risk-adjusted
  - annual_returns       : per-calendar-year TWR
"""

from __future__ import annotations

import math

ANNUALIZATION = 252
DAYS_PER_YEAR = 365.25


def clamp01(x):
    return min(max(x, 0.0), 1.0)


def time_weighted_return(navs, deposit_indices, start_idx, end_idx):
    """Total TWR (fraction) between navs[start_idx] and navs[end_idx], removing deposits."""
    deposit_set = set(deposit_indices)
    segs = []
    base = start_idx
    for di in sorted(deposit_set):
        if di <= start_idx:
            continue
        if di > end_idx:
            break
        if di - 1 >= base and navs[base] > 0:
            segs.append(navs[di - 1] / navs[base])
        base = di
    if end_idx > base and navs[base] > 0 and navs[end_idx] > 0:
        segs.append(navs[end_idx] / navs[base])
    if not segs:
        return 0.0
    prod = 1.0
    for s in segs:
        prod *= s
    return prod - 1.0


def max_drawdown(navs, start_idx, end_idx):
    running_max = -1e18
    worst = 0.0
    for i in range(start_idx, end_idx + 1):
        v = navs[i]
        if v > running_max:
            running_max = v
        if running_max > 0:
            dd = v / running_max - 1.0
            if dd < worst:
                worst = dd
    return worst


def annual_returns(navs, dates, deposit_indices, start_idx, end_idx):
    """dict year -> TWR (fraction) for each calendar year overlapping the investment period."""
    years = {}
    for i in range(start_idx, end_idx + 1):
        y = dates[i].year
        years.setdefault(y, [None, None])
        if years[y][0] is None:
            years[y][0] = i
        years[y][1] = i
    deposit_set = set(deposit_indices)
    out = {}
    for y, (a, b) in years.items():
        if a is None or b is None:
            continue
        out[y] = time_weighted_return(navs, deposit_set, a, b)
    return out


def annualized_from_total(twr_total, days):
    if days <= 0 or (1 + twr_total) <= 0:
        return None
    return (1.0 + twr_total) ** (DAYS_PER_YEAR / days) - 1.0


def sharpe_sortino(log_returns, rf=0.0):
    """Return (sharpe, sortino) annualized from daily log returns (fractions)."""
    arr = [r for r in log_returns if r is not None and not (r != r)]  # drop nan
    if len(arr) < 2:
        return None, None
    mean = sum(arr) / len(arr)
    var = sum((r - mean) ** 2 for r in arr) / (len(arr) - 1)
    std = math.sqrt(var) if var > 0 else 0.0
    downside = math.sqrt(sum(min(0.0, r) ** 2 for r in arr) / len(arr))
    sharpe = (mean - rf / ANNUALIZATION) / std * math.sqrt(ANNUALIZATION) if std > 0 else None
    sortino = (mean - rf / ANNUALIZATION) / downside * math.sqrt(ANNUALIZATION) if downside > 0 else None
    return sharpe, sortino


def xirr(flows):
    """Money-weighted annualized return (fraction).

    flows: list of (amount, day) where day is an ordinal day. Positive amount =
    money returned to investor (final value); negative = money contributed.
    Solve sum(amount * (1+r)**(-t)) = 0 by bisection, t in years.
    """
    if not flows:
        return None
    day0 = min(day for _, day in flows)
    t = [(day - day0) / DAYS_PER_YEAR for _, day in flows]
    amts = [amount for amount, _ in flows]

    def f(r):
        base = 1.0 + r
        if abs(base) < 1e-9:  # floor avoids overflow at extremely negative rates
            base = math.copysign(1e-9, base)
        total = 0.0
        for ti, a in zip(t, amts):
            total += a * (base ** (-ti))
        return total

    lo, hi = -0.9999, 5.0
    flo, fhi = f(lo), f(hi)
    if math.isnan(flo) or math.isnan(fhi) or flo * fhi > 0:
        return None
    for _ in range(200):
        mid = 0.5 * (lo + hi)
        fm = f(mid)
        if abs(fm) < 1e-9:
            return mid
        if flo * fm <= 0:
            hi, fhi = mid, fm
        else:
            lo, flo = mid, fm
    return 0.5 * (lo + hi)


def portfolio_score(twr_annualized, sharpe, mdd, positive_year_ratio):
    """Composite 0-100 score: return quality + risk-adjusted + drawdown + consistency."""
    if twr_annualized is None:
        twr_annualized = 0.0
    if sharpe is None:
        sharpe = 0.0
    mdd_frac = abs(mdd) if mdd is not None else 0.0
    ret_pts = clamp01(twr_annualized * 100.0 / 50.0) * 40.0
    sharpe_pts = clamp01((sharpe + 1.0) / 3.0) * 25.0
    mdd_pts = clamp01(1.0 - mdd_frac / 0.60) * 20.0
    cons_pts = clamp01(positive_year_ratio) * 15.0
    return round(ret_pts + sharpe_pts + mdd_pts + cons_pts, 2)