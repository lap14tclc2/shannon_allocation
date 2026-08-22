"""Top-level joint optimizer: random baseline + NSGA-II + walk-forward robustness.

Discipline:
  - optimization evaluates candidates ONLY on TRAIN windows
  - ranking uses VALIDATION windows (robust fitness)
  - untouched TEST windows measure final out-of-sample performance
  - NET performance (after transaction costs) is used throughout
"""

from __future__ import annotations

import json
import os
import random
import time
from dataclasses import dataclass, field, asdict
from datetime import datetime
from statistics import median

from ..config import BacktestParams
from ..data import load_panel
from ..candidate import Candidate, assert_valid_candidate
from .evaluate import (
    EvaluationCache,
    config_fingerprint,
    evaluate_candidate,
    objectives,
    OBJECTIVE_NAMES,
)
from .nsga2 import nsga2
from .reports import leaderboards, pareto_frontier, final_report, write_exports, write_experiment_json
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
    max_day: int = 252
    lamb: float = 0.5
    n_finalists: int = 5
    train_days: int = 378          # ~1.5 years (optimization window)
    val_days: int = 252            # ~1 year (ranking / robust fitness window)
    test_days: int = 126           # ~0.5 year (untouched OOS evaluation)
    window_step: int = 120
    use_surrogate: bool = True
    data_version: str = "v1"
    cache_path: str = "F:/workspace/shannon_allocation/python/results/optimizer_cache.json"
    out_dir: str = "F:/workspace/shannon_allocation/python/results/optimizer"

    def as_dict(self) -> dict:
        return asdict(self)


def run_optimizer(params: BacktestParams, opt: OptimizerConfig, progress: bool = True):
    t0 = time.time()
    experiment_id = datetime.now().strftime("%Y%m%d_%H%M%S")
    rng = random.Random(opt.seed)

    prices, universe = load_panel(params)
    dates = list(prices.index)
    universe_sorted = sorted(universe)
    windows = make_windows(dates, opt.train_days, opt.val_days, opt.test_days, opt.window_step)
    if not windows:
        raise RuntimeError("Not enough data for even one train/val/test window.")
    print(f"Universe: {len(universe)} symbols; data {dates[0].date()} -> {dates[-1].date()}; "
          f"{len(windows)} rolling windows", flush=True)

    cfg = config_fingerprint(params, opt.data_version)
    cache = EvaluationCache(opt.cache_path)

    def make_eval(win):
        start = str(win[0].date())
        end = str(win[1].date())
        return lambda c: evaluate_candidate(c, prices, params, dates, (start, end), cache, cfg)

    train_eval = make_eval(windows[0]["train"])
    train_obj_eval = lambda c: objectives(train_eval(c))

    # ---------- 1) random joint-search baseline ----------
    print(f"Random baseline: {opt.n_random} candidates on TRAIN window...", flush=True)
    baseline = random_search(opt.n_random, universe_sorted, rng, opt.min_gap, opt.max_day, train_eval,
                             progress=progress)

    # ---------- 2) NSGA-II ----------
    print(f"NSGA-II: pop={opt.population_size} gen={opt.generations} on TRAIN window...", flush=True)
    init_pop = [b["candidate"] for b in baseline[: opt.population_size]]
    while len(init_pop) < opt.population_size:
        from ..candidate import random_candidate
        c = random_candidate(rng, universe_sorted, opt.min_gap, opt.max_day)
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
        max_day=opt.max_day,
        progress=progress,
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
    print(f"Walk-forward robust evaluation: {len(pool)} candidates x {len(windows)} val windows...", flush=True)
    val_window_dicts = [{"val": w["val"]} for w in windows]

    def robust_eval_fn(cc, w):
        ww = w["val"]
        return evaluate_candidate(cc, prices, params, dates,
                                  (str(ww[0].date()), str(ww[1].date())), cache, cfg)

    all_items = []
    for idx, c in enumerate(pool):
        m = train_eval(c)
        robust = evaluate_robust(c, robust_eval_fn, val_window_dicts, lamb=opt.lamb)
        item = {"candidate": c, "metrics": m, "robust": robust, "objectives": objectives(m)}
        all_items.append(item)
        if progress and (idx + 1) % 50 == 0:
            rr = (robust or {}).get("robust_return")
            print(f"  robust eval {idx+1}/{len(pool)} {c} robust_return={rr}", flush=True)

    # ---------- 6) finalists: timing/symbol robustness + concentration + TEST ----------
    by_robust = sorted([i for i in all_items if i["robust"]],
                       key=lambda i: -i["robust"]["robust_return"])
    finalists = by_robust[: opt.n_finalists]
    test_windows = [{"test": w["test"]} for w in windows]
    for item in finalists:
        c = item["candidate"]
        item["timing_robust"] = timing_neighbourhood(c, train_eval, min_gap=opt.min_gap, max_day=opt.max_day)
        item["symbol_robust"] = symbol_neighbourhood(c, universe_sorted, train_eval, rng)
        item["concentration"] = concentration(item["metrics"])
        test_res = [
            evaluate_candidate(c, prices, params, dates,
                               (str(w[0].date()), str(w[1].date())), cache, cfg)
            for w in [tw["test"] for tw in test_windows]
        ]
        ok = [r["net_twr_annualized_pct"] for r in test_res if r and not r.get("error")]
        item["test"] = {
            "median_net_twr": median(ok) if ok else None,
            "n_test_windows": len(ok),
            "per_window": test_res,
        }

    # ---------- 7) leaderboards + pareto + exports ----------
    winners = leaderboards(all_items)
    pareto = pareto_frontier(all_items)
    meta = {
        "experiment_id": experiment_id,
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "seed": opt.seed,
        "data_version": opt.data_version,
        "universe": universe_sorted,
        "data_start": str(dates[0].date()),
        "data_end": str(dates[-1].date()),
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
               "metrics": item["metrics"], "robust": item["robust"]}
        window_rows.append(row)
    timing_rows = [{"symbols": " ".join(i["candidate"].symbols),
                    **{k: v for k, v in i.get("timing_robust", {}).items() if k != "neighbours"}}
                   for i in finalists]
    symbol_rows = [{"symbols": " ".join(i["candidate"].symbols),
                    **{k: v for k, v in i.get("symbol_robust", {}).items() if k != "results"}}
                   for i in finalists]

    write_exports(out_dir, meta, all_items, winners, pareto, window_rows, timing_rows, symbol_rows)
    for name, item in winners.items():
        final_report(item, out_dir, name)
    write_experiment_json(out_dir, meta, winners, pareto, by_robust[:50], finalists)

    print(f"\nOptimizer done in {time.time()-t0:.1f}s. Experiment {experiment_id}")
    print(f"Exports -> {out_dir}")
    return {"experiment_id": experiment_id, "out_dir": out_dir, "items": all_items,
            "winners": winners, "pareto": pareto, "finalists": finalists, "meta": meta}