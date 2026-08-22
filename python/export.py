#!/usr/bin/env python3
"""Export each combination's backtest data in an AI-readable format.

Reads the run artifacts under python/results/runs/<run_id>/ and writes a
per-combination Markdown report (allocation history, weights, trades, holdings),
a run-level overview, and an optional single consolidated Markdown / JSON file.

Usage:
    python export.py                      # export the most recent run (Markdown)
    python export.py --run <run_id>       # a specific run
    python export.py --all                # also write ALL_COMBINATIONS.md
    python export.py --format json        # consolidated JSON instead of Markdown
    python export.py --out <dir>          # output directory (default python/results/export)

Output layout (Markdown):
    <out>/<run_id>/
        _RUN.md                     ranking board + run params
        <SLUG>.md                   one report per combination
        ALL_COMBINATIONS.md         (with --all) everything concatenated
"""

from __future__ import annotations

import argparse
import io
import json
import os
import sys
import zipfile

RESULTS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "results")


def fmt_money(value):
    if value is None:
        return "-"
    try:
        return f"{float(value):,.0f}"
    except (TypeError, ValueError):
        return str(value)


def fmt_pct(value, digits=2):
    if value is None:
        return "-"
    try:
        return f"{float(value):.{digits}f}%"
    except (TypeError, ValueError):
        return str(value)


def fmt_w(value, digits=1):
    if value is None:
        return "-"
    try:
        return f"{float(value) * 100:.{digits}f}%"
    except (TypeError, ValueError):
        return str(value)


def fmt_shares(value):
    if value is None:
        return "-"
    try:
        return f"{float(value):,.0f}"
    except (TypeError, ValueError):
        return str(value)


# --------------------------------------------------------------------------- Markdown builders
def run_overview_md(run_id, meta, index):
    p = (meta or {}).get("params", {})
    lines = []
    lines.append(f"# Run {run_id}\n")
    lines.append(f"- Generated: {(meta or {}).get('generated_at', '-')}")
    lines.append(f"- Start balance: {fmt_money(p.get('initial_balance'))} VND")
    lines.append(f"- Annual deposit: {fmt_money(p.get('annual_deposit'))} VND")
    lines.append(f"- Allocation frequency: {p.get('allocation_frequency', '-')}")
    lines.append(f"- ERC lookback: {p.get('lookback_days', '-')} trading days")
    lines.append(f"- Symbols universe: {p.get('num_combinations', '-')} combinations, "
                 f"{p.get('min_symbols', '-')}-{p.get('max_symbols', '-')} symbols each")
    lines.append("")
    lines.append("## Ranking board (by composite Portfolio Score, 0-100)\n")
    lines.append("Score = return quality + Sharpe + drawdown control + year consistency\n")
    lines.append("| Rank | Symbols | N | Alloc | Score | TWR_ann% | XIRR% | Sharpe | Sortino | MDD% | Final NAV (VND) |")
    lines.append("|-----:|---------|--:|------:|------:|---------:|------:|-------:|--------:|-----:|----------------:|")
    combos = [c for c in (index or {}).get("combinations", []) if not c.get("error")]
    combos.sort(key=lambda c: c.get("rank", 999))
    for c in combos:
        lines.append(
            f"| {c.get('rank')} | {c.get('symbols','')} | {c.get('n_symbols')} | {c.get('n_allocations')} "
            f"| {c.get('score','')} | {fmt_pct(c.get('twr_annualized_pct'))} "
            f"| {fmt_pct(c.get('xirr_pct'))} | {c.get('sharpe','')} | {c.get('sortino','')} "
            f"| {fmt_pct(c.get('max_drawdown_pct'))} | {fmt_money(c.get('final_nav'))} |"
        )
    lines.append("")
    failed = [c for c in (index or {}).get("combinations", []) if c.get("error")]
    if failed:
        lines.append("## Skipped combinations\n")
        for c in failed:
            lines.append(f"- {c.get('symbols','')}: {c.get('error')}")
        lines.append("")
    return "\n".join(lines)


