"""Top-level optimizer: screened random baseline + NSGA-II + OOS robustness.

Large-universe search is intentionally staged:
  1. Reserve one GLOBAL FINAL HOLDOUT at the end of the dataset.
  2. TRAIN-only symbol screening narrows ~90 names to a configurable shortlist.
  3. A modest random baseline trains the surrogate and seeds NSGA-II.
  4. The surrogate ranks thousands of unevaluated candidates cheaply; only the
     strongest proposals receive real TRAIN backtests.
  5. A diverse TRAIN shortlist receives expensive rolling VALIDATION.
  6. A recent anchored validation gate checks the latest pre-holdout regime.
  7. Only finalists receive neighbourhood robustness + the untouched holdout.

The recent/live eligibility gate is deliberately orthogonal to the optimizer:
it does NOT change ERC, Shannon, risk targeting, NSGA-II objectives, or the
rolling robust-return formula. It only decides which research candidates are
eligible to be considered for live deployment.

Independent candidate simulations are evaluated across CPU processes when
available. This changes wall-clock time, not the quantitative methodology.
"""

from __future__ import annotations

import json
import os
import random
import time
from collections import Counter
from dataclasses import dataclass, asdict
from datetime import datetime

from ..config import BacktestParams
from ..data import load_panel
from ..candidate import Candidate, random_candidate, validate_candidate
from .eligibility import assess_live_eligibility
from .evaluate import EvaluationCache, config_fingerprint, evaluate_candidate, objectives
from .nsga2 import nsga2
from .parallel import ParallelEvaluator, auto_worker_count
from .reports import (
    item_to_json,
    leaderboards,
    pareto_frontier,
    final_report,
    write_baseline_comparison,
    write_exports,
    write_experiment_json,
)
from ..recommendation import build_recommendation
from .robustness import concentration, symbol_neighbourhood, timing_neighbourhood
from .screening import screen_universe
from .search import random_search
from .surrogate import Surrogate
from .walkforward import evaluate_robust, make_train_val_windows, split_research_holdout


@dataclass
class OptimizerConfig:
    seed: int = 42
    population_size: int = 60
    generations: int = 30
    crossover_prob: float = 0.9
    mutation_prob: float = 0.4
    n_random: int = 250
    min_gap: int = 40
    max_day: int | None = None
    lamb: float = 0.5
    n_finalists: int = 5
    train_days: int = 378
    val_days: int = 252
    test_days: int = 252                 # one global untouched holdout
    window_step: int = 120
    use_surrogate: bool = True
    data_version: str = "v5-window-accounting-live-eligibility"
    cache_path: str = "F:/workspace/shannon_allocation/python/results/optimizer_cache.json"
    out_dir: str = "F:/workspace/shannon_allocation/python/results/optimizer"

    mode: str = "joint"                 # joint | timing
    fixed_symbols: list[str] | None = None
    portfolio_size: int | None = 7       # exact N for joint mode
    require_full_coverage: bool = True

    # Large-universe acceleration. Screening uses TRAIN only.
    preselect_top: int | None = 45
    robust_pool_size: int = 180
    surrogate_pool_size: int = 5000
    surrogate_proposals: int = 40
    early_stop_generations: int | None = 15

    # 0 = auto (up to 6 processes, leaving one logical CPU for UI/server).
    parallel_workers: int = 0

    # Positive number: validation and final holdout MDD must be no worse than -this%.
    max_oos_drawdown_pct: float | None = 35.0

    # LIVE-ELIGIBILITY gates. These do not alter research scoring. The recent
    # window ends exactly at research_end, immediately before FINAL HOLDOUT.
    recent_validation_days: int = 252
    min_live_train_twr_pct: float = 0.0
    min_live_validation_p10_twr_pct: float = 0.0
    min_live_recent_twr_pct: float = 0.0

    def as_dict(self) -> dict:
        return asdict(self)


def _min_year_session_count(dates) -> int:
    counts = Counter(d.year for d in dates)
    years = sorted(counts)
    if len(years) <= 2:
        return min(counts.values())
    return min(counts[y] for y in years[1:-1])


