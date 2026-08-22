"""Walk-forward validation, robust fitness, and successive halving / racing.

Optimization uses TRAIN windows, ranking uses VALIDATION windows, and TEST is
reserved for final evaluation.  Robust fitness can enforce a hard OOS maximum-
drawdown ceiling so a high-return candidate cannot win while violating the
portfolio's risk budget.
"""

from __future__ import annotations

import random
from statistics import median


def make_windows(dates, train_days=504, val_days=252, test_days=252, step=252) -> list[dict]:
    windows = []
    i = 0
    n = len(dates)
    while i + train_days + val_days + test_days <= n:
        windows.append(
            {
                "train": (dates[i], dates[i + train_days - 1]),
                "val": (dates[i + train_days], dates[i + train_days + val_days - 1]),
                "test": (dates[i + train_days + val_days], dates[i + train_days + val_days + test_days - 1]),
            }
        )
        i += step
    return windows


def _p(vals, p):
    vals = sorted(vals)
    k = (len(vals) - 1) * p
    lo = int(k)
    hi = min(lo + 1, len(vals) - 1)
    return vals[lo] + (k - lo) * (vals[hi] - vals[lo])


def evaluate_robust(
    candidate,
    eval_fn,
    windows: list[dict],
    lamb: float = 0.5,
    min_windows: int | None = None,
    max_drawdown_abs_pct: float | None = None,
) -> dict | None:
    """Evaluate a candidate on every window and aggregate robust metrics.

    ``max_drawdown_abs_pct`` is a positive number, e.g. 35 means every validation
    window must have MDD >= -35%.  A violation makes the candidate ineligible.
    """
    per = []
    for w in windows:
        m = eval_fn(candidate, w)
        if m is None or m.get("error"):
            continue
        per.append(m)
    if not per:
        return None
    if min_windows is not None and len(per) < min_windows:
        return None

    twrs = [m["net_twr_annualized_pct"] for m in per]
    sharpes = [m["sharpe"] for m in per]
    mdds = [m["max_drawdown_pct"] for m in per]
    cdars = [m.get("cdar95_pct", 0.0) for m in per]
    if max_drawdown_abs_pct is not None and any(mdd < -abs(max_drawdown_abs_pct) for mdd in mdds):
        return None

    mean = sum(twrs) / len(twrs)
    var = sum((t - mean) ** 2 for t in twrs) / (len(twrs) - 1) if len(twrs) > 1 else 0.0
    robust = {
        "median_net_twr": median(twrs),
        "p10_net_twr": _p(twrs, 0.10),
        "p25_net_twr": _p(twrs, 0.25),
        "worst_net_twr": min(twrs),
        "return_std": var ** 0.5,
        "median_sharpe": median(sharpes),
        "worst_mdd": min(mdds),
        "median_cdar95": median(cdars),
        "worst_cdar95": min(cdars),
        "positive_window_ratio": sum(1 for t in twrs if t > 0) / len(twrs),
        "n_windows": len(twrs),
        "robust_return": median(twrs) - lamb * (var ** 0.5),
        "drawdown_gate_pct": max_drawdown_abs_pct,
    }
    return robust


def halving(
    candidates,
    eval_fn,
    rng: random.Random,
    cutoffs=(10000, 2000, 500, 100, 20),
    lamb: float = 0.5,
    progress: bool = True,
):
    population = list(candidates)
    eliminated = []
    for level, cutoff in enumerate(cutoffs):
        if len(population) <= cutoff:
            break
        scored = []
        for c in population:
            m = eval_fn(c, level)
            if m is None:
                eliminated.append((c, None, "eval_failed"))
                continue
            scored.append((c, m))
        scored.sort(key=lambda cm: cm[1].get("robust_return", -1e9), reverse=True)
        keep_n = max(cutoff, 1)
        population = [cm[0] for cm in scored[:keep_n]]
        for c, m in scored[keep_n:]:
            eliminated.append((c, m, f"below_cutoff_{cutoff}"))
        if progress:
            print(f"  halving level {level}: retained {len(population)}/{len(scored)} (cutoff {cutoff})", flush=True)
    return population, eliminated