def stats_md(stats):
    """Render aggregate (cross-portfolio) statistics as Markdown."""
    s = stats or {}
    lines = ["# Aggregate statistics\n"]
    lines.append(f"- Portfolios: {s.get('n_success', 0)} of {s.get('n_total', 0)} succeeded\n")
    lines.append("## Distribution (P10 / P25 / median / P75 / P90)\n")
    labels = {
        "final_nav": ("Final NAV (VND)", "money"),
        "twr_annualized_pct": ("TWR annualized %", "pct"),
        "xirr_pct": ("XIRR %", "pct"),
        "sharpe": ("Sharpe", "num"),
        "sortino": ("Sortino", "num"),
        "max_drawdown_pct": ("Max drawdown %", "pct"),
        "score": ("Portfolio score", "num"),
    }
    lines.append("| Metric | P10 | P25 | Median | P75 | P90 |")
    lines.append("|--------|----:|----:|-------:|----:|----:|")
    for key, (label, kind) in labels.items():
        p = s.get("summary", {}).get(key)
        if not p:
            continue
        if kind == "money":
            cells = [fmt_money(p[f"p{q}"]) for q in (10, 25, 50, 75, 90)]
        elif kind == "pct":
            cells = [fmt_pct(p[f"p{q}"]) for q in (10, 25, 50, 75, 90)]
        else:
            cells = [f"{p[f'p{q}']:.2f}" for q in (10, 25, 50, 75, 90)]
        lines.append(f"| {label} | " + " | ".join(cells) + " |")
    lines.append("")
    lines.append("## By portfolio size (N symbols)\n")
    lines.append("| N | Count | Avg TWR_ann% | Avg Sharpe | Avg Sortino | Avg MDD% | Avg Score |")
    lines.append("|--:|------:|------------:|-----------:|------------:|---------:|----------:|")
    for n, b in sorted(s.get("by_n", {}).items(), key=lambda kv: int(kv[0])):
        lines.append(
            f"| {n} | {b['count']} | {fmt_pct(b['avg_cagr_pct'])} | {b['avg_sharpe']} "
            f"| {b['avg_sortino']} | {fmt_pct(b['avg_mdd_pct'])} | {b['avg_score']} |"
        )
    lines.append("")
    lines.append("## Per-symbol association (avg of portfolios containing each symbol)\n")
    lines.append("| Symbol | Appearances | Avg TWR_ann% | Avg Sharpe | Avg Score |")
    lines.append("|--------|------------:|------------:|-----------:|----------:|")
    for sym, d in s.get("per_symbol", {}).items():
        lines.append(
            f"| {sym} | {d['appearances']} | {fmt_pct(d['avg_twr_annualized_pct'])} "
            f"| {d['avg_sharpe']} | {d['avg_score']} |"
        )
    lines.append("")
    if s.get("top_by_score"):
        lines.append("## Top 10 by score\n")
        for i, syms in enumerate(s["top_by_score"], 1):
            lines.append(f"{i}. {', '.join(syms)}")
        lines.append("")
    return "\n".join(lines)


def holding_row(h):
    return f"| {h.get('symbol','')} | {fmt_shares(h.get('shares'))} | {fmt_money(h.get('price'))} " \
           f"| {fmt_money(h.get('value'))} | {fmt_w(h.get('weight'))} |"


def rec_row(r):
    return f"| {r.get('symbol','')} | {fmt_w(r.get('current_weight'))} | {fmt_w(r.get('target_weight'))} " \
           f"| {r.get('band','')} | {fmt_w(r.get('drift'))} | {r.get('recommendation','')} " \
           f"| {fmt_money(r.get('target_trade_amount'))} | {fmt_money(r.get('funded_trade_amount'))} " \
           f"| {fmt_shares(r.get('shares_to_trade'))} |"


