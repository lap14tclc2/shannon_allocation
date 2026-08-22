#!/usr/bin/env python3
"""Joint Portfolio + Allocation-Time Optimizer (NSGA-II + walk-forward robustness).

Searches symbol subsets (5..10) and exactly 4 annual allocation times TOGETHER,
ranks by robust out-of-sample risk-adjusted NET performance, and reports
leaderboards + Pareto frontier + finalist robustness reports.

Usage:
    python optimize_main.py                      # defaults (small quick run)
    python optimize_main.py --population 200 --generations 100 --random 1000
    python optimize_main.py --seed 7 --no-surrogate --finalists 10

Experiment metadata, CSVs and Markdown finalist reports are written under
results/optimizer/<experiment_id>/.
"""

from __future__ import annotations

import argparse

from backtest import BacktestParams
from backtest.optimize import run_optimizer, OptimizerConfig


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Joint portfolio + allocation-time optimizer")
    p.add_argument("--population", type=int, default=60, help="NSGA-II population size (spec default 200)")
    p.add_argument("--generations", type=int, default=30, help="NSGA-II generations (spec default 100)")
    p.add_argument("--random", type=int, default=400, help="random joint-search baseline candidates")
    p.add_argument("--finalists", type=int, default=5)
    p.add_argument("--seed", type=int, default=42)
    p.add_argument("--min-gap", type=int, default=40)
    p.add_argument("--max-day", type=int, default=252)
    p.add_argument("--lamb", type=float, default=0.5, help="robustness lambda (median - lamb*std)")
    p.add_argument("--no-surrogate", action="store_true")
    p.add_argument("--data-dir", default="F:/data_finance/data")
    p.add_argument("--out", default="F:/workspace/shannon_allocation/python/results/optimizer")
    p.add_argument("--no-progress", action="store_true")
    return p


def main() -> int:
    args = build_parser().parse_args()

    params = BacktestParams(
        data_dir=args.data_dir,
        fee_buy_bps=15.0,
        fee_sell_bps=15.0,
        tax_sell_bps=10.0,
        slippage_bps=5.0,
        execution_lag=1,
    )
    opt = OptimizerConfig(
        seed=args.seed,
        population_size=args.population,
        generations=args.generations,
        n_random=args.random,
        n_finalists=args.finalists,
        min_gap=args.min_gap,
        max_day=args.max_day,
        lamb=args.lamb,
        use_surrogate=not args.no_surrogate,
        out_dir=args.out,
    )

    result = run_optimizer(params, opt, progress=not args.no_progress)

    # Print the leaderboards.
    winners = result["winners"]
    print("\n================ LEADERBOARDS ================")
    for name, item in winners.items():
        m = item["metrics"]
        c = item["candidate"]
        robust = item.get("robust") or {}
        print(f"\n[{name}] {c}")
        print(f"  Net TWR ann {m.get('net_twr_annualized_pct', 0):.2f}% | XIRR {m.get('net_xirr_pct', 0):.2f}% "
              f"| Sharpe {m.get('sharpe', 0):.3f} | Sortino {m.get('sortino', 0):.3f} "
              f"| MDD {m.get('max_drawdown_pct', 0):.2f}% | Cost {m.get('cost_pct_of_nav', 0):.2f}%")
        if robust:
            print(f"  Robust: median OOS {robust.get('median_net_twr', 0):.2f}% | P10 {robust.get('p10_net_twr', 0):.2f}% "
                  f"| worst {robust.get('worst_net_twr', 0):.2f}% | robust_return {robust.get('robust_return', 0):.2f}")

    n_pareto = len(result["pareto"])
    print(f"\nPareto frontier size: {n_pareto}")
    print(f"Exports -> {result['out_dir']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())