"""Top-level optimizer: random baseline + NSGA-II + walk-forward robustness.

Two modes:
  - "joint":  searches symbols AND the four annual allocation times together.
  - "timing": the portfolio set is FIXED (`fixed_symbols`) and only the four
              allocation times [T1,T2,T3,T4] are optimized. This answers the
              question "which timing schedule is best for THIS portfolio?"
              without symbol selection contaminating the timing result.

Discipline (evaluation methodology):
  - optimization evaluates candidates ONLY on TRAIN windows
  - ranking uses VALIDATION windows (robust fitness)
  - untouched TEST windows measure final out-of-sample performance
  - NET performance (after transaction costs) is used throughout
  - every window supplies ~lookback_days of pre-window history so ERC can
    calibrate at the first allocation inside the window (no look-ahead)
  - performance is measured from the WINDOW START (cash period included), never
    from the first allocation inside the window
  - candidates that fail ANY validation or test window are INVALID (100%
    coverage policy), not "partially robust"
  - the four allocation times satisfy the cyclic minimum-gap constraint, i.e.
    YEAR_LENGTH + T1 - T4 >= min_gap as well as T2-T1, T3-T2, T4-T3 >= min_gap
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
from .search import random_search
from .surrogate import Surrogate
from .walkforward import evaluate_robust, make_windows


@dataclass
class OptimizerConfig:
    seed: int = 42
    population_size: int = 200
    generations: int = 100
    crossover_prob: float = 0.9
    mutation_prob: float = 0.4
    n_random: int = 1000
    min_gap: int = 40
    max_day: int | None = None          # None => resolved from the real trading calendar
    lamb: float = 0.5
    n_finalists: int = 5
    train_days: int = 378          # ~1.5 years (optimization window)
    val_days: int = 252            # >= 1 year (ranking / robust fitness window)
    test_days: int = 252           # >= 1 year (untouched OOS evaluation)
    window_step: int = 120
    use_surrogate: bool = True
    data_version: str = "v2"       # bumped to invalidate pre-audit cached evaluations
    cache_path: str = "F:/workspace/shannon_allocation/python/results/optimizer_cache.json"
    out_dir: str = "F:/workspace/shannon_allocation/python/results/optimizer"

    # --- evaluation methodology (audit fixes) ---
    mode: str = "joint"                 # "joint" | "timing"
    fixed_symbols: list[str] | None = None   # required when mode == "timing"
    require_full_coverage: bool = True  # candidate INVALID unless every val/test window succeeds

    def as_dict(self) -> dict:
        return asdict(self)


def _min_year_session_count(dates) -> int:
    """Fewest trading sessions of a FULL calendar year in the data (shortens to
    resolve day 252 against the real calendar instead of assuming exactly 252)."""
    counts = Counter(d.year for d in dates)
    years = sorted(counts)
    if len(years) <= 2:
        return min(counts.values())
    return min(counts[y] for y in years[1:-1])  # drop partial first/last years


def _quarterly_baseline(max_day: int) -> tuple[int, ...]:
    """Standard four-times-per-year baseline: first trading day of each quarter."""
    return tuple(sorted({1, round(max_day / 4), round(max_day / 2), round(3 * max_day / 4)}))


def _baseline_valid(days, max_day: int, min_gap: int) -> bool:
    return (
        len(days) == 4
        and list(days) == sorted(days)
        and all(b - a >= min_gap for a, b in zip(days, days[1:]))
        and (max_day + days[0] - days[-1]) >= min_gap
    )


def run_optimizer(params: BacktestParams, opt: OptimizerConfig, progress: bool = True):
    t0 = time.time()
    experiment_id = datetime.now().strftime("%Y%m%d_%H%M%S")
    rng = random.Random(opt.seed)

    prices, universe = load_panel(params)
    dates = list(prices.index)
    universe_sorted = sorted(universe)

    max_day = opt.max_day if opt.max_day else _min_year_session_count(dates)
    if max_day < 4 * opt.min_gap:
        raise RuntimeError(f"max allocation day {max_day} < 4*min_gap {4*opt.min_gap}: no valid schedule exists")
    baseline_days = _quarterly_baseline(max_day)
    if not _baseline_valid(baseline_days, max_day, opt.min_gap):
        raise RuntimeError(f"quarterly baseline {baseline_days} violates min_gap {opt.min_gap} under max_day {max_day}")

    # Timing-only mode: freeze the portfolio set.
    fixed = None
    if opt.mode == "timing":
        if not opt.fixed_symbols:
            raise ValueError(
                "mode='timing' requires fixed_symbols: the portfolio set is frozen and "
                "only [T1,T2,T3,T4] is optimized. Pass e.g. --fixed-symbols CTG,GVR,HDB."
            )
        fixed = tuple(sorted(s.upper() for s in opt.fixed_symbols))
        missing = [s for s in fixed if s not in set(universe_sorted)]
        if missing:
            raise ValueError(f"fixed_symbols not in universe/data: {missing}")
        errs = validate_candidate(Candidate(fixed, baseline_days), set(universe_sorted), max_day, opt.min_gap)
        if errs:
            raise ValueError("fixed symbol portfolio invalid: " + "; ".join(errs))
        print(f"Timing-only mode: portfolio FIXED = {' '.join(fixed)}; optimizing [T1..T4] only.", flush=True)

    windows = make_windows(dates, opt.train_days, opt.val_days, opt.test_days, opt.window_step)
    if not windows:
        raise RuntimeError("Not enough data for even one train/val/test window.")
    print(f"Universe: {len(universe)} symbols; data {dates[0].date()} -> {dates[-1].date()}; "
          f"{len(windows)} rolling windows; max allocation day = {max_day}", flush=True)

    cfg = config_fingerprint(params, opt.data_version)
    cache = EvaluationCache(opt.cache_path)

    def make_eval(win):
        start = str(win[0].date())
        end = str(win[1].date())
        return lambda c: evaluate_candidate(c, prices, params, dates, (start, end), cache, cfg,
                                            max_allocation_day=max_day)

    train_eval = make_eval(windows[0]["train"])
    train_obj_eval = lambda c: objectives(train_eval(c))

    val_window_dicts = [{"val": w["val"]} for w in windows]
    min_val_windows = len(val_window_dicts) if opt.require_full_coverage else None

    def robust_eval_fn(cc, w):
        ww = w["val"]
        return evaluate_candidate(cc, prices, params, dates,
                                  (str(ww[0].date()), str(ww[1].date())), cache, cfg,
                                  max_allocation_day=max_day)

    def robust_of(cc):
        return evaluate_robust(cc, robust_eval_fn, val_window_dicts, lamb=opt.lamb,
                               min_windows=min_val_windows)

    # ---------- 1) random baseline ----------
    print(f"Random baseline: {opt.n_random} candidates on TRAIN window...", flush=True)
    baseline = random_search(opt.n_random, universe_sorted, rng, opt.min_gap, max_day, train_eval,
                             progress=progress, fixed_symbols=list(fixed) if fixed else None)

    # ---------- 2) NSGA-II ----------
    print(f"NSGA-II: pop={opt.population_size} gen={opt.generations} on TRAIN window...", flush=True)
    init_pop = [b["candidate"] for b in baseline[: opt.population_size]]
    while len(init_pop) < opt.population_size:
        c = random_candidate(rng, universe_sorted, opt.min_gap, max_day, list(fixed) if fixed else None)
        if c.key() not in {x.key() for x in init_pop}:
            init_pop.append(c)
    pop, fit, _ = nsga2(
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
        fixed_symbols=list(fixed) if fixed else None,
    )

    # ---------- 3) surrogate-guided additions (optional) ----------
    if opt.use_surrogate and len(baseline) >= 50:
        print("Training surrogate and proposing candidates...", flush=True)
        surf = Surrogate(universe_sorted, seed=opt.seed)
        surf.fit([b["candidate"] for b in baseline],
                 [b["metrics"]["net_twr_annualized_pct"] for b in baseline])
        proposed = surf.rank(init_pop + pop)
        for c in proposed[: opt.n_finalists]:
            if c.key() not in {x.key() for x in init_pop + pop}:
                m = train_eval(c)
                if m and not m.get("error"):
                    pop.append(c)

    # ---------- 4) assemble evaluation pool ----------
    pool = [b["candidate"] for b in baseline]
    seen = {c.key() for c in pool}
    for c in pop:
        if c.key() not in seen:
            seen.add(c.key())
            pool.append(c)

    # ---------- 5) walk-forward robust fitness on VALIDATION windows ----------
    print(f"Walk-forward robust evaluation: {len(pool)} candidates x {len(windows)} val windows "
          f"(coverage policy: {'100% required' if opt.require_full_coverage else 'best effort'})...", flush=True)
    all_items = []
    for idx, c in enumerate(pool):
        m = train_eval(c)
        robust = robust_of(c)
        item = {"candidate": c, "metrics": m, "robust": robust, "objectives": objectives(m)}
        item["train_metrics"] = m
        item["validation_metrics"] = robust
        all_items.append(item)
        if progress and (idx + 1) % 50 == 0:
            rr = (robust or {}).get("robust_return")
            print(f"  robust eval {idx+1}/{len(pool)} {c} robust_return={rr}", flush=True)

    # ---------- 6) finalists: robustness + concentration + FINAL TEST ----------
    by_robust = sorted([i for i in all_items if i["robust"]],
                       key=lambda i: -i["robust"]["robust_return"])
    finalists = by_robust[: opt.n_finalists]
    test_windows = [{"test": w["test"]} for w in windows]

    def full_test_eval(cc):
        res = [
            evaluate_candidate(cc, prices, params, dates,
                               (str(w[0].date()), str(w[1].date())), cache, cfg,
                               max_allocation_day=max_day)
            for w in [tw["test"] for tw in test_windows]
        ]
        ok = [r for r in res if r and not r.get("error")]
        return {
            "median_net_twr": median([r["net_twr_annualized_pct"] for r in ok]) if ok else None,
            "n_test_windows": len(ok),
            "required_test_windows": len(test_windows),
            "valid": len(ok) == len(test_windows),
            "per_window": res,
        }

    for item in finalists:
        c = item["candidate"]
        # Timing robustness measured from OOS (validation) robust scores.
        item["timing_robust"] = timing_neighbourhood(c, robust_of, radius=5, min_gap=opt.min_gap,
                                                     max_day=max_day, value_key="robust_return")
        if fixed is None:
            item["symbol_robust"] = symbol_neighbourhood(c, universe_sorted, train_eval, rng)
        else:
            item["symbol_robust"] = {"n_neighbours": 0, "mean": None, "median": None, "std": None,
                                     "note": "symbols fixed in timing mode"}
        item["concentration"] = concentration(item["metrics"])
        item["test"] = full_test_eval(c)
        item["test_metrics"] = item["test"]

    # Leaderboard winners that are not finalists still get a FINAL TEST block, so no
    # leaderboard ever reports "0/0 windows".
    for name, item in leaderboards(all_items).items():
        if "test" not in item:
            item["test"] = full_test_eval(item["candidate"])
            item["test_metrics"] = item["test"]

    # ---------- 6b) quarterly baseline (same symbols, standard schedule) ----------
    baseline_items = {}
    for item in finalists:
        c = item["candidate"]
        bc = Candidate(c.symbols, baseline_days)
        baseline_items[c.key()] = {"candidate": bc, "train": train_eval(bc),
                                   "robust": robust_of(bc), "test": full_test_eval(bc)}

    # ---------- 7) leaderboards + pareto + exports ----------
    winners = leaderboards(all_items)
    pareto = pareto_frontier(all_items)
    meta = {
        "experiment_id": experiment_id,
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "seed": opt.seed,
        "data_version": opt.data_version,
        "mode": opt.mode,
        "fixed_symbols": list(fixed) if fixed else None,
        "universe": universe_sorted,
        "universe_variant": params.universe,
        "data_start": str(dates[0].date()),
        "data_end": str(dates[-1].date()),
        "max_allocation_day": max_day,
        "baseline_allocation_days": list(baseline_days),
        "n_windows": len(windows),
        "windows": [{"train": (str(w["train"][0].date()), str(w["train"][1].date())),
                     "val": (str(w["val"][0].date()), str(w["val"][1].date())),
                     "test": (str(w["test"][0].date()), str(w["test"][1].date()))} for w in windows],
        "erc_config": {k: getattr(params, k) for k in
                       ["annualization_factor", "minimum_observations", "lookback_days",
                        "normal_band", "soft_band", "allocation_frequency"]},
        "cost_config": {k: getattr(params, k) for k in
                        ["fee_buy_bps", "fee_sell_bps", "tax_sell_bps", "slippage_bps", "execution_lag"]},
        "optimizer_config": opt.as_dict(),
    }

    out_dir = os.path.join(opt.out_dir, experiment_id)
    window_rows = []
    for i, item in enumerate(by_robust[:20]):
        row = {"rank": i + 1, "symbols": " ".join(item["candidate"].symbols),
               "allocation_days": list(item["candidate"].allocation_days),
               "train_metrics": item["metrics"], "validation_metrics": item["robust"]}
        window_rows.append(row)
    timing_rows = [{"symbols": " ".join(i["candidate"].symbols),
                    **{k: v for k, v in i.get("timing_robust", {}).items() if k != "neighbours"}}
                   for i in finalists]
    symbol_rows = [{"symbols": " ".join(i["candidate"].symbols),
                    **{k: v for k, v in i.get("symbol_robust", {}).items() if k != "results"}}
                   for i in finalists]

    write_exports(out_dir, meta, all_items, winners, pareto, window_rows, timing_rows, symbol_rows)
    write_baseline_comparison(out_dir, finalists, baseline_items, baseline_days, winners)
    for name, item in winners.items():
        final_report(item, out_dir, name)
    write_experiment_json(out_dir, meta, winners, pareto, by_robust[:50], finalists, baseline_items, baseline_days)
    _write_recommendation(out_dir, meta, winners)

    print(f"\nOptimizer done in {time.time()-t0:.1f}s. Experiment {experiment_id}")
    print(f"Exports -> {out_dir}")
    return {"experiment_id": experiment_id, "out_dir": out_dir, "items": all_items,
            "winners": winners, "pareto": pareto, "finalists": finalists, "meta": meta,
            "baseline": {"allocation_days": list(baseline_days),
                         "items": {k: v for k, v in baseline_items.items()}}}


def _write_recommendation(out_dir: str, meta: dict, winners: dict) -> str | None:
    """Write recommendation.json next to experiment.json (what to deploy next)."""
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