"""Dedicated optimizer for dynamic-alpha membership + recalibration timing.

Unlike static joint search, the candidate genome here contains no stock symbols.
At every recalibration the simulator ranks the configured market universe using
strictly-past alpha features, applies the correlation filter, then hands the
selected names to ERC. The optimizer therefore searches only the number/timing
of annual recalibrations and cannot fit a static symbol tuple to the holdout.
"""

from __future__ import annotations

import json
import os
import random
import time
from dataclasses import asdict
from datetime import datetime

from ..candidate import Candidate, random_candidate
from ..config import BacktestParams
from ..data import load_panel
from ..recommendation import build_recommendation
from .eligibility import assess_live_eligibility, live_risk_reward_score
from .evaluate import EvaluationCache, config_fingerprint, evaluate_candidate, objectives
from .nsga2 import nsga2
from .parallel import ParallelEvaluator, auto_worker_count
from .reports import (
    final_report,
    leaderboards,
    pareto_frontier,
    write_baseline_comparison,
    write_exports,
    write_experiment_json,
)
from .robustness import concentration, timing_neighbourhood
from .search import random_search
from .surrogate import Surrogate
from .walkforward import evaluate_robust, make_train_val_windows, split_research_holdout
from .run import (
    OptimizerConfig,
    _baseline_valid,
    _diverse_train_shortlist,
    _min_year_session_count,
    _quarterly_baseline,
    _surrogate_candidates,
)


def _live_rank(item: dict) -> float:
    m = item.get("metrics") or {}
    r = item.get("robust") or {}
    recent = item.get("recent_validation") or {}
    quality = (item.get("live_quality") or {}).get("overall", 0.0)
    return float(
        0.42 * r.get("robust_return", -1e9)
        + 0.23 * r.get("p10_net_twr", -1e9)
        + 0.20 * recent.get("net_twr_annualized_pct", -1e9)
        + 0.10 * m.get("net_twr_annualized_pct", -1e9)
        + 0.05 * quality
    )


