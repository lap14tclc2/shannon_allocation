"""Suggest what to deploy next based on a completed optimizer experiment.

This is a historical robustness recommendation, not a forecast. Candidate
selection is frozen before the final holdout. The holdout may accept/reject that
candidate (or show that the simple quarterly schedule is safer), but it must never
be used to re-rank the research candidates after inspection.
"""
from __future__ import annotations

import json
import os
from datetime import datetime


MIN_FINAL_RETURN_TO_DRAWDOWN = 0.25


def _holdout_quality(test: dict | None) -> tuple[bool, list[str], float | None]:
    """Final assessment gate used only after the research winner is frozen."""
    t = test or {}
    reasons: list[str] = []
    if not t.get("valid"):
        reasons.append("final_holdout_invalid")

    ret = t.get("median_net_twr")
    mdd = t.get("worst_mdd")
    if ret is None or ret <= 0:
        reasons.append("final_holdout_return_not_positive")

    ratio = None
    if ret is not None and mdd is not None and abs(float(mdd)) > 1e-12:
        ratio = float(ret) / abs(float(mdd))
        if ratio < MIN_FINAL_RETURN_TO_DRAWDOWN:
            reasons.append(
                f"final_return_to_drawdown_below_{MIN_FINAL_RETURN_TO_DRAWDOWN:g}"
            )
    return not reasons, reasons, ratio