def _quarterly_baseline(max_day: int) -> tuple[int, ...]:
    return tuple(sorted({1, round(max_day / 4), round(max_day / 2), round(3 * max_day / 4)}))


def _baseline_valid(days, max_day: int, min_gap: int) -> bool:
    return (
        len(days) == 4
        and list(days) == sorted(days)
        and all(b - a >= min_gap for a, b in zip(days, days[1:]))
        and (max_day + days[0] - days[-1]) >= min_gap
    )


def _diverse_train_shortlist(candidates, train_eval, limit: int, preferred=None):
    """Racing stage: keep objective diversity without validating everybody."""
    unique = {c.key(): c for c in candidates}
    records = []
    for c in unique.values():
        m = train_eval(c)
        if m and not m.get("error"):
            records.append((c, m))
    if len(records) <= limit:
        return [c for c, _ in records]

    selected = {}
    for c in preferred or []:
        if c.key() in unique and len(selected) < limit:
            selected[c.key()] = c

    keys = [
        ("net_twr_annualized_pct", True),
        ("score", True),
        ("sharpe", True),
        ("sortino", True),
        ("calmar", True),
        ("max_drawdown_pct", True),
        ("cdar95_pct", True),
        ("turnover_pct", False),
    ]
    per_metric = max(5, limit // (len(keys) + 2))
    for key, higher_is_better in keys:
        ranked = sorted(
            records,
            key=lambda cm: cm[1].get(key, -1e18 if higher_is_better else 1e18),
            reverse=higher_is_better,
        )
        for c, _ in ranked[:per_metric]:
            if len(selected) >= limit:
                break
            selected[c.key()] = c

    if len(selected) < limit:
        for c, _ in sorted(records, key=lambda cm: cm[1].get("score", 0.0), reverse=True):
            selected[c.key()] = c
            if len(selected) >= limit:
                break
    return list(selected.values())[:limit]


def _surrogate_candidates(
    surrogate,
    rng,
    universe,
    min_gap,
    max_day,
    fixed_symbols,
    portfolio_size,
    pool_size,
    proposals,
    exclude_keys,
):
    """Generate many candidates without backtests, then return top predictions."""
    pool = []
    seen = set(exclude_keys)
    attempts = 0
    target = max(proposals, pool_size)
    while len(pool) < target and attempts < target * 20:
        attempts += 1
        c = random_candidate(rng, universe, min_gap, max_day, fixed_symbols, portfolio_size)
        if c.key() in seen:
            continue
        seen.add(c.key())
        pool.append(c)
    return surrogate.rank(pool)[:proposals]


def run_optimizer(params: BacktestParams, opt: OptimizerConfig, progress: bool = True):
    t0 = time.time()
    experiment_id = datetime.now().strftime("%Y%m%d_%H%M%S")
    rng = random.Random(opt.seed)

    prices, universe = load_panel(params)
    dates = list(prices.index)
    universe_sorted = sorted(universe)

    if opt.portfolio_size is not None and not (5 <= opt.portfolio_size <= 10):
        raise ValueError("portfolio_size must be between 5 and 10")

    # FINAL HOLDOUT is reserved before any research ranking or eligibility gate.
    research_dates, final_holdout = split_research_holdout(dates, opt.test_days)
    windows = make_train_val_windows(
        research_dates, opt.train_days, opt.val_days, opt.window_step
    )
    if not windows:
        raise RuntimeError(
            "Not enough pre-holdout data for one train/validation window. "
            "Reduce train/val/test lengths only if the research design justifies it."
        )

    recent_days = min(max(2, int(opt.recent_validation_days)), len(research_dates))
    recent_validation = (
        research_dates[-recent_days],
        research_dates[-1],
    )

    max_day = opt.max_day if opt.max_day else _min_year_session_count(research_dates)
    if max_day < 4 * opt.min_gap:
        raise RuntimeError(
            f"max allocation day {max_day} < 4*min_gap {4*opt.min_gap}: no valid schedule exists"
        )
    baseline_days = _quarterly_baseline(max_day)
    if not _baseline_valid(baseline_days, max_day, opt.min_gap):
        raise RuntimeError(
            f"quarterly baseline {baseline_days} violates min_gap {opt.min_gap} under max_day {max_day}"
        )

    fixed = None
    search_universe = list(universe_sorted)
    screening_rows = []
    if opt.mode == "timing":
        if not opt.fixed_symbols:
            raise ValueError("mode='timing' requires fixed_symbols")
        fixed = tuple(sorted(s.upper() for s in opt.fixed_symbols))
        missing = [s for s in fixed if s not in set(universe_sorted)]
        if missing:
            raise ValueError(f"fixed_symbols not in universe/data: {missing}")
        errs = validate_candidate(
            Candidate(fixed, baseline_days),
            set(universe_sorted),
            max_day,
            opt.min_gap,
            len(fixed),
        )
        if errs:
            raise ValueError("fixed symbol portfolio invalid: " + "; ".join(errs))
        print(f"Timing-only mode: portfolio FIXED = {' '.join(fixed)}", flush=True)
    else:
        min_obs = min(params.lookback_days // 2, max(60, opt.train_days // 3))
        search_universe, screening_rows = screen_universe(
            prices,
            universe_sorted,
            windows[0]["train"],
            opt.preselect_top,
            annualization=params.annualization_factor,
            min_observations=min_obs,
        )
        if opt.portfolio_size and len(search_universe) < opt.portfolio_size:
            raise RuntimeError(
                f"TRAIN screening left only {len(search_universe)} symbols "
                f"for portfolio_size={opt.portfolio_size}"
            )
        print(
            f"Joint mode: {len(universe_sorted)} raw symbols -> {len(search_universe)} "
            f"TRAIN-screened; portfolio size={opt.portfolio_size or '5..10'}",
            flush=True,
        )

    print(
        f"Data {dates[0].date()} -> {dates[-1].date()}; research ends "
        f"{research_dates[-1].date()}; {len(windows)} rolling validation windows; "
        f"RECENT VALIDATION {recent_validation[0].date()} -> {recent_validation[1].date()}; "
        f"FINAL HOLDOUT {final_holdout[0].date()} -> {final_holdout[1].date()}; "
        f"MDD gate={opt.max_oos_drawdown_pct}%",
        flush=True,
    )

    cfg = config_fingerprint(params, opt.data_version)
    cache = EvaluationCache(opt.cache_path)

    train_start = str(windows[0]["train"][0].date())
    train_end = str(windows[0]["train"][1].date())
    train_cache_key = f"{train_start}|{train_end}"
    recent_start = str(recent_validation[0].date())
    recent_end = str(recent_validation[1].date())

    parallel = None
    resolved_workers = auto_worker_count(opt.parallel_workers)
    try:
        parallel = ParallelEvaluator(
            prices, params, dates, cfg, max_day, workers=opt.parallel_workers
        )
        print(f"Parallel evaluation: {resolved_workers} worker process(es).", flush=True)
    except Exception as exc:
        print(f"Parallel evaluation unavailable; using serial path: {exc}", flush=True)
        parallel = None
        resolved_workers = 1

    def make_eval(win):
        start = str(win[0].date())
        end = str(win[1].date())
        return lambda c: evaluate_candidate(
            c,
            prices,
            params,
            dates,
            (start, end),
            cache,
            cfg,
            max_allocation_day=max_day,
        )

    train_eval = make_eval(windows[0]["train"])
    recent_eval = make_eval(recent_validation)

    def train_eval_many(candidates):
        nonlocal parallel, resolved_workers
        candidates = list(candidates)
        out = [None] * len(candidates)
        missing = []
        missing_indices = []
        for idx, c in enumerate(candidates):
            hit = cache.get(c, train_cache_key, cfg)
            if hit is not None:
                out[idx] = hit
            else:
                missing.append(c)
                missing_indices.append(idx)
        if missing:
            try:
                metrics = (
                    parallel.evaluate_many(missing, train_start, train_end)
                    if parallel is not None
                    else [train_eval(c) for c in missing]
                )
            except Exception as exc:
                print(f"Parallel TRAIN batch failed; falling back to serial: {exc}", flush=True)
                if parallel is not None:
                    parallel.close()
                parallel = None
                resolved_workers = 1
                metrics = [train_eval(c) for c in missing]
            for idx, c, m in zip(missing_indices, missing, metrics):
                out[idx] = m
                cache.put(c, train_cache_key, cfg, m)
        return out

    train_obj_eval = lambda c: objectives(train_eval(c))
    train_obj_many = lambda candidates: [objectives(m) for m in train_eval_many(candidates)]

    val_window_dicts = [{"val": w["val"]} for w in windows]
    val_windows_serialized = [
        (str(w["val"][0].date()), str(w["val"][1].date())) for w in windows
    ]
    min_val_windows = len(val_window_dicts) if opt.require_full_coverage else None

    def robust_eval_fn(cc, w):
        ww = w["val"]
        return evaluate_candidate(
            cc,
            prices,
            params,
            dates,
            (str(ww[0].date()), str(ww[1].date())),
            cache,
            cfg,
            max_allocation_day=max_day,
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

    print(f"Random baseline: {opt.n_random} candidates on TRAIN...", flush=True)
    baseline = random_search(
        opt.n_random,
        search_universe,
        rng,
        opt.min_gap,
        max_day,
        train_eval,
        progress=progress,
        fixed_symbols=list(fixed) if fixed else None,
        portfolio_size=None if fixed else opt.portfolio_size,
        evaluate_many=train_eval_many,
    )
    if not baseline:
        if parallel is not None:
            parallel.close()
        raise RuntimeError("No valid candidates survived the TRAIN random baseline.")

    print(f"NSGA-II: pop={opt.population_size} gen={opt.generations} on TRAIN...", flush=True)
    init_pop = [b["candidate"] for b in baseline[: opt.population_size]]
    init_keys = {x.key() for x in init_pop}
    while len(init_pop) < opt.population_size:
        c = random_candidate(
            rng,
            search_universe,
            opt.min_gap,
            max_day,
            list(fixed) if fixed else None,
            None if fixed else opt.portfolio_size,
        )
        if c.key() not in init_keys:
            init_pop.append(c)
            init_keys.add(c.key())

    pop, _fit, _ = nsga2(
        init_pop,
        train_obj_eval,
        search_universe,
        rng,
        population_size=opt.population_size,
        generations=opt.generations,
        crossover_prob=opt.crossover_prob,
        mutation_prob=opt.mutation_prob,
        min_gap=opt.min_gap,
        max_day=max_day,
        progress=progress,
        fixed_symbols=list(fixed) if fixed else None,
        portfolio_size=None if fixed else opt.portfolio_size,
        early_stop_generations=opt.early_stop_generations,
        evaluate_many=train_obj_many,
    )

    proposed = []
    if opt.use_surrogate and len(baseline) >= 50 and opt.surrogate_proposals > 0:
        try:
            print(
                f"Surrogate: fitting {len(baseline)} real TRAIN runs, ranking up to "
                f"{opt.surrogate_pool_size} cheap candidates...",
                flush=True,
            )
            surf = Surrogate(search_universe, seed=opt.seed)
            surf.fit(
                [b["candidate"] for b in baseline],
                [b["metrics"]["score"] for b in baseline],
            )
            exclude = {b["candidate"].key() for b in baseline} | {c.key() for c in pop}
            proposed = _surrogate_candidates(
                surf,
                rng,
                search_universe,
                opt.min_gap,
                max_day,
                list(fixed) if fixed else None,
                None if fixed else opt.portfolio_size,
                opt.surrogate_pool_size,
                opt.surrogate_proposals,
                exclude,
            )
            proposed_metrics = train_eval_many(proposed)
            proposed = [
                c for c, m in zip(proposed, proposed_metrics)
                if m and not m.get("error")
            ]
        except Exception as exc:
            print(f"Surrogate disabled for this run: {exc}", flush=True)
            proposed = []

    candidate_pool = [b["candidate"] for b in baseline] + pop + proposed
    shortlist = _diverse_train_shortlist(
        candidate_pool,
        train_eval,
        max(opt.n_finalists, opt.robust_pool_size),
        preferred=pop,
    )
    print(
        f"Racing: {len({c.key() for c in candidate_pool})} TRAIN candidates -> "
        f"{len(shortlist)} receive full VALIDATION ({len(windows)} windows).",
        flush=True,
    )

    try:
        robust_results = (
            parallel.robust_many(
                shortlist,
                val_windows_serialized,
                opt.lamb,
                opt.require_full_coverage,
                opt.max_oos_drawdown_pct,
            )
            if parallel is not None
            else [robust_of(c) for c in shortlist]
        )
    except Exception as exc:
        print(f"Parallel VALIDATION failed; falling back to serial: {exc}", flush=True)
        if parallel is not None:
            parallel.close()
        parallel = None
        resolved_workers = 1
        robust_results = [robust_of(c) for c in shortlist]

    # Build the research records first. LIVE eligibility is evaluated only after
    # the existing robust-return calculation, so research ranking is unchanged.
    train_metrics = train_eval_many(shortlist)
    all_items = []
    for c, m, robust in zip(shortlist, train_metrics, robust_results):
        all_items.append(
            {
                "candidate": c,
                "metrics": m,
                "robust": robust,
                "objectives": objectives(m),
                "train_metrics": m,
                "validation_metrics": robust,
            }
        )

    # Avoid spending a recent-window backtest on candidates that already fail an
    # earlier live gate. This affects runtime only, not eligibility semantics.
    recent_candidates = []
    for item in all_items:
        m = item["metrics"] or {}
        r = item["robust"] or {}
        if not r:
            continue
        if m.get("net_twr_annualized_pct", -1e18) < opt.min_live_train_twr_pct:
            continue
        if r.get("p10_net_twr", -1e18) < opt.min_live_validation_p10_twr_pct:
            continue
        recent_candidates.append(item["candidate"])

    recent_by_key = {}
    if recent_candidates:
        try:
            recent_results = (
                parallel.evaluate_many(recent_candidates, recent_start, recent_end)
                if parallel is not None
                else [recent_eval(c) for c in recent_candidates]
            )
        except Exception as exc:
            print(f"Parallel RECENT validation failed; falling back to serial: {exc}", flush=True)
            if parallel is not None:
                parallel.close()
            parallel = None
            resolved_workers = 1
            recent_results = [recent_eval(c) for c in recent_candidates]
        recent_by_key = {
            c.key(): m for c, m in zip(recent_candidates, recent_results)
        }

    for item in all_items:
        recent = recent_by_key.get(item["candidate"].key())
        eligible, reasons = assess_live_eligibility(
            item.get("metrics"),
            item.get("robust"),
            recent,
            min_train_twr_pct=opt.min_live_train_twr_pct,
            min_validation_p10_twr_pct=opt.min_live_validation_p10_twr_pct,
            min_recent_twr_pct=opt.min_live_recent_twr_pct,
        )
        item["recent_validation"] = recent
        item["live_eligible"] = eligible
        item["eligibility_reasons"] = reasons

    if parallel is not None:
        parallel.close()
        parallel = None

    by_robust = sorted(
        [i for i in all_items if i["robust"]],
        key=lambda i: -i["robust"]["robust_return"],
    )
    if not by_robust:
        raise RuntimeError(
            "No candidate passed the validation risk/coverage gate. "
            "Inspect risk configuration before loosening the MDD ceiling."
        )

    by_live_robust = [i for i in by_robust if i.get("live_eligible")]
    if by_live_robust:
        finalists = by_live_robust[: opt.n_finalists]
        print(
            f"LIVE eligibility: {len(by_live_robust)}/{len(by_robust)} robust candidates passed; "
            f"testing top {len(finalists)} on FINAL HOLDOUT.",
            flush=True,
        )
    else:
        # Keep the research experiment usable even when nothing is deployable.
        # The recommendation layer will explicitly block live deployment.
        finalists = by_robust[: opt.n_finalists]
        print(
            "LIVE eligibility: 0 candidates passed. Final holdout is still run for research, "
            "but no candidate may be recommended for live deployment.",
            flush=True,
        )

    def full_test_eval(cc):
        r = evaluate_candidate(
            cc,
            prices,
            params,
            dates,
            (str(final_holdout[0].date()), str(final_holdout[1].date())),
            cache,
            cfg,
            max_allocation_day=max_day,
        )
        ok = bool(r and not r.get("error"))
        worst_mdd = r.get("max_drawdown_pct") if ok else None
        drawdown_valid = bool(
            ok
            and (
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

    # Diagnostics are informational; they do not determine research ranking.
    diagnostic_key = finalists[0]["candidate"].key()
    for item in finalists:
        c = item["candidate"]
        if c.key() == diagnostic_key:
            item["timing_robust"] = timing_neighbourhood(
                c,
                robust_of,
                radius=5,
                min_gap=opt.min_gap,
                max_day=max_day,
                value_key="robust_return",
            )
            if fixed is None:
                item["symbol_robust"] = symbol_neighbourhood(
                    c, search_universe, train_eval, rng
                )
            else:
                item["symbol_robust"] = {
                    "n_neighbours": 0,
                    "mean": None,
                    "median": None,
                    "std": None,
                    "note": "symbols fixed in timing mode",
                }
        else:
            item["timing_robust"] = {
                "n_neighbours": 0,
                "mean": None,
                "median": None,
                "std": None,
                "isolated_spike": None,
                "note": "diagnostic skipped for non-best finalist",
            }
            item["symbol_robust"] = {
                "n_neighbours": 0,
                "mean": None,
                "median": None,
                "std": None,
                "note": "diagnostic skipped for non-best finalist",
            }
        item["concentration"] = concentration(item["metrics"])
        item["test"] = full_test_eval(c)
        item["test_metrics"] = item["test"]

    provisional = leaderboards(all_items)
    for item in provisional.values():
        if item is not None and "test" not in item:
            item["test"] = full_test_eval(item["candidate"])
            item["test_metrics"] = item["test"]

    winners = leaderboards(all_items)

    baseline_items = {}
    for item in finalists:
        c = item["candidate"]
        bc = Candidate(c.symbols, baseline_days)
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
        "mode": opt.mode,
        "fixed_symbols": list(fixed) if fixed else None,
        "portfolio_size": len(fixed) if fixed else opt.portfolio_size,
        "universe": universe_sorted,
        "search_universe": search_universe,
        "universe_variant": params.universe,
        "data_start": str(dates[0].date()),
        "data_end": str(dates[-1].date()),
        "research_end": str(research_dates[-1].date()),
        "recent_validation": {
            "start": recent_start,
            "end": recent_end,
            "trading_days": recent_days,
            "purpose": "pre-holdout live eligibility only; not included in robust-return score",
        },
        "final_holdout": {
            "start": str(final_holdout[0].date()),
            "end": str(final_holdout[1].date()),
            "trading_days": opt.test_days,
        },
        "live_eligibility": {
            "min_train_twr_pct": opt.min_live_train_twr_pct,
            "min_validation_p10_twr_pct": opt.min_live_validation_p10_twr_pct,
            "min_recent_twr_pct": opt.min_live_recent_twr_pct,
            "eligible_candidates": len(by_live_robust),
            "note": "Post-research deployment gate; ERC/Shannon/NSGA-II scoring unchanged.",
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
            "screened_universe_size": len(search_universe),
            "preselect_top": opt.preselect_top,
            "top": screening_rows[: min(50, len(screening_rows))],
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
            for k in [
                "annualization_factor",
                "minimum_observations",
                "lookback_days",
                "normal_band",
                "soft_band",
                "allocation_frequency",
            ]
        },
        "risk_config": {
            k: getattr(params, k)
            for k in [
                "risk_overlay_enabled",
                "target_volatility",
                "risk_fast_lookback",
                "risk_slow_lookback",
                "min_equity_exposure",
                "risk_missing_data_exposure",
                "max_position_weight",
            ]
        },
        "cost_config": {
            k: getattr(params, k)
            for k in [
                "fee_buy_bps",
                "fee_sell_bps",
                "tax_sell_bps",
                "slippage_bps",
                "execution_lag",
            ]
        },
        "optimizer_config": opt.as_dict(),
    }

    out_dir = os.path.join(opt.out_dir, experiment_id)
    window_rows = []
    for i, item in enumerate(by_robust[:20]):
        window_rows.append(
            {
                "rank": i + 1,
                "symbols": " ".join(item["candidate"].symbols),
                "allocation_days": list(item["candidate"].allocation_days),
                "train_metrics": item["metrics"],
                "validation_metrics": item["robust"],
                "recent_validation_metrics": item.get("recent_validation"),
                "live_eligible": item.get("live_eligible"),
                "eligibility_reasons": item.get("eligibility_reasons"),
            }
        )
    timing_rows = [
        {
            "symbols": " ".join(i["candidate"].symbols),
            **{
                k: v
                for k, v in i.get("timing_robust", {}).items()
                if k != "neighbours"
            },
        }
        for i in finalists
    ]
    symbol_rows = [
        {
            "symbols": " ".join(i["candidate"].symbols),
            **{
                k: v
                for k, v in i.get("symbol_robust", {}).items()
                if k != "results"
            },
        }
        for i in finalists
    ]

    write_exports(
        out_dir,
        meta,
        all_items,
        winners,
        pareto,
        window_rows,
        timing_rows,
        symbol_rows,
    )
    write_baseline_comparison(
        out_dir, finalists, baseline_items, baseline_days, winners
    )
    for name, item in winners.items():
        if item is not None:
            final_report(item, out_dir, name)
    write_experiment_json(
        out_dir,
        meta,
        winners,
        pareto,
        by_robust[:50],
        finalists,
        baseline_items,
        baseline_days,
    )
    _write_recommendation(
        out_dir, meta, winners, baseline_items, baseline_days
    )
    cache.flush()

    elapsed = time.time() - t0
    print(f"\nOptimizer done in {elapsed:.1f}s. Experiment {experiment_id}")
    print(f"Exports -> {out_dir}")
    return {
        "experiment_id": experiment_id,
        "out_dir": out_dir,
        "items": all_items,
        "winners": winners,
        "pareto": pareto,
        "finalists": finalists,
        "meta": meta,
        "baseline": {
            "allocation_days": list(baseline_days),
            "items": {k: v for k, v in baseline_items.items()},
        },
    }


def _write_recommendation(
    out_dir: str,
    meta: dict,
    winners: dict,
    baseline_items: dict,
    baseline_days,
) -> str | None:
    """Write recommendation.json with the same baseline used by the report."""
    best = (
        winners.get("best_live_eligible")
        or winners.get("best_robust")
        or next((v for v in winners.values() if v is not None), None)
    )
    baseline = {}
    if best is not None:
        b = baseline_items.get(best["candidate"].key()) or {}
        baseline = {
            "allocation_days": [int(d) for d in baseline_days],
            "robust": b.get("robust"),
            "test": b.get("test"),
            "train": b.get("train"),
        }
    payload = {
        "experiment_id": meta["experiment_id"],
        "generated_at": meta.get("generated_at"),
        "meta": meta,
        "winners": {
            name: item_to_json(item)
            for name, item in winners.items()
            if item is not None
        },
        "baseline": baseline,
    }
    rec = build_recommendation(payload)
    rec["generated_at"] = datetime.now().isoformat(timespec="seconds")
    path = os.path.join(out_dir, "recommendation.json")
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(rec, fh, indent=2, ensure_ascii=False)
    return path
