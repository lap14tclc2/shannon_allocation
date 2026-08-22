#!/usr/bin/env python3
"""Rank random 5-10 symbol combinations using ERC + Shannon rebalancing.

Concept: starting from 200M VND (20M VND deposited each year), each random
symbol combination is allocated and managed with the same rules as the
reference portfolio_allocation system (ERC annual target + Shannon drift
bands + sell-to-buy/cash funding). Combinations are ranked by money growth.

Examples:
    python main.py --combos 50
    python main.py --combos 200 --seed 7 --fractional --rebalance 1
    python main.py --combos 100 --integer-shares --out results/ranking.csv
"""

from __future__ import annotations

import argparse
import os

from backtest import BacktestParams, load_panel, generate_combinations, run_combinations, ranking_rows


def _print_pctiles(summary: dict, rows) -> None:
    print(f"{'Metric':<24}{'P10':>10}{'P25':>10}{'MEDIAN':>10}{'P75':>10}{'P90':>10}")
    print("-" * 74)
    labels = {
        "final_nav": "Final NAV (VND)",
        "twr_annualized_pct": "TWR annualized %",
        "xirr_pct": "XIRR %",
        "sharpe": "Sharpe",
        "sortino": "Sortino",
        "max_drawdown_pct": "Max drawdown %",
        "score": "Portfolio score",
    }
    for key, label in labels.items():
        p = summary.get(key)
        if not p:
            continue
        if key in ("final_nav",):
            cells = [f"{p[f'p{int(q)}']:,.0f}" for q in (10, 25, 50, 75, 90)]
            width = 16
        else:
            cells = [f"{p[f'p{int(q)}']:.2f}" for q in (10, 25, 50, 75, 90)]
            width = 10
        print(f"{label:<24}" + "".join(f"{c:>{width}}" for c in cells))
    print()


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Shannon/ERC combination ranking backtest")
    p.add_argument("--data-dir", default="F:/data_finance/data", help="folder with <TICKER>.csv files")
    p.add_argument("--universe", choices=["all", "vn30", "vn50", "vn100"], default="all",
                   help="filter symbols to an index universe (vn100 = every symbol in the data folder)")
    p.add_argument("--combos", type=int, default=50, help="number of random combinations")
    p.add_argument("--min-symbols", type=int, default=5)
    p.add_argument("--max-symbols", type=int, default=10)
    p.add_argument("--seed", type=int, default=42)
    p.add_argument("--initial-balance", type=float, default=200_000_000, help="starting cash (VND)")
    p.add_argument("--annual-deposit", type=float, default=20_000_000, help="yearly deposit (VND)")
    p.add_argument("--no-deposit", action="store_true", help="disable annual deposits")
    p.add_argument("--lookback", type=int, default=252, help="ERC calibration trailing trading days")
    p.add_argument("--min-obs", type=int, default=60, help="minimum aligned observations for ERC")
    p.add_argument("--allocation-freq", choices=["quarterly", "annual"], default="quarterly",
                   help="how often to recompute ERC targets (default quarterly)")
    p.add_argument("--normal-band", type=float, default=0.10)
    p.add_argument("--soft-band", type=float, default=0.20)
    p.add_argument("--fractional", action="store_true", help="allow fractional shares (default)")
    p.add_argument("--integer-shares", action="store_true", help="round down to whole shares")
    p.add_argument("--rebalance", type=int, default=1, help="band check every N trading days (1=daily)")
    p.add_argument("--start-date", default=None, help="YYYY-MM-DD (optional sim window)")
    p.add_argument("--end-date", default=None, help="YYYY-MM-DD (optional sim window)")
    p.add_argument("--out", default="F:/workspace/shannon_allocation/python/results/ranking.csv",
                   help="ranking CSV output path")
    p.add_argument("--top", type=int, default=20, help="rows to print")
    p.add_argument("--run-id", default=None, help="explicit run id for saved artifacts")
    p.add_argument("--no-save", action="store_true", help="skip persisting run artifacts")
    p.add_argument("--plot", action="store_true", help="save equity curve chart of top combinations")
    p.add_argument("--plot-top", type=int, default=10, help="number of top combos to plot")
    p.add_argument("--chart-out", default="F:/workspace/shannon_allocation/python/results/top_equity.png",
                   help="chart PNG output path")
    p.add_argument("--save-nav", default=None, help="save all nav histories to a JSON file")
    p.add_argument("--no-progress", action="store_true", help="hide per-combination progress")
    return p