def allocation_md(a):
    lines = []
    note = " (initial)" if a.get("initial_allocation") else ""
    dep = f", deposit {fmt_money(a.get('deposit_amount'))} VND" if a.get("deposit_amount") else ""
    lines.append(f"### Q{a.get('quarter')} {a.get('year')} — {a.get('allocation_date')}{note}{dep}")
    lines.append("")
    lines.append(f"- NAV before -> after: {fmt_money(a.get('nav_before'))} -> {fmt_money(a.get('nav_after'))} VND; "
                 f"cash after: {fmt_money(a.get('cash_after'))} VND; "
                 f"rebalances since last allocation: {a.get('rebalances_since_last_allocation')}")
    erc = a.get("erc") or {}
    lines.append(f"- ERC: {erc.get('observations','-')} obs, window {erc.get('window_start','-')} -> "
                 f"{erc.get('window_end','-')}, portfolio risk {fmt_w(erc.get('portfolio_risk'))}, "
                 f"erc error {erc.get('erc_error','-')}")
    if a.get("targets"):
        lines.append("- Target weights: " + ", ".join(
            f"{s} {fmt_w(w)}" for s, w in sorted(a["targets"].items())))
    recs = [r for r in (a.get("recommendations") or []) if r.get("recommendation") != "HOLD"]
    if recs:
        lines.append("")
        lines.append("| Symbol | Current | Target | Band | Drift | Rec | Target trade | Funded trade | Shares |")
        lines.append("|--------|--------:|-------:|------|------:|-----:|-------------:|-------------:|-------:|")
        for r in recs:
            lines.append(rec_row(r))
    holdings = a.get("holdings_after")
    if holdings:
        lines.append("")
        lines.append("Holdings after:")
        lines.append("| Symbol | Shares | Price | Value | Weight |")
        lines.append("|--------|-------:|------:|------:|-------:|")
        for h in holdings:
            lines.append(holding_row(h))
    lines.append("")
    return "\n".join(lines)