def run_alpha_optimizer(params: BacktestParams, opt: OptimizerConfig, progress: bool = True):
    t0 = time.time()
    experiment_id = datetime.now().strftime("%Y%m%d_%H%M%S")
    rng = random.Random(opt.seed)

    params.dynamic_alpha_enabled = True
    if not (5 <= int(params.dynamic_alpha_portfolio_size) <= 10):
        raise ValueError("dynamic_alpha_portfolio_size must be between 5 and 10")

    prices, universe = load_panel(params)
    dates = list(prices.index)
    universe_sorted = sorted(universe)
    if len(universe_sorted) < params.dynamic_alpha_portfolio_size:
        raise RuntimeError("Universe is smaller than the requested dynamic alpha portfolio.")

    research_dates, final_holdout = split_research_holdout(dates, opt.test_days)
    windows = make_train_val_windows(
        research_dates, opt.train_days, opt.val_days, opt.window_step
    )
    if not windows:
        raise RuntimeError("Not enough pre-holdout data for dynamic-alpha walk-forward validation.")

    recent_days = min(max(2, int(opt.recent_validation_days)), len(research_dates))
    recent_validation = (research_dates[-recent_days], research_dates[-1])

    max_day = opt.max_day if opt.max_day else _min_year_session_count(research_dates)
    if max_day < 4 * opt.min_gap:
        raise RuntimeError(f"max allocation day {max_day} cannot support the configured min_gap")
    baseline_days = _quarterly_baseline(max_day)
    if not _baseline_valid(baseline_days, max_day, opt.min_gap):
        raise RuntimeError("Quarterly benchmark is invalid under the current trading calendar.")

    print(
        f"Dynamic Alpha mode: rank {len(universe_sorted)} symbols at each event -> "
        f"select {params.dynamic_alpha_portfolio_size}; optimize 1-6 recalibrations/year.",
        flush=True,
    )
    print(
        f"Research ends {research_dates[-1].date()}; RECENT {recent_validation[0].date()} -> "
        f"{recent_validation[1].date()}; FINAL HOLDOUT {final_holdout[0].date()} -> "
        f"{final_holdout[1].date()}.",
        flush=True,
    )

    cfg = config_fingerprint(params, opt.data_version + "|dynamic-alpha-v1")
    cache = EvaluationCache(opt.cache_path)
    train_start = str(windows[0]["train"][0].date())
    train_end = str(windows[0]["train"][1].date())
    train_cache_key = f"{train_start}|{train_end}"
    recent_start = str(recent_validation[0].date())
    recent_end = str(recent_validation[1].date())

    parallel = None
    resolved_workers = auto_worker_count(opt.parallel_workers)
    try:
        parallel = ParallelEvaluator(prices, params, dates, cfg, max_day, workers=opt.parallel_workers)
    except Exception as exc:
        print(f"Parallel evaluation unavailable; serial fallback: {exc}", flush=True)
        resolved_workers = 1

    def make_eval(win):
        start = str(win[0].date())
        end = str(win[1].date())
        return lambda c: evaluate_candidate(
            c, prices, params, dates, (start, end), cache, cfg,
            max_allocation_day=max_day,
        )

    train_eval = make_eval(windows[0]["train"])
    recent_eval = make_eval(recent_validation)

    def train_eval_many(candidates):
        nonlocal parallel, resolved_workers
        candidates = list(candidates)
        out = [None] * len(candidates)
        missing, indices = [], []
        for i, c in enumerate(candidates):
            hit = cache.get(c, train_cache_key, cfg)
            if hit is not None:
                out[i] = hit
            else:
                missing.append(c)
                indices.append(i)
        if missing:
            try:
                values = (
                    parallel.evaluate_many(missing, train_start, train_end)
                    if parallel is not None
                    else [train_eval(c) for c in missing]
                )
            except Exception as exc:
                print(f"Parallel TRAIN failed; serial fallback: {exc}", flush=True)
                if parallel is not None:
                    parallel.close()
                parallel = None
                resolved_workers = 1
                values = [train_eval(c) for c in missing]
            for i, c, m in zip(indices, missing, values):
                out[i] = m
                cache.put(c, train_cache_key, cfg, m)
        return out

    train_obj_eval = lambda c: objectives(train_eval(c))
    train_obj_many = lambda cs: [objectives(m) for m in train_eval_many(cs)]

    val_window_dicts = [{"val": w["val"]} for w in windows]
    val_serialized = [
        (str(w["val"][0].date()), str(w["val"][1].date())) for w in windows
    ]
    min_val_windows = len(val_window_dicts) if opt.require_full_coverage else None

    def robust_eval_fn(cc, w):
        ww = w["val"]
        return evaluate_candidate(
            cc, prices, params, dates,
            (str(ww[0].date()), str(ww[1].date())),
            cache, cfg, max_allocation_day=max_day,
        )

    def robust_of(cc):
        return evaluate_robust(
            cc,
            robust_eval_fn,
            val_window_dicts,
            lamb=opt.lamb,
            min_windows=min_val_windows,
            max_drawdown_abs_pct=opt.max_oos_drawdown_pct,
        )

    # Empty symbols are intentional: they encode "membership selected dynamically".
    fixed_symbols: list[str] = []
    baseline = random_search(
        opt.n_random,
        universe_sorted,
        rng,
        opt.min_gap,
        max_day,
        train_eval,
        progress=progress,
        fixed_symbols=fixed_symbols,
        evaluate_many=train_eval_many,
    )
    if not baseline:
        if parallel is not None:
            parallel.close()
        raise RuntimeError("No deployable dynamic-alpha timing candidates survived TRAIN.")

    init_pop = [b["candidate"] for b in baseline[: opt.population_size]]
    init_keys = {c.key() for c in init_pop}
    while len(init_pop) < opt.population_size:
        c = random_candidate(
            rng, universe_sorted, opt.min_gap, max_day, fixed_symbols=fixed_symbols
        )
        if c.key() not in init_keys:
            init_pop.append(c)
            init_keys.add(c.key())

    pop, _fit, _ = nsga2(
        init_pop,
        train_obj_eval,
        universe_sorted,
        rng,
        population_size=opt.population_size,
        generations=opt.generations,
        crossover_prob=opt.crossover_prob,
        mutation_prob=opt.mutation_prob,
        min_gap=opt.min_gap,
        max_day=max_day,
        progress=progress,
        fixed_symbols=fixed_symbols,
        early_stop_generations=opt.early_stop_generations,
        evaluate_many=train_obj_many,
    )

    proposed = []
    if opt.use_surrogate and len(baseline) >= 30 and opt.surrogate_proposals > 0:
        try:
            surf = Surrogate(universe_sorted, seed=opt.seed)
            surf.fit(
                [b["candidate"] for b in baseline],
                [b["metrics"]["score"] for b in baseline],
            )
            exclude = {b["candidate"].key() for b in baseline} | {c.key() for c in pop}
            proposed = _surrogate_candidates(
                surf, rng, universe_sorted, opt.min_gap, max_day,
                fixed_symbols, None, opt.surrogate_pool_size,
                opt.surrogate_proposals, exclude,
            )
            pmetrics = train_eval_many(proposed)
            proposed = [c for c, m in zip(proposed, pmetrics) if m and not m.get("error")]
        except Exception as exc:
            print(f"Dynamic-alpha surrogate disabled: {exc}", flush=True)
            proposed = []

    candidate_pool = [b["candidate"] for b in baseline] + pop + proposed
    shortlist = _diverse_train_shortlist(
        candidate_pool,
        train_eval,
        max(opt.n_finalists, opt.robust_pool_size),
        preferred=pop,
    )

    try:
        robust_results = (
            parallel.robust_many(
                shortlist, val_serialized, opt.lamb,
                opt.require_full_coverage, opt.max_oos_drawdown_pct,
            )
            if parallel is not None
            else [robust_of(c) for c in shortlist]
        )
    except Exception as exc:
        print(f"Parallel VALIDATION failed; serial fallback: {exc}", flush=True)
        if parallel is not None:
            parallel.close()
        parallel = None
        resolved_workers = 1
        robust_results = [robust_of(c) for c in shortlist]

    train_metrics = train_eval_many(shortlist)
    all_items = [
        {
            "candidate": c,
            "metrics": m,
            "robust": robust,
            "objectives": objectives(m),
            "train_metrics": m,
            "validation_metrics": robust,
        }
        for c, m, robust in zip(shortlist, train_metrics, robust_results)
    ]

    # Recent validation is only needed after OOS-tail survival. Calmar is not a
    # hard filter anymore; it becomes the smooth live_quality score below.
    recent_candidates = [
        item["candidate"] for item in all_items
        if item.get("robust")
        and (item["robust"] or {}).get("p10_net_twr", -1e18)
            >= opt.min_live_validation_p10_twr_pct
    ]
    recent_by_key = {}
    if recent_candidates:
        try:
            vals = (
                parallel.evaluate_many(recent_candidates, recent_start, recent_end)
                if parallel is not None
                else [recent_eval(c) for c in recent_candidates]
            )
        except Exception as exc:
            print(f"Parallel RECENT failed; serial fallback: {exc}", flush=True)
            if parallel is not None:
                parallel.close()
            parallel = None
            resolved_workers = 1
            vals = [recent_eval(c) for c in recent_candidates]
        recent_by_key = {c.key(): m for c, m in zip(recent_candidates, vals)}

    for item in all_items:
        recent = recent_by_key.get(item["candidate"].key())
        eligible, reasons = assess_live_eligibility(
            item.get("metrics"),
            item.get("robust"),
            recent,
            min_train_twr_pct=None,
            min_validation_p10_twr_pct=opt.min_live_validation_p10_twr_pct,
            min_recent_twr_pct=-5.0,
        )
        item["recent_validation"] = recent
        item["live_eligible"] = eligible
        item["eligibility_reasons"] = reasons
        item["live_quality"] = live_risk_reward_score(
            item.get("metrics"), item.get("robust"), recent
        )

    if parallel is not None:
        parallel.close()
        parallel = None

    by_robust = sorted(
        [i for i in all_items if i.get("robust")],
        key=lambda i: -i["robust"]["robust_return"],
    )
    if not by_robust:
        raise RuntimeError("No dynamic-alpha candidate passed OOS coverage/risk validation.")

    live = sorted(
        [i for i in by_robust if i.get("live_eligible")],
        key=_live_rank,
        reverse=True,
    )
    finalists = (live or by_robust)[: opt.n_finalists]

    def full_test_eval(cc):
        r = evaluate_candidate(
            cc, prices, params, dates,
            (str(final_holdout[0].date()), str(final_holdout[1].date())),
            cache, cfg, max_allocation_day=max_day,
        )
        ok = bool(r and not r.get("error"))
        worst_mdd = r.get("max_drawdown_pct") if ok else None
        drawdown_valid = bool(
            ok and (
                opt.max_oos_drawdown_pct is None
                or worst_mdd >= -abs(opt.max_oos_drawdown_pct)
            )
        )
        return {
            "median_net_twr": r.get("net_twr_annualized_pct") if ok else None,
            "median_sharpe": r.get("sharpe") if ok else None,
            "worst_mdd": worst_mdd,
            "worst_cdar95": r.get("cdar95_pct") if ok else None,
            "n_test_windows": 1 if ok else 0,
            "required_test_windows": 1,
            "coverage_valid": ok,
            "drawdown_valid": drawdown_valid,
            "valid": ok and drawdown_valid,
            "holdout_start": str(final_holdout[0].date()),
            "holdout_end": str(final_holdout[1].date()),
            "per_window": [r] if r else [],
        }

    diagnostic_key = finalists[0]["candidate"].key()
    for item in finalists:
        c = item["candidate"]
        if c.key() == diagnostic_key:
            item["timing_robust"] = timing_neighbourhood(
                c, robust_of, radius=5, min_gap=opt.min_gap,
                max_day=max_day, value_key="robust_return",
            )
        else:
            item["timing_robust"] = {
                "n_neighbours": 0, "mean": None, "median": None,
                "std": None, "isolated_spike": None,
                "note": "diagnostic skipped for non-best finalist",
            }
        item["symbol_robust"] = {
            "n_neighbours": 0,
            "mean": None,
            "median": None,
            "std": None,
            "note": "not applicable: membership is re-ranked dynamically at each recalibration",
        }
        item["concentration"] = concentration(item["metrics"])
        item["test"] = full_test_eval(c)
        item["test_metrics"] = item["test"]

    winners = leaderboards(all_items)
    if live:
        winners["best_live_eligible"] = live[0]
    for item in winners.values():
        if item is not None and "test" not in item:
            item["test"] = full_test_eval(item["candidate"])
            item["test_metrics"] = item["test"]

    baseline_items = {}
    for item in finalists:
        c = item["candidate"]
        bc = Candidate((), baseline_days)
        baseline_items[c.key()] = {
            "candidate": bc,
            "train": train_eval(bc),
            "robust": robust_of(bc),
            "test": full_test_eval(bc),
        }

    pareto = pareto_frontier(all_items)
    meta = {
        "experiment_id": experiment_id,
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "seed": opt.seed,
        "data_version": opt.data_version,
        "mode": "alpha",
        "fixed_symbols": None,
        "portfolio_size": int(params.dynamic_alpha_portfolio_size),
        "universe": universe_sorted,
        "search_universe": universe_sorted,
        "universe_variant": params.universe,
        "data_start": str(dates[0].date()),
        "data_end": str(dates[-1].date()),
        "research_end": str(research_dates[-1].date()),
        "recent_validation": {
            "start": recent_start,
            "end": recent_end,
            "trading_days": recent_days,
            "purpose": "pre-holdout hard-catastrophe gate + soft risk/reward quality",
        },
        "final_holdout": {
            "start": str(final_holdout[0].date()),
            "end": str(final_holdout[1].date()),
            "trading_days": opt.test_days,
        },
        "live_eligibility": {
            "hard_gates": ["validation_p10_nonnegative", "recent_twr_above_-5pct", "OOS_MDD_ceiling"],
            "soft_quality": ["train_calmar", "validation_return_to_drawdown", "recent_calmar"],
            "eligible_candidates": len(live),
        },
        "dynamic_alpha": {
            "enabled": True,
            "portfolio_size": int(params.dynamic_alpha_portfolio_size),
            "min_observations": params.alpha_min_observations,
            "short_lookback": params.alpha_short_lookback,
            "medium_lookback": params.alpha_medium_lookback,
            "long_lookback": params.alpha_long_lookback,
            "correlation_lookback": params.alpha_correlation_lookback,
            "max_pair_correlation": params.alpha_max_pair_correlation,
            "selection_rule": "strictly-past cross-sectional alpha rank -> correlation filter -> ERC",
        },
        "max_allocation_day": max_day,
        "baseline_allocation_days": list(baseline_days),
        "n_windows": len(windows),
        "n_train_candidates": len({c.key() for c in candidate_pool}),
        "n_validation_candidates": len(shortlist),
        "parallel_workers": resolved_workers,
        "capital_config": {
            "initial_balance": params.initial_balance,
            "annual_deposit": params.annual_deposit,
            "deposit_at_start_year": params.deposit_at_start_year,
        },
        "screening": {
            "raw_universe_size": len(universe_sorted),
            "screened_universe_size": len(universe_sorted),
            "preselect_top": None,
            "note": "dynamic alpha ranks the full configured universe at each event",
        },
        "windows": [
            {
                "train": (str(w["train"][0].date()), str(w["train"][1].date())),
                "val": (str(w["val"][0].date()), str(w["val"][1].date())),
            }
            for w in windows
        ],
        "erc_config": {
            k: getattr(params, k)
            for k in ["annualization_factor", "minimum_observations", "lookback_days", "normal_band", "soft_band"]
        },
        "risk_config": {
            k: getattr(params, k)
            for k in [
                "risk_overlay_enabled", "target_volatility", "risk_fast_lookback",
                "risk_slow_lookback", "min_equity_exposure",
                "risk_missing_data_exposure", "max_position_weight",
            ]
        },
        "cost_config": {
            k: getattr(params, k)
            for k in ["fee_buy_bps", "fee_sell_bps", "tax_sell_bps", "slippage_bps", "execution_lag"]
        },
        "optimizer_config": asdict(opt),
    }

    out_dir = os.path.join(opt.out_dir, experiment_id)
    window_rows = [
        {
            "rank": i + 1,
            "symbols": "DYNAMIC_ALPHA",
            "allocation_days": list(item["candidate"].allocation_days),
            "train_metrics": item["metrics"],
            "validation_metrics": item["robust"],
            "recent_validation_metrics": item.get("recent_validation"),
            "live_quality": item.get("live_quality"),
            "live_eligible": item.get("live_eligible"),
            "eligibility_reasons": item.get("eligibility_reasons"),
        }
        for i, item in enumerate(by_robust[:20])
    ]
    timing_rows = [
        {"symbols": "DYNAMIC_ALPHA", **{k: v for k, v in i.get("timing_robust", {}).items() if k != "neighbours"}}
        for i in finalists
    ]
    symbol_rows = [
        {"symbols": "DYNAMIC_ALPHA", **{k: v for k, v in i.get("symbol_robust", {}).items() if k != "results"}}
        for i in finalists
    ]

    write_exports(out_dir, meta, all_items, winners, pareto, window_rows, timing_rows, symbol_rows)
    write_baseline_comparison(out_dir, finalists, baseline_items, baseline_days, winners)
    for name, item in winners.items():
        if item is not None:
            final_report(item, out_dir, name)
    write_experiment_json(
        out_dir, meta, winners, pareto, by_robust[:50], finalists,
        baseline_items, baseline_days,
    )

    exp_path = os.path.join(out_dir, "experiment.json")
    with open(exp_path, "r", encoding="utf-8") as fh:
        experiment = json.load(fh)
    recommendation = build_recommendation(experiment)
    recommendation["dynamic_alpha"] = meta["dynamic_alpha"]
    recommendation["symbols"] = []
    recommendation["n_symbols"] = int(params.dynamic_alpha_portfolio_size)
    with open(os.path.join(out_dir, "recommendation.json"), "w", encoding="utf-8") as fh:
        json.dump(recommendation, fh, indent=2, ensure_ascii=False)

    cache.flush()
    return {
        "experiment_id": experiment_id,
        "out_dir": out_dir,
        "elapsed_seconds": time.time() - t0,
        "mode": "alpha",
        "eligible_candidates": len(live),
    }
