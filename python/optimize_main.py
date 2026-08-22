#!/usr/bin/env python3
"""Portfolio + Allocation-Time Optimizer (risk-aware NSGA-II + walk-forward robustness).

Examples:
    python optimize_main.py --portfolio-size 7 --universe vn100
    python optimize_main.py --portfolio-size 6 --risk-overlay --target-vol 0.18
    python optimize_main.py --portfolio-size 8 --preselect-top 45 --robust-pool 180
    python optimize_main.py --mode timing --fixed-symbols CTG,GVR,HDB,LPB,MWG,STB,VIB
"""

from __future__ import annotations

import argparse

from backtest import BacktestParams
from backtest.optimize import run_optimizer, OptimizerConfig


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Risk-aware portfolio + allocation-time optimizer")
    p.add_argument("--mode", choices=["joint", "timing"], default="joint")
    p.add_argument("--fixed-symbols", type=str, default=None,
                   help="comma-separated tickers; required for --mode timing")
    p.add_argument("--portfolio-size", type=int, default=7,
                   help="exact number of symbols to search in joint mode (5..10)")

    p.add_argument("--population", type=int, default=60)
    p.add_argument("--generations", type=int, default=30)
    p.add_argument("--random", type=int, default=250,
                   help="real TRAIN backtests used as random baseline")
    p.add_argument("--finalists", type=int, default=5)
    p.add_argument("--seed", type=int, default=42)
    p.add_argument("--min-gap", type=int, default=40)
    p.add_argument("--max-day", type=int, default=None)
    p.add_argument("--lamb", type=float, default=0.5)
    p.add_argument("--no-surrogate", action="store_true")
    p.add_argument("--preselect-top", type=int, default=45,
                   help="TRAIN-only symbol pre-screen size; 0 disables narrowing")
    p.add_argument("--robust-pool", type=int, default=180,
                   help="max diverse TRAIN candidates receiving expensive validation")
    p.add_argument("--surrogate-pool", type=int, default=5000,
                   help="cheap unevaluated candidates ranked by surrogate")
    p.add_argument("--surrogate-proposals", type=int, default=40,
                   help="surrogate-ranked candidates promoted to real TRAIN backtests")
    p.add_argument("--early-stop", type=int, default=15,
                   help="stop NSGA-II after Pareto front is unchanged for N generations; 0 disables")

    p.add_argument("--risk-overlay", action=argparse.BooleanOptionalAction, default=True,
                   help="enable absolute volatility targeting (default: enabled for optimizer)")
    p.add_argument("--target-vol", type=float, default=0.18,
                   help="annualized target portfolio volatility, e.g. 0.18 = 18%%")
    p.add_argument("--risk-fast-lookback", type=int, default=63)
    p.add_argument("--risk-slow-lookback", type=int, default=252)
    p.add_argument("--min-equity-exposure", type=float, default=0.25)
    p.add_argument("--max-position-weight", type=float, default=0.30)
    p.add_argument("--max-oos-drawdown", type=float, default=35.0,
                   help="hard validation/test MDD ceiling in absolute percent; 0 disables")

    p.add_argument("--test-days", type=int, default=252)
    p.add_argument("--no-full-coverage", action="store_true")
    p.add_argument("--universe", choices=["all", "vn30", "vn50", "vn100"], default="all")
    p.add_argument("--data-dir", default="F:/data_finance/data")
    p.add_argument("--out", default="F:/workspace/shannon_allocation/python/results/optimizer")
    p.add_argument("--no-progress", action="store_true")
    return p


def main() -> int:
    args = build_parser().parse_args()

    fixed_symbols = None
    if args.fixed_symbols:
        fixed_symbols = [s.strip().upper() for s in args.fixed_symbols.split(",") if s.strip()]

    portfolio_size = None if args.mode == "timing" else args.portfolio_size
    params = BacktestParams(
        data_dir=args.data_dir,
        universe=args.universe,
        fee_buy_bps=15.0,
        fee_sell_bps=15.0,
        tax_sell_bps=10.0,
        slippage_bps=5.0,
        execution_lag=1,
        risk_overlay_enabled=args.risk_overlay,
        target_volatility=args.target_vol,
        risk_fast_lookback=args.risk_fast_lookback,
        risk_slow_lookback=args.risk_slow_lookback,
        min_equity_exposure=args.min_equity_exposure,
        max_position_weight=args.max_position_weight if args.max_position_weight > 0 else None,
        portfolio_size=portfolio_size,
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
        portfolio_size=portfolio_size,
        test_days=args.test_days,
        require_full_coverage=not args.no_full_coverage,
        preselect_top=args.preselect_top if args.preselect_top > 0 else None,
        robust_pool_size=max(args.finalists, args.robust_pool),
        surrogate_pool_size=max(0, args.surrogate_pool),
        surrogate_proposals=max(0, args.surrogate_proposals),
        early_stop_generations=args.early_stop if args.early_stop > 0 else None,
        max_oos_drawdown_pct=args.max_oos_drawdown if args.max_oos_drawdown > 0 else None,
    )

    result = run_optimizer(params, opt, progress=not args.no_progress)

    winners = result["winners"]
    print("\n================ LEADERBOARDS ================")
    for name, item in winners.items():
        m = item["metrics"]
        c = item["candidate"]
        robust = item.get("robust") or {}
        test = item.get("test") or {}
        print(f"\n[{name}] {c}")
        print(
            f"  TRAIN: Net TWR ann {m.get('net_twr_annualized_pct', 0):.2f}% | "
            f"Sharpe {m.get('sharpe', 0):.3f} | MDD {m.get('max_drawdown_pct', 0):.2f}% | "
            f"CDaR95 {m.get('cdar95_pct', 0):.2f}% | avg exposure {m.get('avg_equity_exposure', 1):.2f}"
        )
        if robust:
            print(
                f"  VALIDATION: median {robust.get('median_net_twr', 0):.2f}% | "
                f"P10 {robust.get('p10_net_twr', 0):.2f}% | worst MDD {robust.get('worst_mdd', 0):.2f}% | "
                f"robust_return {robust.get('robust_return', 0):.2f}"
            )
        print(
            f"  FINAL TEST: {test.get('n_test_windows', 0)}/{test.get('required_test_windows', 0)} "
            f"{'PASS' if test.get('valid') else 'INVALID'} | median {test.get('median_net_twr', 0) or 0:.2f}% | "
            f"worst MDD {test.get('worst_mdd', 0) or 0:.2f}%"
        )

    base = result.get("baseline") or {}
    if base:
        print(f"\nQuarterly baseline schedule: {base['allocation_days']}")
    print(f"Pareto frontier size: {len(result['pareto'])}")
    print(f"Exports -> {result['out_dir']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
