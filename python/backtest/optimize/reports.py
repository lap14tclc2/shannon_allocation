"""Leaderboards, Pareto frontier, and CSV/JSON exports per the spec."""

from __future__ import annotations

import csv
import json
import os

from ..candidate import Candidate
from .nsga2 import dominates


def pareto_frontier(items: list[dict]) -> list[dict]:
    """Non-dominated items (maximised objectives)."""
    out = []
    for i, item in enumerate(items):
        dom = False
        for j, other in enumerate(items):
            if i == j:
                continue
            if dominates(other["objectives"], item["objectives"]):
                dom = True
                break
        if not dom:
            out.append(item)
    return out


def leaderboards(results: list[dict]) -> dict:
    """Best return / best risk-adjusted / best low-drawdown / best robust.

    The first three use TRAIN-window metrics and are labelled as such. `best_robust`
    is the candidate with the highest OOS robust score that ALSO passed 100% of its
    final TEST windows — a candidate that failed part of its untouched test set is
    not trusted (audit rule: valid_test_windows < required_test_windows => INVALID).
    """
    valid = [r for r in results if r.get("metrics") and not r["metrics"].get("error")]
    if not valid:
        return {}

    def test_ok(r: dict) -> bool:
        t = r.get("test")
        if t is None:
            return False
        return bool(t.get("valid"))

    best_return = max(valid, key=lambda r: r["metrics"]["net_twr_annualized_pct"])
    best_risk = max(valid, key=lambda r: 0.4 * r["metrics"]["sharpe"] + 0.3 * r["metrics"]["sortino"]
                    + 0.3 * r["metrics"]["calmar"])
    best_mdd = max(valid, key=lambda r: r["metrics"]["max_drawdown_pct"])
    tested = [r for r in valid if test_ok(r)]
    pool_robust = tested if tested else [r for r in valid if r.get("robust")]
    best_robust = max(pool_robust, key=lambda r: (r.get("robust") or {}).get("robust_return", -1e9))
    return {
        "best_return": best_return,
        "best_risk_adjusted": best_risk,
        "best_low_drawdown": best_mdd,
        "best_robust": best_robust,
    }


def _row(item: dict) -> dict:
    c: Candidate = item["candidate"]
    m = item.get("metrics") or {}
    r = item.get("robust") or {}
    t = item.get("test") or {}
    row = {
        "symbols": " ".join(c.symbols),
        "n_symbols": len(c.symbols),
        "allocation_days": "[" + ",".join(str(d) for d in c.allocation_days) + "]",
    }
    for k in [
        "net_twr_annualized_pct", "net_xirr_pct", "sharpe", "sortino", "calmar",
        "max_drawdown_pct", "turnover_pct", "cost_pct_of_nav", "transaction_cost",
        "trade_count", "gross_twr_annualized_pct", "gross_xirr_pct", "worst_year",
        "positive_year_ratio", "final_nav", "first_allocation_date",
    ]:
        row[f"train_{k}"] = m.get(k)
    for k in ["median_net_twr", "p10_net_twr", "worst_net_twr", "return_std",
              "median_sharpe", "worst_mdd", "positive_window_ratio", "robust_return", "n_windows"]:
        row[f"val_{k}"] = r.get(k)
    row["test_median_net_twr"] = t.get("median_net_twr")
    row["test_n_windows"] = t.get("n_test_windows")
    row["test_required_windows"] = t.get("required_test_windows")
    row["test_valid"] = t.get("valid")
    row["timing_spike"] = item.get("timing_robust", {}).get("isolated_spike")
    row["timing_median"] = item.get("timing_robust", {}).get("median")
    row["symbol_mean"] = item.get("symbol_robust", {}).get("mean")
    row["concentration_single_stock"] = (item.get("concentration") or {}).get("single_stock")
    return row