def combination_md(run_id, combo):
    lines = []
    symbols = " ".join(combo.get("symbols", []))
    lines.append(f"# Combination: {symbols}\n")
    lines.append(f"- Run: `{run_id}`")
    lines.append(f"- **Portfolio Score: {combo.get('score','-')} (0-100)**")
    lines.append(f"- Final NAV: {fmt_money(combo.get('final_nav'))} VND")
    lines.append(f"- Net contributed capital: {fmt_money(combo.get('total_deposits'))} VND")
    lines.append(f"- Absolute profit: {fmt_money(combo.get('absolute_profit'))} VND")
    lines.append(f"- Total return (NAV/deposits-1, informational): {fmt_pct(combo.get('total_return_pct'))}")
    lines.append(f"- **TWR (strategy, deposits removed): {fmt_pct(combo.get('twr_pct'))} total, "
                 f"{fmt_pct(combo.get('twr_annualized_pct'))} annualized**")
    lines.append(f"- **XIRR (investor money-weighted): {fmt_pct(combo.get('xirr_pct'))}**")
    lines.append(f"- CAGR (informational): {fmt_pct(combo.get('cagr_pct'))}")
    lines.append(f"- Annualized volatility: {fmt_pct(combo.get('annualized_volatility_pct'))}")
    lines.append(f"- Sharpe: {combo.get('sharpe','-')} | Sortino: {combo.get('sortino','-')} | Calmar: {combo.get('calmar','-')}")
    lines.append(f"- Max drawdown: {fmt_pct(combo.get('max_drawdown_pct'))}")
    lines.append(f"- First investment: {combo.get('first_allocation_date')} (warm-up excluded from metrics)")
    lines.append(f"- Turnover: {fmt_pct(combo.get('turnover_pct'),1)} | Trades: {combo.get('trade_count','-')}")
    lines.append(f"- Number of allocations: {len(combo.get('allocations') or [])}")
    annual = combo.get("annual_returns") or {}
    if annual:
        lines.append("- Annual returns (TWR): " + ", ".join(
            f"{y}: {fmt_pct(v)}" for y, v in sorted(annual.items())))
        lines.append(f"- Worst year: {fmt_pct(combo.get('worst_year'))} | "
                     f"Positive-year ratio: {combo.get('positive_year_ratio','-')}")
    lines.append("")
    lines.append("## NAV history (start -> end)")
    nav = combo.get("nav_history") or []
    if nav:
        lines.append(f"- {nav[0][0]} -> {nav[-1][0]}: {fmt_money(nav[0][1])} -> {fmt_money(nav[-1][1])} VND "
                     f"({len(nav)} daily points)")
        lines.append("")
        lines.append("| Date | NAV (VND) |")
        lines.append("|------|----------:|")
        # sample to keep readable (first, last, and ~20 evenly spaced points)
        step = max(1, len(nav) // 20)
        for i in range(0, len(nav), step):
            lines.append(f"| {nav[i][0]} | {fmt_money(nav[i][1])} |")
        if nav[-1] not in nav[::step]:
            lines.append(f"| {nav[-1][0]} | {fmt_money(nav[-1][1])} |")
    lines.append("")
    lines.append("## Allocation history\n")
    for a in combo.get("allocations") or []:
        lines.append(allocation_md(a))
    return "\n".join(lines)


def combination_json(run_id, combo):
    """Compact, AI-friendly JSON view (drops bulky repeated holdings where redundant)."""
    out = {
        "run": run_id,
        "symbols": combo.get("symbols", []),
        "score": combo.get("score"),
        "final_nav": combo.get("final_nav"),
        "total_deposits": combo.get("total_deposits"),
        "absolute_profit": combo.get("absolute_profit"),
        "total_return_pct": combo.get("total_return_pct"),
        "twr_pct": combo.get("twr_pct"),
        "twr_annualized_pct": combo.get("twr_annualized_pct"),
        "xirr_pct": combo.get("xirr_pct"),
        "cagr_pct": combo.get("cagr_pct"),
        "annualized_volatility_pct": combo.get("annualized_volatility_pct"),
        "sharpe": combo.get("sharpe"),
        "sortino": combo.get("sortino"),
        "calmar": combo.get("calmar"),
        "max_drawdown_pct": combo.get("max_drawdown_pct"),
        "worst_year": combo.get("worst_year"),
        "positive_year_ratio": combo.get("positive_year_ratio"),
        "turnover_pct": combo.get("turnover_pct"),
        "trade_count": combo.get("trade_count"),
        "first_allocation_date": combo.get("first_allocation_date"),
        "annual_returns": combo.get("annual_returns", {}),
        "nav_history": combo.get("nav_history", []),
        "allocations": combo.get("allocations", []),
    }
    return json.dumps(out, ensure_ascii=False, indent=2)


# --------------------------------------------------------------------------- driver
def latest_run_id():
    runs_dir = os.path.join(RESULTS_DIR, "runs")
    if not os.path.isdir(runs_dir):
        return None
    best, best_ts = None, ""
    for rid in os.listdir(runs_dir):
        meta_path = os.path.join(runs_dir, rid, "meta.json")
        if not os.path.isfile(meta_path):
            continue
        try:
            with open(meta_path, "r", encoding="utf-8") as fh:
                ts = json.load(fh).get("generated_at", "")
        except Exception:
            ts = ""
        if ts > best_ts:
            best, best_ts = rid, ts
    return best


def collect_markdown(run_id: str, include_all: bool = True) -> dict[str, str]:
    """Build all Markdown reports for a run in memory: {filename: content}."""
    run_dir = os.path.join(RESULTS_DIR, "runs", run_id)
    meta = _read(os.path.join(run_dir, "meta.json"))
    index = _read(os.path.join(run_dir, "index.json"))
    if not index:
        raise FileNotFoundError(f"No index data for run {run_id}")

    files: dict[str, str] = {}
    files["_RUN.md"] = run_overview_md(run_id, meta, index)
    stats = _read(os.path.join(run_dir, "stats.json"))
    if stats and stats.get("stats"):
        files["_STATS.md"] = stats_md(stats["stats"])

    all_parts = []
    combos = [c for c in index.get("combinations", []) if not c.get("error")]
    for c in combos:
        slug = c.get("slug") or "_".join(c.get("symbols", []))
        combo = _read(os.path.join(run_dir, "combinations", f"{slug}.json"))
        if not combo:
            continue
        md = combination_md(run_id, combo)
        files[f"{slug}.md"] = md
        all_parts.append(md)
    if include_all and all_parts:
        files["ALL_COMBINATIONS.md"] = "# ALL COMBINATIONS\n\n" + "\n\n---\n\n".join(all_parts)
    return files


def build_zip(run_id: str, include_all: bool = True) -> bytes:
    """One-button export: every Markdown report + all raw JSON artifacts of the run."""
    files = collect_markdown(run_id, include_all=include_all)
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        for name, content in files.items():
            zf.writestr(name, content)
        base = os.path.join(RESULTS_DIR, "runs", run_id)
        if os.path.isdir(base):
            for root, _dirs, names in os.walk(base):
                for f in names:
                    full = os.path.join(root, f)
                    zf.write(full, f"data/{os.path.relpath(full, base)}")
        ranking = os.path.join(RESULTS_DIR, "ranking.csv")
        if os.path.isfile(ranking):
            zf.write(ranking, "data/ranking.csv")
    return buf.getvalue()


def main():
    ap = argparse.ArgumentParser(description="Export combination data in an AI-readable format")
    ap.add_argument("--run", default=None, help="run id (default: latest)")
    ap.add_argument("--out", default=os.path.join(RESULTS_DIR, "export"), help="output directory")
    ap.add_argument("--format", choices=["md", "json"], default="md", help="export format")
    ap.add_argument("--all", action="store_true", help="also write ALL_COMBINATIONS file")
    args = ap.parse_args()

    run_id = args.run or latest_run_id()
    if not run_id:
        print("No runs found under", RESULTS_DIR)
        return 1
    run_dir = os.path.join(RESULTS_DIR, "runs", run_id)
    meta = _read(os.path.join(run_dir, "meta.json"))
    index = _read(os.path.join(run_dir, "index.json"))
    if not index:
        print(f"No index data for run {run_id}")
        return 1

    out_dir = os.path.join(args.out, run_id)
    os.makedirs(out_dir, exist_ok=True)

    combos = [c for c in index.get("combinations", []) if not c.get("error")]

    if args.format == "md":
        files = collect_markdown(run_id, include_all=args.all)
        for name, content in files.items():
            with open(os.path.join(out_dir, name), "w", encoding="utf-8") as fh:
                fh.write(content)
        print(f"Exported {len(files) - (2 if '_RUN.md' in files else 1)} combination reports (Markdown) -> {out_dir}")
    else:
        for c in combos:
            slug = c.get("slug") or "_".join(c.get("symbols", []))
            combo = _read(os.path.join(run_dir, "combinations", f"{slug}.json"))
            if not combo:
                continue
            with open(os.path.join(out_dir, f"{slug}.json"), "w", encoding="utf-8") as fh:
                fh.write(combination_json(run_id, combo))
        if args.all:
            with open(os.path.join(out_dir, "ALL_COMBINATIONS.json"), "w", encoding="utf-8") as fh:
                json.dump([_read(os.path.join(run_dir, "combinations", f"{(c.get('slug') or '_'.join(c.get('symbols', [])))}.json"))
                           for c in combos], fh, ensure_ascii=False, indent=2)
        print(f"Exported {len(combos)} combination reports (JSON) -> {out_dir}")
    return 0


def _read(path):
    try:
        with open(path, "r", encoding="utf-8") as fh:
            return json.load(fh)
    except Exception:
        return None


if __name__ == "__main__":
    sys.exit(main())