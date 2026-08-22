#!/usr/bin/env python3
"""Portfolio + Allocation-Time Optimizer (NSGA-II + walk-forward robustness).

Two modes:
  joint  (default)  searches symbol subsets (5..10) and 4 annual allocation times
                    together.
  timing            fixes a portfolio set (--fixed-symbols) and optimizes ONLY the
                    four allocation times [T1,T2,T3,T4] against it.

Evaluation methodology (audit):
  - walk-forward train/val/test windows, val/test >= 252 trading days
  - ~lookback_days of pre-window history warms up ERC (no look-ahead)
  - performance clock starts at the WINDOW START (cash included)
  - 100% window coverage required (a candidate that fails any val/test window is INVALID)
  - cyclic minimum gap (year-end to next year's T1) is enforced
  - max allocation day is resolved against the real trading calendar
  - a quarterly baseline is evaluated on the same symbols for comparison

Usage:
    python optimize_main.py                      # defaults (small quick run)
    python optimize_main.py --population 200 --generations 100 --random 1000
    python optimize_main.py --mode timing --fixed-symbols CTG,GVR,HDB,LPB,MWG,STB,VIB
    python optimize_main.py --seed 7 --no-surrogate --finalists 10

Experiment metadata, CSVs and Markdown finalist reports are written under
results/optimizer/<experiment_id>/.
"""

from __future__ import annotations

import argparse

from backtest import BacktestParams
from backtest.optimize import run_optimizer, OptimizerConfig


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Portfolio + allocation-time optimizer")
    p.add_argument("--mode", choices=["joint", "timing"], default="joint",
                   help="'joint' searches symbols+timing; 'timing' optimizes only [T1..T4] "
                        "against a FIXED portfolio set (--fixed-symbols)")
    p.add_argument("--fixed-symbols", type=str, default=None,
                   help="comma-separated tickers to freeze as the portfolio (required for --mode timing)")
    p.add_argument("--population", type=int, default=60, help="NSGA-II population size (spec default 200)")
    p.add_argument("--generations", type=int, default=30, help="NSGA-II generations (spec default 100)")
    p.add_argument("--random", type=int, default=400, help="random joint-search baseline candidates")
    p.add_argument("--finalists", type=int, default=5)
    p.add_argument("--seed", type=int, default=42)
    p.add_argument("--min-gap", type=int, default=40)
    p.add_argument("--max-day", type=int, default=None,
                   help="override max allocation day (default: resolved from the actual trading calendar)")
    p.add_argument("--lamb", type=float, default=0.5, help="robustness lambda (median - lamb*std)")
    p.add_argument("--no-surrogate", action="store_true")
    p.add_argument("--test-days", type=int, default=252, help="length of untouched OOS test windows")
    p.add_argument("--no-full-coverage", action="store_true",
                   help="allow candidates that fail some validation/test windows (default: require 100%)")
    p.add_argument("--universe", choices=["all", "vn30", "vn50", "vn100"], default="all",
                   help="restrict the candidate symbol universe to an index variant")
    p.add_argument("--data-dir", default="F:/data_finance/data")
    p.add_argument("--out", default="F:/workspace/shannon_allocation/python/results/optimizer")
    p.add_argument("--no-progress", action="store_true")
    return p


def main() -> int:
    args = build_parser().parse_args()

    fixed_symbols = None
    if args.fixed_symbols:
        fixed_symbols = [s.strip().upper() for s in args.fixed_symbols.split(",") if s.strip()]

    params = BacktestParams(
        data_dir=args.data_dir,
        universe=args.universe,
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
        mode=args.mode,
        fixed_symbols=fixed_symbols,
        test_days=args.test_days,
        require_full_coverage=not args.no_full_coverage,
    )

    result = run_optimizer(params, opt, progress=not args.no_progress)

    # Print the leaderboards.
    winners = result["winners"]
    print("\n================ LEADERBOARDS ================")
    for name, item in winners.items():
        m = item["metrics"]
        c = item["candidate"]
        robust = item.get("robust") or {}
        test = item.get("test") or {}
        print(f"\n[{name}] {c}")
        print(f"  TRAIN: Net TWR ann {m.get('net_twr_annualized_pct', 0):.2f}% | XIRR {m.get('net_xirr_pct', 0):.2f}% "
              f"| Sharpe {m.get('sharpe', 0):.3f} | Sortino {m.get('sortino', 0):.3f} "
              f"| MDD {m.get('max_drawdown_pct', 0):.2f}% | Cost {m.get('cost_pct_of_nav', 0):.2f}%")
        if robust:
            print(f"  VALIDATION: median OOS {robust.get('median_net_twr', 0):.2f}% | P10 {robust.get('p10_net_twr', 0):.2f}% "
                  f"| worst {robust.get('worst_net_twr', 0):.2f}% | robust_return {robust.get('robust_return', 0):.2f}")
        print(f"  FINAL TEST: {test.get('n_test_windows', 0)}/{test.get('required_test_windows', 0)} windows "
              f"{'PASS' if test.get('valid') else 'INVALID'} | median {test.get('median_net_twr', 0):.2f}%")

    n_pareto = len(result["pareto"])
    base = result.get("baseline") or {}
    if base:
        print(f"\nQuarterly baseline schedule: {base['allocation_days']}")
        print("Baseline vs optimized comparison -> baseline_comparison.csv in the experiment folder")
    print(f"\nPareto frontier size: {n_pareto}")
    print(f"Exports -> {result['out_dir']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())