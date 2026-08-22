#!/usr/bin/env python3
"""Rank random ERC/Shannon combinations with optional absolute-risk overlay."""

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
        "cdar95_pct": "CDaR95 %",
        "score": "Portfolio score",
    }
    for key, label in labels.items():
        p = summary.get(key)
        if not p:
            continue
        if key == "final_nav":
            cells = [f"{p[f'p{int(q)}']:,.0f}" for q in (10, 25, 50, 75, 90)]
            width = 16
        else:
            cells = [f"{p[f'p{int(q)}']:.2f}" for q in (10, 25, 50, 75, 90)]
            width = 10
        print(f"{label:<24}" + "".join(f"{c:>{width}}" for c in cells))
    print()


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Shannon/ERC combination ranking backtest")
    p.add_argument("--data-dir", default="F:/data_finance/data")
    p.add_argument("--universe", choices=["all", "vn30", "vn50", "vn100"], default="all")
    p.add_argument("--combos", type=int, default=50)
    p.add_argument("--portfolio-size", type=int, default=None,
                   help="exact number of symbols; overrides --min-symbols/--max-symbols")
    p.add_argument("--min-symbols", type=int, default=5)
    p.add_argument("--max-symbols", type=int, default=10)
    p.add_argument("--seed", type=int, default=42)
    p.add_argument("--initial-balance", type=float, default=200_000_000)
    p.add_argument("--annual-deposit", type=float, default=20_000_000)
    p.add_argument("--no-deposit", action="store_true")
    p.add_argument("--lookback", type=int, default=252)
    p.add_argument("--min-obs", type=int, default=60)
    p.add_argument("--allocation-freq", choices=["quarterly", "annual"], default="quarterly")
    p.add_argument("--normal-band", type=float, default=0.10)
    p.add_argument("--soft-band", type=float, default=0.20)
    p.add_argument("--integer-shares", action="store_true")
    p.add_argument("--rebalance", type=int, default=1)

    p.add_argument("--risk-overlay", action=argparse.BooleanOptionalAction, default=False,
                   help="volatility-target total equity exposure; baseline default is disabled")
    p.add_argument("--target-vol", type=float, default=0.18)
    p.add_argument("--risk-fast-lookback", type=int, default=63)
    p.add_argument("--risk-slow-lookback", type=int, default=252)
    p.add_argument("--min-equity-exposure", type=float, default=0.25)
    p.add_argument("--max-position-weight", type=float, default=0.30)

    p.add_argument("--start-date", default=None)
    p.add_argument("--end-date", default=None)
    p.add_argument("--out", default="F:/workspace/shannon_allocation/python/results/ranking.csv")
    p.add_argument("--top", type=int, default=20)
    p.add_argument("--run-id", default=None)
    p.add_argument("--no-save", action="store_true")
    p.add_argument("--plot", action="store_true")
    p.add_argument("--plot-top", type=int, default=10)
    p.add_argument("--chart-out", default="F:/workspace/shannon_allocation/python/results/top_equity.png")
    p.add_argument("--save-nav", default=None)
    p.add_argument("--no-progress", action="store_true")
    return p


