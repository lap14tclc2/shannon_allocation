"""Walk-forward validation, robust fitness, and successive halving / racing.

WINDOW discipline: optimization uses TRAIN windows, ranking uses VALIDATION
windows, and the untouched TEST windows are reserved for final evaluation.
A candidate's robustness is measured across K validation windows (median, lower
tail, dispersion), not a single backtest.
"""

from __future__ import annotations

import random
from statistics import median


def make_windows(dates, train_days=504, val_days=252, test_days=252, step=252) -> list[dict]:
    """Rolling train/val/test windows over the date list."""
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


def evaluate_robust(candidate, eval_fn, windows: list[dict], lamb: float = 0.5, min_windows: int | None = None) -> dict | None:
    """Evaluate `candidate` on every window and aggregate into robust metrics.

    eval_fn(candidate, window) -> metrics dict (or None on failure).
    Returns None if no window succeeded, or if `min_windows` is set and fewer
    than that many windows succeeded (100% coverage policy: a candidate that
    fails ANY validation window is INVALID, not partially robust).
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
        "positive_window_ratio": sum(1 for t in twrs if t > 0) / len(twrs),
        "n_windows": len(twrs),
        "robust_return": median(twrs) - lamb * (var ** 0.5),
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
    """Successive halving: cheap eval -> retain best -> expensive eval -> ...

    `eval_fn(candidate, level_index) -> metrics or None`. Candidates are ranked
    by robust_return at each level. Returns list of (candidate, metrics, reason).
    """
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