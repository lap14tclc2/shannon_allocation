"""Top-level optimizer: screened random baseline + NSGA-II + OOS robustness.

Large-universe search is intentionally staged:
  1. TRAIN-only symbol screening narrows ~90 names to a configurable shortlist.
  2. A modest random baseline trains the surrogate and seeds NSGA-II.
  3. The surrogate ranks thousands of *unevaluated* candidates cheaply; only the
     most promising proposals receive real TRAIN backtests.
  4. A diverse TRAIN shortlist receives expensive multi-window VALIDATION.
  5. Only finalists receive timing/symbol neighbourhood and FINAL TEST work.

Validation/test data never participates in screening or surrogate training.
"""

from __future__ import annotations

import json
import os
import random
import time
from collections import Counter
from dataclasses import dataclass, asdict
from datetime import datetime
from statistics import median

from ..config import BacktestParams
from ..data import load_panel
from ..candidate import Candidate, random_candidate, validate_candidate
from .evaluate import (
    EvaluationCache,
    config_fingerprint,
    evaluate_candidate,
    objectives,
    OBJECTIVE_NAMES,
)
from .nsga2 import nsga2
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
from .walkforward import evaluate_robust, make_windows


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
    test_days: int = 252
    window_step: int = 120
    use_surrogate: bool = True
    data_version: str = "v3-risk-fast"
    cache_path: str = "F:/workspace/shannon_allocation/python/results/optimizer_cache.json"
    out_dir: str = "F:/workspace/shannon_allocation/python/results/optimizer"

    mode: str = "joint"                      # joint | timing
    fixed_symbols: list[str] | None = None
    portfolio_size: int | None = 7            # exact N for joint mode; None keeps legacy 5..10
    require_full_coverage: bool = True

    # Large-universe acceleration. Screening uses TRAIN only.
    preselect_top: int | None = 45
    robust_pool_size: int = 180
    surrogate_pool_size: int = 5000
    surrogate_proposals: int = 40
    early_stop_generations: int | None = 15

    # Positive number: every OOS validation/test MDD must be no worse than -this%.
    max_oos_drawdown_pct: float | None = 35.0

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
    """Racing stage: retain a diverse set without running validation on everybody."""
    unique = {}
    for c in candidates:
        unique[c.key()] = c
    records = []
    for c in unique.values():
        m = train_eval(c)
        if m and not m.get("error"):
            records.append((c, m))
    if len(records) <= limit:
        return [c for c, _ in records]

    selected = {}
    preferred = preferred or []
    for c in preferred:
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
        ranked = sorted(records, key=lambda cm: cm[1].get("score", 0.0), reverse=True)
        for c, _ in ranked:
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
        c = random_candidate(
            rng, universe, min_gap, max_day, fixed_symbols, portfolio_size
        )
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

    max_day = opt.max_day if opt.max_day else _min_year_session_count(dates)
    if max_day < 4 * opt.min_gap:
        raise RuntimeError(f"max allocation day {max_day} < 4*min_gap {4*opt.min_gap}: no valid schedule exists")
    baseline_days = _quarterly_baseline(max_day)
    if not _baseline_valid(baseline_days, max_day, opt.min_gap):
        raise RuntimeError(f"quarterly baseline {baseline_days} violates min_gap {opt.min_gap} under max_day {max_day}")

    windows = make_windows(dates, opt.train_days, opt.val_days, opt.test_days, opt.window_step)
    if not windows:
        raise RuntimeError("Not enough data for even one train/val/test window.")

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
            Candidate(fixed, baseline_days), set(universe_sorted), max_day, opt.min_gap, len(fixed)
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
                f"TRAIN screening left only {len(search_universe)} symbols for portfolio_size={opt.portfolio_size}"
            )
        print(
            f"Joint mode: {len(universe_sorted)} raw symbols -> {len(search_universe)} TRAIN-screened; "
            f"portfolio size={opt.portfolio_size or '5..10'}",
            flush=True,
        )

    print(
        f"Data {dates[0].date()} -> {dates[-1].date()}; {len(windows)} rolling windows; "
        f"max allocation day={max_day}; OOS MDD gate={opt.max_oos_drawdown_pct}",
        flush=True,
    )

    cfg = config_fingerprint(params, opt.data_version)
    cache = EvaluationCache(opt.cache_path)

    def make_eval(win):
        start = str(win[0].date())
        end = str(win[1].date())
        return lambda c: evaluate_candidate(
            c, prices, params, dates, (start, end), cache, cfg, max_allocation_day=max_day
        )

    train_eval = make_eval(windows[0]["train"])
    train_obj_eval = lambda c: objectives(train_eval(c))

    val_window_dicts = [{"val": w["val"]} for w in windows]
    min_val_windows = len(val_window_dicts) if opt.require_full_coverage else None

    def robust_eval_fn(cc, w):
        ww = w["val"]
        return evaluate_candidate(
            cc, prices, params, dates,
            (str(ww[0].date()), str(ww[1].date())), cache, cfg,
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
    )
    if not baseline:
        raise RuntimeError("No valid candidates survived the TRAIN random baseline.")

    print(f"NSGA-II: pop={opt.population_size} gen={opt.generations} on TRAIN...", flush=True)
    init_pop = [b["candidate"] for b in baseline[: opt.population_size]]
    init_keys = {x.key() for x in init_pop}
    while len(init_pop) < opt.population_size:
        c = random_candidate(
            rng, search_universe, opt.min_gap, max_day,
            list(fixed) if fixed else None,
            None if fixed else opt.portfolio_size,
        )
        if c.key() not in init_keys:
            init_pop.append(c)
            init_keys.add(c.key())

    pop, fit, _ = nsga2(
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
    )

    proposed = []
    if opt.use_surrogate and len(baseline) >= 50:
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
            # Force real TRAIN evaluations now; prediction is never a final result.
            proposed = [c for c in proposed if train_eval(c) and not train_eval(c).get("error")]
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

    all_items = []
    for idx, c in enumerate(shortlist):
        m = train_eval(c)
        robust = robust_of(c)
        item = {
            "candidate": c,
            "metrics": m,
            "robust": robust,
            "objectives": objectives(m),
            "train_metrics": m,
            "validation_metrics": robust,
        }
        all_items.append(item)
        if progress and (idx + 1) % 25 == 0:
            print(
                f"  validation {idx+1}/{len(shortlist)} robust="
                f"{(robust or {}).get('robust_return')}",
                flush=True,
            )

    by_robust = sorted(
        [i for i in all_items if i["robust"]],
        key=lambda i: -i["robust"]["robust_return"],
    )
    if not by_robust:
        raise RuntimeError(
            "No candidate passed the OOS risk/coverage gate. Increase max_oos_drawdown_pct "
            "or reduce target volatility only after inspecting the failed run configuration."
        )
    finalists = by_robust[: opt.n_finalists]
    test_windows = [{"test": w["test"]} for w in windows]

    def full_test_eval(cc):
        res = [
            evaluate_candidate(
                cc, prices, params, dates,
                (str(w[0].date()), str(w[1].date())), cache, cfg,
                max_allocation_day=max_day,
            )
            for w in [tw["test"] for tw in test_windows]
        ]
        ok = [r for r in res if r and not r.get("error")]
        coverage_valid = len(ok) == len(test_windows)
        worst_mdd = min([r["max_drawdown_pct"] for r in ok], default=None)
        drawdown_valid = (
            worst_mdd is not None
            and (
                opt.max_oos_drawdown_pct is None
                or worst_mdd >= -abs(opt.max_oos_drawdown_pct)
            )
        )
        return {
            "median_net_twr": median([r["net_twr_annualized_pct"] for r in ok]) if ok else None,
            "median_sharpe": median([r["sharpe"] for r in ok]) if ok else None,
            "worst_mdd": worst_mdd,
            "worst_cdar95": min([r.get("cdar95_pct", 0.0) for r in ok], default=None),
            "n_test_windows": len(ok),
            "required_test_windows": len(test_windows),
            "coverage_valid": coverage_valid,
            "drawdown_valid": drawdown_valid,
            "valid": coverage_valid and drawdown_valid,
            "per_window": res,
        }

    for item in finalists:
        c = item["candidate"]
        item["timing_robust"] = timing_neighbourhood(
            c, robust_of, radius=5, min_gap=opt.min_gap,
            max_day=max_day, value_key="robust_return",
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
        item["concentration"] = concentration(item["metrics"])
        item["test"] = full_test_eval(c)
        item["test_metrics"] = item["test"]

    # Compute test blocks for train leaderboards too; final robust winner is chosen
    # after these blocks are attached.
    provisional = leaderboards(all_items)
    for item in provisional.values():
        if "test" not in item:
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
        "max_allocation_day": max_day,
        "baseline_allocation_days": list(baseline_days),
        "n_windows": len(windows),
        "n_train_candidates": len({c.key() for c in candidate_pool}),
        "n_validation_candidates": len(shortlist),
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
                "test": (str(w["test"][0].date()), str(w["test"][1].date())),
            }
            for w in windows
        ],
        "erc_config": {
            k: getattr(params, k)
            for k in [
                "annualization_factor", "minimum_observations", "lookback_days",
                "normal_band", "soft_band", "allocation_frequency",
            ]
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
            for k in [
                "fee_buy_bps", "fee_sell_bps", "tax_sell_bps",
                "slippage_bps", "execution_lag",
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
            }
        )
    timing_rows = [
        {
            "symbols": " ".join(i["candidate"].symbols),
            **{k: v for k, v in i.get("timing_robust", {}).items() if k != "neighbours"},
        }
        for i in finalists
    ]
    symbol_rows = [
        {
            "symbols": " ".join(i["candidate"].symbols),
            **{k: v for k, v in i.get("symbol_robust", {}).items() if k != "results"},
        }
        for i in finalists
    ]

    write_exports(out_dir, meta, all_items, winners, pareto, window_rows, timing_rows, symbol_rows)
    write_baseline_comparison(out_dir, finalists, baseline_items, baseline_days, winners)
    for name, item in winners.items():
        final_report(item, out_dir, name)
    write_experiment_json(
        out_dir, meta, winners, pareto, by_robust[:50], finalists,
        baseline_items, baseline_days,
    )
    _write_recommendation(out_dir, meta, winners)
    cache.flush()

    print(f"\nOptimizer done in {time.time()-t0:.1f}s. Experiment {experiment_id}")
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


def _write_recommendation(out_dir: str, meta: dict, winners: dict) -> str | None:
    payload = {
        "experiment_id": meta["experiment_id"],
        "generated_at": meta.get("generated_at"),
        "meta": meta,
        "winners": {name: item_to_json(item) for name, item in winners.items()},
    }
    rec = build_recommendation(payload)
    rec["generated_at"] = datetime.now().isoformat(timespec="seconds")
    path = os.path.join(out_dir, "recommendation.json")
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(rec, fh, indent=2, ensure_ascii=False)
    return path