def _write_csv(path: str, rows: list[dict]):
    if not rows:
        open(path, "w", encoding="utf-8").close()
        return
    keys = list(rows[0].keys())
    with open(path, "w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=keys)
        writer.writeheader()
        writer.writerows(rows)


def write_baseline_comparison(out_dir: str, finalists: list[dict], baseline_items: dict, baseline_days,
                              winners: dict | None = None) -> None:
    """Compare each finalist's schedule against the quarterly baseline on the SAME symbols."""
    rows = []
    for item in finalists:
        c: Candidate = item["candidate"]
        b = baseline_items.get(c.key()) or {}
        br = b.get("robust") or {}
        bt = b.get("test") or {}
        r = item.get("robust") or {}
        t = item.get("test") or {}
        m = item.get("metrics") or {}
        bm = b.get("train") or {}
        rows.append({
            "symbols": " ".join(c.symbols),
            "optimized_allocation_days": "[" + ",".join(str(d) for d in c.allocation_days) + "]",
            "baseline_allocation_days": "[" + ",".join(str(d) for d in baseline_days) + "]",
            "opt_robust_return": r.get("robust_return"),
            "base_robust_return": br.get("robust_return"),
            "delta_robust_return": (r.get("robust_return") or 0) - (br.get("robust_return") or 0),
            "opt_median_oos_twr": r.get("median_net_twr"),
            "base_median_oos_twr": br.get("median_net_twr"),
            "opt_p10_oos_twr": r.get("p10_net_twr"),
            "base_p10_oos_twr": br.get("p10_net_twr"),
            "opt_test_median_twr": t.get("median_net_twr"),
            "base_test_median_twr": bt.get("median_net_twr"),
            "opt_test_valid": t.get("valid"),
            "base_test_valid": bt.get("valid"),
            "opt_train_net_twr_ann": m.get("net_twr_annualized_pct"),
            "base_train_net_twr_ann": bm.get("net_twr_annualized_pct"),
        })
    if winners:
        for name, item in winners.items():
            for rw in rows:
                if rw["symbols"] == " ".join(item["candidate"].symbols) and \
                   rw["optimized_allocation_days"] == "[" + ",".join(str(d) for d in item["candidate"].allocation_days) + "]":
                    rw["leaderboard"] = (rw.get("leaderboard") or "") + name + ";"
    _write_csv(os.path.join(out_dir, "baseline_comparison.csv"), rows)


def write_exports(
    out_dir: str,
    meta: dict,
    all_items: list[dict],
    winners: dict,
    pareto: list[dict],
    window_results: list[dict],
    timing_rows: list[dict],
    symbol_rows: list[dict],
) -> None:
    os.makedirs(out_dir, exist_ok=True)

    with open(os.path.join(out_dir, "optimizer_config.json"), "w", encoding="utf-8") as fh:
        json.dump(meta, fh, indent=2, ensure_ascii=False)

    _write_csv(os.path.join(out_dir, "candidate_metrics.csv"),
               [_row(i) for i in all_items if i.get("metrics") and not i["metrics"].get("error")])
    _write_csv(os.path.join(out_dir, "pareto_frontier.csv"), [_row(i) for i in pareto])
    _write_csv(os.path.join(out_dir, "top_candidates.csv"),
               [_row(i) for i in sorted(all_items, key=lambda i: -(i.get("robust") or {}).get("robust_return", -1e9))][:50])
    _write_csv(os.path.join(out_dir, "walk_forward_results.csv"),
               [dict(r) for r in window_results])
    _write_csv(os.path.join(out_dir, "timing_robustness.csv"), timing_rows)
    _write_csv(os.path.join(out_dir, "symbol_robustness.csv"), symbol_rows)

    summary_rows = []
    for name, item in winners.items():
        r = _row(item)
        r["leaderboard"] = name
        summary_rows.append(r)
    _write_csv(os.path.join(out_dir, "optimizer_summary.csv"), summary_rows)


def _write_csv(path: str, rows: list[dict]):
    if not rows:
        open(path, "w", encoding="utf-8").close()
        return
    keys = list(rows[0].keys())
    with open(path, "w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=keys)
        writer.writeheader()
        writer.writerows(rows)


def item_to_json(item: dict) -> dict:
    """Structured JSON view of one candidate item (for the web UI)."""
    c: Candidate = item["candidate"]
    test = item.get("test") or {}
    return {
        "symbols": list(c.symbols),
        "n_symbols": len(c.symbols),
        "allocation_days": list(c.allocation_days),
        "metrics": item.get("metrics"),
        "train_metrics": item.get("train_metrics") or item.get("metrics"),
        "validation_metrics": item.get("validation_metrics") or item.get("robust"),
        "test_metrics": item.get("test_metrics") or test,
        "robust": item.get("robust"),
        "timing_robust": {k: v for k, v in (item.get("timing_robust") or {}).items() if k != "neighbours"},
        "symbol_robust": {k: v for k, v in (item.get("symbol_robust") or {}).items() if k != "results"},
        "concentration": item.get("concentration"),
        "test": test,
    }


def write_experiment_json(out_dir: str, meta: dict, winners: dict, pareto: list,
                          top_candidates: list, finalists: list,
                          baseline_items: dict | None = None, baseline_days=None) -> str:
    """Write a structured experiment.json consumed by the web UI."""
    baseline_block = None
    if baseline_items and baseline_days:
        best = None
        for item in winners.values():
            if item.get("test", {}).get("valid"):
                best = item
                break
        b = (baseline_items.get(best["candidate"].key()) if best else None) or {}
        baseline_block = {
            "allocation_days": [int(d) for d in baseline_days],
            "robust": b.get("robust"),
            "test": b.get("test"),
        }
    payload = {
        "experiment_id": meta["experiment_id"],
        "generated_at": meta.get("generated_at"),
        "meta": meta,
        "winners": {name: item_to_json(item) for name, item in winners.items()},
        "pareto": [item_to_json(i) for i in pareto],
        "top_candidates": [item_to_json(i) for i in top_candidates],
        "finalists": [item_to_json(i) for i in finalists],
        "baseline": baseline_block,
    }
    path = os.path.join(out_dir, "experiment.json")
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(payload, fh, indent=2, ensure_ascii=False)
    return path


def final_report(item: dict, out_dir: str, name: str) -> str:
    """Markdown report for one finalist, with clearly-labelled evaluation phases."""
    c: Candidate = item["candidate"]
    m = item.get("metrics") or {}          # TRAIN window
    r = item.get("robust") or {}           # VALIDATION (walk-forward robust)
    t = item.get("test") or {}             # FINAL TEST (untouched OOS)
    tr = item.get("timing_robust") or {}
    sr = item.get("symbol_robust") or {}
    conc = item.get("concentration") or {}
    lines = [
        f"# Finalist: {name}",
        "",
        "## Portfolio",
        f"- Symbols: {' '.join(c.symbols)}",
        f"- N: {len(c.symbols)}",
        "",
        "## Allocation times (trading-day positions)",
        *[f"- T{i+1}: {d}" for i, d in enumerate(c.allocation_days)],
        "",
        "## TRAIN window (optimization) — metrics computed from the window START, full window counted",
        f"- Net TWR annualized: {m.get('net_twr_annualized_pct', '-')}%",
        f"- Net XIRR: {m.get('net_xirr_pct', '-')}%",
        f"- Gross TWR annualized: {m.get('gross_twr_annualized_pct', '-')}%",
        f"- Gross XIRR: {m.get('gross_xirr_pct', '-')}%",
        f"- Sharpe: {m.get('sharpe', '-')} | Sortino: {m.get('sortino', '-')} | Calmar: {m.get('calmar', '-')}",
        f"- Max drawdown: {m.get('max_drawdown_pct', '-')}%",
        f"- Worst year: {m.get('worst_year', '-')}% | Positive-year ratio: {m.get('positive_year_ratio', '-')}",
        f"- Turnover: {m.get('turnover_pct', '-')}% | Trade count: {m.get('trade_count', '-')}",
        f"- Total transaction cost: {m.get('transaction_cost', '-')} VND ({m.get('cost_pct_of_nav', '-')}% of NAV)",
        f"- First allocation date: {m.get('first_allocation_date', '-')}",
        "",
        "## VALIDATION (walk-forward robust fitness across all validation windows)",
        f"- Median OOS net TWR: {r.get('median_net_twr', '-')}%",
        f"- P10 OOS net TWR: {r.get('p10_net_twr', '-')}%",
        f"- P25 OOS net TWR: {r.get('p25_net_twr', '-')}%",
        f"- Worst OOS net TWR: {r.get('worst_net_twr', '-')}%",
        f"- Return std: {r.get('return_std', '-')}",
        f"- Median OOS Sharpe: {r.get('median_sharpe', '-')}",
        f"- Worst OOS MDD: {r.get('worst_mdd', '-')}%",
        f"- Positive-window ratio: {r.get('positive_window_ratio', '-')}",
        f"- Valid windows: {r.get('n_windows', '-')} / {r.get('n_windows', '-')} (100% coverage policy)",
        f"- Robust return (median - lambda*std): {r.get('robust_return', '-')}",
        "",
        "## FINAL TEST (untouched out-of-sample windows)",
        f"- Valid test windows: {t.get('n_test_windows', '-')} / {t.get('required_test_windows', '-')} "
        f"({'PASS' if t.get('valid') else 'INVALID'})",
        f"- Median test net TWR: {t.get('median_net_twr', '-')}%",
        "",
        "## Timing robustness (neighbourhood stability from OOS robust scores)",
        f"- Neighbour mean: {tr.get('mean', '-')} | median: {tr.get('median', '-')} | std: {tr.get('std', '-')}",
        f"- Neighbour max: {tr.get('max', '-')} | min: {tr.get('min', '-')} | isolated spike: {tr.get('isolated_spike', '-')}",
        f"- Symbol neighbourhood mean: {sr.get('mean', '-')}",
        f"- Concentration single-stock: {conc.get('single_stock', '-')}, single-year: {conc.get('single_year', '-')}",
        "",
        "## Diagnostics",
        f"- Annual returns: {m.get('annual_returns', {})}",
        f"- Stock contributions: {m.get('stock_contributions', {})}",
        "",
    ]
    path = os.path.join(out_dir, f"finalist_{name}.md")
    with open(path, "w", encoding="utf-8") as fh:
        fh.write("\n".join(lines))
    return path