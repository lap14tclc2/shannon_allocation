"""Suggest what to deploy next based on a completed optimizer experiment.

The system is purely historical/backward-looking — it has no forecast engine
and no live runner. But the *most robust historical candidate* is a sensible
"what to deploy next" recommendation: it survived the most historical
walk-forward windows, so it's the portfolio most likely to behave well under
realistic regime changes. This module lifts that answer out of the experiment
so the UI can surface it as an actionable recommendation, clearly labelled.

Honest caveats (exported alongside the suggestion):
  - This is NOT a forecast. It is the candidate with the strongest historical
    robustness from the last optimizer experiment.
  - The live daily runner (fetch open prices at 09:20, compute today's signal,
    produce real target trades) is not built yet — the recommendation here is
    meant to be acted on manually at the next allocation event.
  - The recommendation becomes invalid as soon as new market data invalidates
    the assumptions used by ERC on the chosen universe. Re-run the optimizer
    periodically.
"""
from __future__ import annotations

import json
import os
from datetime import datetime


def build_recommendation(experiment: dict) -> dict:
    """Derive the next-action recommendation from an optimizer experiment.

    Input: the experiment JSON returned by /api/optimizer/<id>
    Output: a dict with deployment-ready fields.
    """
    meta = experiment.get("meta") or {}
    best = experiment.get("winners", {}).get("best_robust") or {}
    winner_metrics = best.get("metrics") or {}
    winner_robust = best.get("robust") or {}
    winner_test = best.get("test") or {}
    symbols = best.get("symbols") or []
    allocation_days = best.get("allocation_days") or []
    universe_variant = meta.get("universe_variant") or "all"
    experiment_id = experiment.get("experiment_id") or ""
    generated_at = meta.get("generated_at") or experiment.get("generated_at") or ""
    data_end = meta.get("data_end") or ""

    baseline = experiment.get("baseline") or {}
    base_robust = (baseline.get("robust") or {}).get("robust_return")
    base_test = (baseline.get("test") or {}).get("median_net_twr")
    opt_robust = winner_robust.get("robust_return")
    opt_test = winner_test.get("median_net_twr")
    delta_robust = (opt_robust - base_robust) if (opt_robust is not None and base_robust is not None) else None
    delta_test = (opt_test - base_test) if (opt_test is not None and base_test is not None) else None
    verdict = _improvement_verdict(delta_robust, delta_test)

    next_event_idx = _next_quarterly_index(allocation_days)
    return {
        "experiment_id": experiment_id,
        "generated_at": generated_at,
        "universe_variant": universe_variant,
        "data_end": data_end,
        "symbols": list(symbols),
        "n_symbols": len(symbols),
        "allocation_days": list(allocation_days),
        "next_allocation_index": next_event_idx,
        "score": float(best.get("score") or 0.0),
        "robust_return_pct": float(winner_robust.get("robust_return") or 0.0),
        "oos_median_net_twr_pct": float(winner_robust.get("median_net_twr") or 0.0),
        "oos_worst_net_twr_pct": float(winner_robust.get("worst_net_twr") or 0.0),
        "oos_worst_mdd_pct": float(winner_robust.get("worst_mdd") or 0.0),
        "test_median_net_twr_pct": float(winner_test.get("median_net_twr") or 0.0),
        "test_valid": bool(winner_test.get("valid")),
        "train_net_twr_annualized_pct": float(winner_metrics.get("net_twr_annualized_pct") or 0.0),
        "train_sharpe": float(winner_metrics.get("sharpe") or 0.0),
        "train_max_drawdown_pct": float(winner_metrics.get("max_drawdown_pct") or 0.0),
        "baseline_allocation_days": [int(d) for d in (baseline.get("allocation_days") or [])],
        "baseline_robust_return_pct": base_robust,
        "baseline_test_median_net_twr_pct": base_test,
        "improvement_vs_baseline": {
            "delta_robust_return": delta_robust,
            "delta_test_median_twr": delta_test,
            "verdict": verdict,
        },
        "cost_config": meta.get("cost_config") or {},
        "caveats": [
            "Recommendation is the most historically robust candidate from the optimizer, NOT a forecast.",
            "No live daily runner is built yet — the open-price-once-at-09:20 fetch and target-trade generation are pending.",
            "Re-run the optimizer whenever new market data materially changes the ERC signal.",
        ],
    }


def _improvement_verdict(delta_robust, delta_test):
    """Should we deploy the optimized schedule over the plain quarterly baseline?"""
    if delta_robust is None:
        return "unknown"
    if delta_robust >= 5.0:
        return "materially_better"
    if delta_robust >= 1.0:
        return "marginal_better"
    return "not_significantly_better"


def _next_quarterly_index(allocation_days: list[int]) -> int:
    """Return the next allocation index (1-based) in the order they will fire."""
    return 1 if allocation_days else 0


# --------------------------------------------------------------------- file I/O

def write_recommendation(experiment_id: str, out_dir: str) -> str | None:
    """Read experiment.json and write recommendation.json next to it."""
    base = os.path.join(out_dir, "runs" if False else "optimizer", experiment_id)
    exp_path = os.path.join(base, "experiment.json")
    if not os.path.isfile(exp_path):
        return None
    with open(exp_path, "r", encoding="utf-8") as fh:
        experiment = json.load(fh)
    rec = build_recommendation(experiment)
    rec["generated_at"] = datetime.now().isoformat(timespec="seconds")
    out_path = os.path.join(base, "recommendation.json")
    with open(out_path, "w", encoding="utf-8") as fh:
        json.dump(rec, fh, indent=2, ensure_ascii=False)
    return out_path