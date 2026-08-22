"""Suggest what to deploy next based on a completed optimizer experiment.

This is a historical robustness recommendation, not a forecast.  Deployment
verdicts require both validation improvement and non-degradation on FINAL TEST;
a strong validation score alone is insufficient.
"""
from __future__ import annotations

import json
import os
from datetime import datetime


def build_recommendation(experiment: dict) -> dict:
    meta = experiment.get("meta") or {}
    best = experiment.get("winners", {}).get("best_robust") or {}
    winner_metrics = best.get("metrics") or best.get("train_metrics") or {}
    winner_robust = best.get("robust") or best.get("validation_metrics") or {}
    winner_test = best.get("test") or best.get("test_metrics") or {}
    symbols = best.get("symbols") or []
    allocation_days = best.get("allocation_days") or []
    universe_variant = meta.get("universe_variant") or "all"
    experiment_id = experiment.get("experiment_id") or ""
    generated_at = meta.get("generated_at") or experiment.get("generated_at") or ""
    data_end = meta.get("data_end") or ""

    baseline = experiment.get("baseline") or {}
    base_robust = (baseline.get("robust") or {}).get("robust_return")
    base_test = (baseline.get("test") or {}).get("median_net_twr")
    base_test_mdd = (baseline.get("test") or {}).get("worst_mdd")
    opt_robust = winner_robust.get("robust_return")
    opt_test = winner_test.get("median_net_twr")
    opt_test_mdd = winner_test.get("worst_mdd")

    delta_robust = (
        opt_robust - base_robust
        if opt_robust is not None and base_robust is not None
        else None
    )
    delta_test = (
        opt_test - base_test
        if opt_test is not None and base_test is not None
        else None
    )
    verdict = _improvement_verdict(
        delta_robust,
        delta_test,
        bool(winner_test.get("valid")),
        opt_test_mdd,
        base_test_mdd,
    )

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
        "score": float(best.get("score") or winner_metrics.get("score") or 0.0),
        "robust_return_pct": float(winner_robust.get("robust_return") or 0.0),
        "oos_median_net_twr_pct": float(winner_robust.get("median_net_twr") or 0.0),
        "oos_worst_net_twr_pct": float(winner_robust.get("worst_net_twr") or 0.0),
        "oos_worst_mdd_pct": float(winner_robust.get("worst_mdd") or 0.0),
        "oos_worst_cdar95_pct": float(winner_robust.get("worst_cdar95") or 0.0),
        "test_median_net_twr_pct": float(winner_test.get("median_net_twr") or 0.0),
        "test_worst_mdd_pct": winner_test.get("worst_mdd"),
        "test_worst_cdar95_pct": winner_test.get("worst_cdar95"),
        "test_valid": bool(winner_test.get("valid")),
        "train_net_twr_annualized_pct": float(winner_metrics.get("net_twr_annualized_pct") or 0.0),
        "train_sharpe": float(winner_metrics.get("sharpe") or 0.0),
        "train_max_drawdown_pct": float(winner_metrics.get("max_drawdown_pct") or 0.0),
        "train_cdar95_pct": float(winner_metrics.get("cdar95_pct") or 0.0),
        "avg_equity_exposure": winner_metrics.get("avg_equity_exposure"),
        "baseline_allocation_days": [int(d) for d in (baseline.get("allocation_days") or [])],
        "baseline_robust_return_pct": base_robust,
        "baseline_test_median_net_twr_pct": base_test,
        "baseline_test_worst_mdd_pct": base_test_mdd,
        "improvement_vs_baseline": {
            "delta_robust_return": delta_robust,
            "delta_test_median_twr": delta_test,
            "delta_test_mdd": (
                opt_test_mdd - base_test_mdd
                if opt_test_mdd is not None and base_test_mdd is not None
                else None
            ),
            "verdict": verdict,
        },
        "risk_config": meta.get("risk_config") or {},
        "cost_config": meta.get("cost_config") or {},
        "caveats": [
            "Recommendation is the most historically robust candidate, NOT a forecast.",
            "Deployment requires valid final-test windows and should remain user-approved.",
            "Re-run research when new market data materially changes the selection/risk assumptions.",
        ],
    }


def _improvement_verdict(delta_robust, delta_test, test_valid=True, opt_mdd=None, base_mdd=None):
    """Return a conservative optimized-vs-baseline deployment verdict."""
    if delta_robust is None or delta_test is None:
        return "unknown"
    if not test_valid:
        return "keep_baseline"
    if delta_test < 0:
        return "keep_baseline"
    if opt_mdd is not None and base_mdd is not None and opt_mdd < base_mdd - 2.0:
        return "keep_baseline"
    if delta_robust >= 5.0 and delta_test >= 1.0:
        return "materially_better"
    if delta_robust >= 1.0 and delta_test >= 0.0:
        return "marginal_better"
    return "not_significantly_better"


def _next_quarterly_index(allocation_days: list[int]) -> int:
    return 1 if allocation_days else 0


def write_recommendation(experiment_id: str, out_dir: str) -> str | None:
    base = os.path.join(out_dir, "optimizer", experiment_id)
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