def main() -> None:
    args = build_parser().parse_args()

    params = BacktestParams(
        data_dir=args.data_dir,
        universe=args.universe,
        num_combinations=args.combos,
        min_symbols=args.min_symbols,
        max_symbols=args.max_symbols,
        seed=args.seed,
        initial_balance=args.initial_balance,
        annual_deposit=0 if args.no_deposit else args.annual_deposit,
        lookback_days=args.lookback,
        minimum_observations=args.min_obs,
        allocation_frequency=args.allocation_freq,
        normal_band=args.normal_band,
        soft_band=args.soft_band,
        fractional_shares=not args.integer_shares,
        rebalance_every_days=args.rebalance,
        start_date=args.start_date,
        end_date=args.end_date,
        output_dir=os.path.dirname(args.out) or ".",
        top_n=args.top,
    )

    print("Loading price panel...", flush=True)
    prices, symbols = load_panel(params)
    print(f"Loaded {len(symbols)} symbols, {prices.index.min().date()} -> {prices.index.max().date()} "
          f"({len(prices)} trading days)", flush=True)

    print(f"Generating {params.num_combinations} random combinations "
          f"({params.min_symbols}-{params.max_symbols} symbols, seed={params.seed})...", flush=True)
    combos = generate_combinations(symbols, params)
    print(f"Generated {len(combos)} unique combinations.", flush=True)

    print(f"Running backtests (start {params.initial_balance:,.0f} VND, "
          f"deposit {params.annual_deposit:,.0f} VND/year, "
          f"allocation {params.allocation_frequency})...", flush=True)
    results = run_combinations(combos, prices, params, progress=not args.no_progress)

    run_dir = None
    if not args.no_save:
        from backtest.persist import save_run
        run_dir = save_run(params, results, params.output_dir, run_id=args.run_id)
        print(f"Run artifacts saved -> {run_dir}", flush=True)

    rows = [r for r in ranking_rows(results) if not r["error"]]
    failed = [r for r in ranking_rows(results) if r["error"]]
    rows.sort(key=lambda r: r["score"], reverse=True)
    for i, r in enumerate(rows, 1):
        r["rank"] = i

    print("\n" + "=" * 150)
    print("RANKING BOARD — random combinations ranked by composite Portfolio Score (0-100)")
    print("Score = return quality + Sharpe + drawdown control + year consistency")
    print("=" * 150)
    header = ("{:<6}{:<28}{:>3}{:>6}{:>7}{:>10}{:>10}{:>8}{:>9}{:>8}{:>8}{:>14}".format(
        "RANK", "SYMBOLS", "N", "ALC", "SCORE", "TWR_ANN%", "XIRR%", "SHARPE", "SORTINO", "MDD%", "VOL%", "FINAL_NAV"))
    print(header)
    print("-" * 150)
    for r in rows[: params.top_n]:
        print("{:<6}{:<28}{:>3}{:>6}{:>7.1f}{:>10.2f}{:>10.2f}{:>8.3f}{:>9.3f}{:>8.2f}{:>8.2f}{:>14,.0f}".format(
            r["rank"], r["symbols"][:28], r["n_symbols"], r["n_allocations"], r["score"],
            r["twr_annualized_pct"], r["xirr_pct"], r["sharpe"], r["sortino"],
            r["max_drawdown_pct"], r["ann_volatility_pct"], r["final_nav"]))
    if len(rows) > params.top_n:
        print(f"  ... {len(rows) - params.top_n} more combinations (full table saved to {args.out})")
    if failed:
        print(f"\n{len(failed)} combinations skipped (insufficient aligned history):")
        for f in failed:
            print(f"  - {f['symbols']}: {f['error']}")

    # Aggregate / robustness statistics across all combinations.
    from backtest.runner import aggregate_stats
    stats = aggregate_stats(results)
    print("\n" + "=" * 150)
    print("AGGREGATE STATISTICS (%d random portfolios)" % stats["n_success"])
    print("=" * 150)
    _print_pctiles(stats["summary"], rows)

    print("\nBy portfolio size (N symbols):")
    print("{:<8}{:>8}{:>14}{:>12}{:>12}{:>10}{:>10}".format("N", "COUNT", "AVG TWR_ANN%", "AVG SHARPE", "AVG SORTINO", "AVG MDD%", "AVG SCORE"))
    for n, s in sorted(stats["by_n"].items(), key=lambda kv: int(kv[0])):
        print("{:<8}{:>8}{:>14.2f}{:>12.3f}{:>12.3f}{:>10.2f}{:>10.2f}".format(
            n, s["count"], s["avg_cagr_pct"], s["avg_sharpe"], s["avg_sortino"], s["avg_mdd_pct"], s["avg_score"]))

    os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)
    import csv
    with open(args.out, "w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=list(rows[0].keys()) if rows else list(ranking_rows(results)[0].keys()))
        writer.writeheader()
        writer.writerows(rows + failed)
    print(f"\nSaved full ranking -> {args.out}")

    best = rows[0] if rows else None
    if best:
        print(f"\nBest by score: rank #{best['rank']} {best['symbols']} "
              f"-> score {best['score']}, final NAV {best['final_nav']:,.0f} VND, "
              f"TWR annualized {best['twr_annualized_pct']:+.2f}%, MDD {best['max_drawdown_pct']:.2f}%")

    if args.save_nav:
        import json
        payload = [
            {"symbols": " ".join(r.symbols), "nav_history": [[d, v] for d, v in r.nav_history]}
            for r in results
        ]
        with open(args.save_nav, "w", encoding="utf-8") as fh:
            json.dump(payload, fh)
        print(f"Saved nav histories -> {args.save_nav}")

    if args.plot and rows:
        from backtest.plot import plot_top_equity_curves
        best_results = [r for r in results if not r.error]
        plot_top_equity_curves(best_results, args.chart_out, top_n=args.plot_top)


if __name__ == "__main__":
    main()