def build_recommendation(experiment: dict) -> dict:
    meta = experiment.get("meta") or {}
    winners = experiment.get("winners", {}) or {}
    live_best = winners.get("best_live_eligible") or {}
    research_best = winners.get("best_robust") or {}
    pre_holdout_eligible = bool(live_best)
    best = live_best or research_best

    winner_metrics = best.get("metrics") or best.get("train_metrics") or {}
    winner_robust = best.get("robust") or best.get("validation_metrics") or {}
    winner_recent = best.get("recent_validation") or {}
    winner_test = best.get("test") or best.get("test_metrics") or {}
    symbols = best.get("symbols") or []
    allocation_days = best.get("allocation_days") or []
    universe_variant = meta.get("universe_variant") or "all"
    experiment_id = experiment.get("experiment_id") or ""
    generated_at = meta.get("generated_at") or experiment.get("generated_at") or ""
    data_end = meta.get("data_end") or ""

    baseline = experiment.get("baseline") or {}
    base_robust = (baseline.get("robust") or {}).get("robust_return")
    base_test_obj = baseline.get("test") or {}
    base_test = base_test_obj.get("median_net_twr")
    base_test_mdd = base_test_obj.get("worst_mdd")
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
    if pre_holdout_eligible:
        verdict = _improvement_verdict(
            delta_robust,
            delta_test,
            bool(winner_test.get("valid")),
            opt_test_mdd,
            base_test_mdd,
        )
    else:
        verdict = "no_live_eligible_candidate"

    optimized_holdout_ok, optimized_holdout_reasons, optimized_holdout_ratio = (
        _holdout_quality(winner_test)
    )
    baseline_holdout_ok, baseline_holdout_reasons, baseline_holdout_ratio = (
        _holdout_quality(base_test_obj) if baseline else (False, ["baseline_missing"], None)
    )

    deployment_variant = "none"
    deployment_reasons: list[str] = []
    if not pre_holdout_eligible:
        deployment_reasons.extend(best.get("eligibility_reasons") or ["no_live_eligible_candidate"])
    elif optimized_holdout_ok and verdict != "keep_baseline":
        deployment_variant = "optimized"
    elif verdict == "keep_baseline" and baseline_holdout_ok:
        # The symbol combination survived research, but the optimized event
        # schedule did not improve the same-symbol quarterly benchmark. Prefer the
        # simpler benchmark instead of searching the holdout for another winner.
        deployment_variant = "quarterly_baseline"
    else:
        deployment_reasons.extend(optimized_holdout_reasons)
        if verdict == "keep_baseline":
            deployment_reasons.append("optimized_schedule_did_not_beat_baseline")
            if not baseline_holdout_ok:
                deployment_reasons.extend(
                    f"baseline:{r}" for r in baseline_holdout_reasons
                )

    deployment_eligible = deployment_variant != "none"
    recommended_allocation_days = (
        list(baseline.get("allocation_days") or [])
        if deployment_variant == "quarterly_baseline"
        else list(allocation_days)
        if deployment_variant == "optimized"
        else []
    )

    next_event_idx = _next_allocation_index(recommended_allocation_days)
    return {
        "experiment_id": experiment_id,
        "generated_at": generated_at,
        "universe_variant": universe_variant,
        "data_end": data_end,
        "pre_holdout_live_eligible": pre_holdout_eligible,
        "deployment_eligible": deployment_eligible,
        "deployment_variant": deployment_variant,
        "deployment_reasons": deployment_reasons,
        "eligibility_reasons": list(best.get("eligibility_reasons") or []),
        "symbols": list(symbols),
        "n_symbols": len(symbols),
        "allocation_count_per_year": len(allocation_days),
        "allocation_days": list(allocation_days),
        "recommended_allocation_days": recommended_allocation_days,
        "recommended_allocation_count_per_year": len(recommended_allocation_days),
        "next_allocation_index": next_event_idx,
        "score": float(best.get("score") or winner_metrics.get("score") or 0.0),
        "robust_return_pct": float(winner_robust.get("robust_return") or 0.0),
        "oos_median_net_twr_pct": float(winner_robust.get("median_net_twr") or 0.0),
        "oos_p10_net_twr_pct": float(winner_robust.get("p10_net_twr") or 0.0),
        "oos_worst_net_twr_pct": float(winner_robust.get("worst_net_twr") or 0.0),
        "oos_worst_mdd_pct": float(winner_robust.get("worst_mdd") or 0.0),
        "oos_worst_cdar95_pct": float(winner_robust.get("worst_cdar95") or 0.0),
        "recent_validation_net_twr_pct": winner_recent.get("net_twr_annualized_pct"),
        "recent_validation_mdd_pct": winner_recent.get("max_drawdown_pct"),
        "test_median_net_twr_pct": float(winner_test.get("median_net_twr") or 0.0),
        "test_worst_mdd_pct": winner_test.get("worst_mdd"),
        "test_worst_cdar95_pct": winner_test.get("worst_cdar95"),
        "test_return_to_drawdown": optimized_holdout_ratio,
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
        "baseline_test_return_to_drawdown": baseline_holdout_ratio,
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
        "final_assessment_policy": {
            "minimum_return_pct": 0.0,
            "minimum_return_to_drawdown": MIN_FINAL_RETURN_TO_DRAWDOWN,
            "selection_rule": "holdout may accept/reject frozen winner; never re-rank candidates",
        },
        "eligibility_config": meta.get("live_eligibility") or {},
        "risk_config": meta.get("risk_config") or {},
        "cost_config": meta.get("cost_config") or {},
        "caveats": [
            "Recommendation is a historically robust candidate, NOT a forecast.",
            "The research/live winner is frozen before the final holdout is inspected.",
            "Final holdout is an accept/reject assessment and cannot select a different candidate.",
            "Growth-first search changes research ranking but does not change ERC/Shannon execution mechanics.",
            "Deployment requires positive final return with acceptable return-to-drawdown quality.",
            "Re-run research when new market data materially changes the selection/risk assumptions.",
        ],
    }


def _improvement_verdict(delta_robust, delta_test, test_valid=True, opt_mdd=None, base_mdd=None):
    """Return a conservative optimized-vs-quarterly-baseline deployment verdict."""
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


def _next_allocation_index(allocation_days: list[int]) -> int:
    # Calendar-date resolution belongs to the live scheduler. The research
    # recommendation only exposes that an allocation sequence exists.
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