def main() -> None:
    args = build_parser().parse_args()
    if args.portfolio_size is not None and not (1 <= args.portfolio_size <= 10):
        raise SystemExit("--portfolio-size must be between 1 and 10")

    params = BacktestParams(
        data_dir=args.data_dir,
        universe=args.universe,
        num_combinations=args.combos,
        min_symbols=args.min_symbols,
        max_symbols=args.max_symbols,
        portfolio_size=args.portfolio_size,
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
        risk_overlay_enabled=args.risk_overlay,
        target_volatility=args.target_vol,
        risk_fast_lookback=args.risk_fast_lookback,
        risk_slow_lookback=args.risk_slow_lookback,
        min_equity_exposure=args.min_equity_exposure,
        max_position_weight=args.max_position_weight if args.max_position_weight > 0 else None,
        start_date=args.start_date,
        end_date=args.end_date,
        output_dir=os.path.dirname(args.out) or ".",
        top_n=args.top,
    )

    print("Loading raw price panel...", flush=True)
    prices, symbols = load_panel(params)
    print(
        f"Loaded {len(symbols)} symbols, {prices.index.min().date()} -> {prices.index.max().date()} "
        f"({len(prices)} trading days)",
        flush=True,
    )

    size_desc = str(params.portfolio_size) if params.portfolio_size else f"{params.min_symbols}-{params.max_symbols}"
    print(
        f"Generating {params.num_combinations} random combinations ({size_desc} symbols, seed={params.seed})...",
        flush=True,
    )
    combos = generate_combinations(symbols, params)
    print(f"Generated {len(combos)} unique combinations.", flush=True)

    risk_desc = (
        f"vol-target {params.target_volatility:.0%}, fast/slow {params.risk_fast_lookback}/{params.risk_slow_lookback}"
        if params.risk_overlay_enabled else "OFF"
    )
    print(
        f"Running backtests (allocation {params.allocation_frequency}, risk overlay {risk_desc})...",
        flush=True,
    )
    results = run_combinations(combos, prices, params, progress=not args.no_progress)

    run_dir = None
    if not args.no_save:
        from backtest.persist import save_run
        run_dir = save_run(params, results, params.output_dir, run_id=args.run_id)
        print(f"Run artifacts saved -> {run_dir}", flush=True)

    all_rows = ranking_rows(results)
    rows = [r for r in all_rows if not r["error"]]
    failed = [r for r in all_rows if r["error"]]
    rows.sort(key=lambda r: r["score"], reverse=True)
    for i, r in enumerate(rows, 1):
        r["rank"] = i

    print("\n" + "=" * 166)
    print("RANKING BOARD — composite score with drawdown-tail quality")
    print("=" * 166)
    header = ("{:<6}{:<28}{:>3}{:>7}{:>10}{:>9}{:>9}{:>9}{:>9}{:>8}{:>8}{:>8}{:>14}".format(
        "RANK", "SYMBOLS", "N", "SCORE", "TWR_ANN%", "SHARPE", "SORTINO", "MDD%", "CDAR95%", "VOL%", "AVGEXP", "COST%", "FINAL_NAV"))
    print(header)
    print("-" * 166)
    for r in rows[: params.top_n]:
        print("{:<6}{:<28}{:>3}{:>7.1f}{:>10.2f}{:>9.3f}{:>9.3f}{:>9.2f}{:>9.2f}{:>8.2f}{:>8.2f}{:>8.2f}{:>14,.0f}".format(
            r["rank"], r["symbols"][:28], r["n_symbols"], r["score"],
            r["twr_annualized_pct"], r["sharpe"], r["sortino"],
            r["max_drawdown_pct"], r["cdar95_pct"], r["ann_volatility_pct"],
            r["avg_equity_exposure"], 0.0, r["final_nav"]))

    if failed:
        print(f"\n{len(failed)} combinations skipped:")
        for f in failed:
            print(f"  - {f['symbols']}: {f['error']}")

    from backtest.runner import aggregate_stats
    stats = aggregate_stats(results)
    print("\nAGGREGATE STATISTICS")
    _print_pctiles(stats["summary"], rows)

    os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)
    import csv
    fieldnames = list(rows[0].keys()) if rows else (list(all_rows[0].keys()) if all_rows else [])
    with open(args.out, "w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows + failed)
    print(f"Saved full ranking -> {args.out}")

    if args.save_nav:
        import json
        payload = [
            {"symbols": " ".join(r.symbols), "nav_history": [[d, v] for d, v in r.nav_history]}
            for r in results
        ]
        with open(args.save_nav, "w", encoding="utf-8") as fh:
            json.dump(payload, fh)

    if args.plot and rows:
        from backtest.plot import plot_top_equity_curves
        best_results = [r for r in results if not r.error]
        plot_top_equity_curves(best_results, args.chart_out, top_n=args.plot_top)


if __name__ == "__main__":
    main()
