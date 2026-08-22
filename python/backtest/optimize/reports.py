"""Leaderboards, Pareto frontier, and CSV/JSON exports."""

from __future__ import annotations

import csv
import json
import os

from ..candidate import Candidate
from .nsga2 import dominates


def pareto_frontier(items: list[dict]) -> list[dict]:
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


def _pre_holdout_live_growth_score(item: dict) -> float:
    """Growth-first live ranking using only information available pre-holdout."""
    m = item.get("metrics") or {}
    r = item.get("robust") or {}
    recent = item.get("recent_validation") or {}
    return float(
        0.45 * r.get("robust_return", -1e9)
        + 0.25 * r.get("p10_net_twr", -1e9)
        + 0.20 * recent.get("net_twr_annualized_pct", -1e9)
        + 0.10 * m.get("net_twr_annualized_pct", -1e9)
    )


def leaderboards(results: list[dict]) -> dict:
    """Research leaderboards and a pre-holdout frozen live winner.

    Final-holdout fields are never used for ranking. A frozen winner may fail the
    holdout without the system silently switching to a different candidate.
    """
    valid = [r for r in results if r.get("metrics") and not r["metrics"].get("error")]
    if not valid:
        return {}

    best_return = max(valid, key=lambda r: r["metrics"].get("net_twr_annualized_pct", -1e9))
    best_risk = max(
        valid,
        key=lambda r: (
            0.35 * r["metrics"].get("sharpe", 0.0)
            + 0.25 * r["metrics"].get("sortino", 0.0)
            + 0.25 * r["metrics"].get("calmar", 0.0)
            + 0.15 * (1.0 + r["metrics"].get("cdar95_pct", 0.0) / 100.0)
        ),
    )
    best_mdd = max(
        valid,
        key=lambda r: (
            r["metrics"].get("max_drawdown_pct", -1e9)
            + 0.35 * r["metrics"].get("cdar95_pct", -1e9)
        ),
    )

    robust_pool = [r for r in valid if r.get("robust")]
    if robust_pool:
        best_robust = max(
            robust_pool,
            key=lambda r: (r.get("robust") or {}).get("robust_return", -1e9),
        )
    else:
        best_robust = best_mdd

    winners = {
        "best_return": best_return,
        "best_risk_adjusted": best_risk,
        "best_low_drawdown": best_mdd,
        "best_robust": best_robust,
    }

    live = [r for r in valid if r.get("live_eligible") and r.get("robust")]
    if live:
        winners["best_live_eligible"] = max(live, key=_pre_holdout_live_growth_score)
    return winners


def _row(item: dict) -> dict:
    c: Candidate = item["candidate"]
    m = item.get("metrics") or {}
    r = item.get("robust") or {}
    recent = item.get("recent_validation") or {}
    t = item.get("test") or {}
    test_period = ((t.get("per_window") or [{}])[0] or {}) if t else {}
    row = {
        "symbols": " ".join(c.symbols),
        "n_symbols": len(c.symbols),
        "allocation_count_per_year": len(c.allocation_days),
        "allocation_days": "[" + ",".join(str(d) for d in c.allocation_days) + "]",
        "live_eligible": item.get("live_eligible"),
        "eligibility_reasons": ";".join(item.get("eligibility_reasons") or []),
    }
    for k in [
        "net_twr_annualized_pct", "net_xirr_pct", "sharpe", "sortino", "calmar",
        "max_drawdown_pct", "cdar95_pct", "underwater_ratio", "max_underwater_days",
        "min_equity_exposure", "avg_equity_exposure", "turnover_pct", "cost_pct_of_nav",
        "transaction_cost", "trade_count", "gross_twr_annualized_pct", "gross_xirr_pct",
        "worst_year", "positive_year_ratio", "score", "final_nav", "first_allocation_date",
        "measurement_start_date", "measurement_start_nav",
        "measurement_external_contributions", "measurement_profit",
        "initial_deployment_date", "initial_deployment_before_measurement",
        "n_clamped_allocations", "n_skipped_allocations",
    ]:
        row[f"train_{k}"] = m.get(k)
    for k in [
        "median_net_twr", "p10_net_twr", "p25_net_twr", "worst_net_twr", "return_std",
        "median_sharpe", "worst_mdd", "median_cdar95", "worst_cdar95",
        "positive_window_ratio", "robust_return", "n_windows", "drawdown_gate_pct",
    ]:
        row[f"val_{k}"] = r.get(k)
    for k in [
        "net_twr_annualized_pct", "net_xirr_pct", "sharpe", "max_drawdown_pct",
        "cdar95_pct", "measurement_start_nav", "measurement_external_contributions",
        "measurement_profit", "final_nav", "initial_deployment_date",
        "initial_deployment_before_measurement",
    ]:
        row[f"recent_{k}"] = recent.get(k)
    for k in [
        "median_net_twr", "median_sharpe", "worst_mdd", "worst_cdar95",
        "n_test_windows", "required_test_windows", "coverage_valid", "drawdown_valid", "valid",
    ]:
        row[f"test_{k}"] = t.get(k)
    for k in [
        "net_twr_annualized_pct", "net_xirr_pct", "measurement_start_date",
        "measurement_start_nav", "measurement_external_contributions",
        "measurement_profit", "final_nav", "avg_equity_exposure",
        "initial_deployment_date", "initial_deployment_before_measurement",
    ]:
        row[f"test_period_{k}"] = test_period.get(k)
    row["timing_spike"] = item.get("timing_robust", {}).get("isolated_spike")
    row["timing_median"] = item.get("timing_robust", {}).get("median")
    row["symbol_mean"] = item.get("symbol_robust", {}).get("mean")
    row["concentration_single_stock"] = (item.get("concentration") or {}).get("single_stock")
    return row


def _write_csv(path: str, rows: list[dict]):
    if not rows:
        open(path, "w", encoding="utf-8").close()
        return
    keys = []
    seen = set()
    for row in rows:
        for key in row:
            if key not in seen:
                seen.add(key)
                keys.append(key)
    with open(path, "w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=keys, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def write_baseline_comparison(out_dir: str, finalists: list[dict], baseline_items: dict, baseline_days,
                              winners: dict | None = None) -> None:
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
            "live_eligible": item.get("live_eligible"),
            "eligibility_reasons": ";".join(item.get("eligibility_reasons") or []),
            "opt_recent_twr": (item.get("recent_validation") or {}).get("net_twr_annualized_pct"),
            "opt_robust_return": r.get("robust_return"),
            "base_robust_return": br.get("robust_return"),
            "delta_robust_return": (r.get("robust_return") or 0) - (br.get("robust_return") or 0),
            "opt_median_oos_twr": r.get("median_net_twr"),
            "base_median_oos_twr": br.get("median_net_twr"),
            "opt_p10_oos_twr": r.get("p10_net_twr"),
            "base_p10_oos_twr": br.get("p10_net_twr"),
            "opt_worst_oos_mdd": r.get("worst_mdd"),
            "base_worst_oos_mdd": br.get("worst_mdd"),
            "opt_worst_oos_cdar95": r.get("worst_cdar95"),
            "base_worst_oos_cdar95": br.get("worst_cdar95"),
            "opt_test_median_twr": t.get("median_net_twr"),
            "base_test_median_twr": bt.get("median_net_twr"),
            "opt_test_worst_mdd": t.get("worst_mdd"),
            "base_test_worst_mdd": bt.get("worst_mdd"),
            "opt_test_valid": t.get("valid"),
            "base_test_valid": bt.get("valid"),
            "opt_train_net_twr_ann": m.get("net_twr_annualized_pct"),
            "base_train_net_twr_ann": bm.get("net_twr_annualized_pct"),
            "opt_initial_deployment_date": m.get("initial_deployment_date"),
            "base_initial_deployment_date": bm.get("initial_deployment_date"),
        })
    if winners:
        for name, item in winners.items():
            if item is None:
                continue
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

    _write_csv(os.path.join(out_dir, "candidate_metrics.csv"), [_row(i) for i in all_items if i.get("metrics") and not i["metrics"].get("error")])
    _write_csv(os.path.join(out_dir, "pareto_frontier.csv"), [_row(i) for i in pareto])
    _write_csv(os.path.join(out_dir, "top_candidates.csv"), [_row(i) for i in sorted(all_items, key=lambda i: -(i.get("robust") or {}).get("robust_return", -1e9))][:50])
    _write_csv(os.path.join(out_dir, "walk_forward_results.csv"), [dict(r) for r in window_results])
    _write_csv(os.path.join(out_dir, "timing_robustness.csv"), timing_rows)
    _write_csv(os.path.join(out_dir, "symbol_robustness.csv"), symbol_rows)

    summary_rows = []
    for name, item in winners.items():
        if item is None:
            continue
        r = _row(item)
        r["leaderboard"] = name
        summary_rows.append(r)
    _write_csv(os.path.join(out_dir, "optimizer_summary.csv"), summary_rows)


def item_to_json(item: dict) -> dict:
    c: Candidate = item["candidate"]
    test = item.get("test") or {}
    return {
        "symbols": list(c.symbols),
        "n_symbols": len(c.symbols),
        "allocation_count_per_year": len(c.allocation_days),
        "allocation_days": list(c.allocation_days),
        "metrics": item.get("metrics"),
        "train_metrics": item.get("train_metrics") or item.get("metrics"),
        "validation_metrics": item.get("validation_metrics") or item.get("robust"),
        "recent_validation": item.get("recent_validation"),
        "live_eligible": bool(item.get("live_eligible")),
        "eligibility_reasons": list(item.get("eligibility_reasons") or []),
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
    baseline_block = None
    if baseline_items and baseline_days:
        best = (
            winners.get("best_live_eligible")
            or winners.get("best_robust")
            or next((v for v in winners.values() if v is not None), None)
        )
        b = (baseline_items.get(best["candidate"].key()) if best else None) or {}
        baseline_block = {
            "allocation_days": [int(d) for d in baseline_days],
            "robust": b.get("robust"),
            "test": b.get("test"),
            "train": b.get("train"),
        }
    payload = {
        "experiment_id": meta["experiment_id"],
        "generated_at": meta.get("generated_at"),
        "meta": meta,
        "winners": {name: item_to_json(item) for name, item in winners.items() if item is not None},
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
    c: Candidate = item["candidate"]
    m = item.get("metrics") or {}
    r = item.get("robust") or {}
    recent = item.get("recent_validation") or {}
    t = item.get("test") or {}
    tp = ((t.get("per_window") or [{}])[0] or {}) if t else {}
    tr = item.get("timing_robust") or {}
    sr = item.get("symbol_robust") or {}
    conc = item.get("concentration") or {}
    lines = [
        f"# Finalist: {name}",
        "",
        "## Portfolio",
        f"- Symbols: {' '.join(c.symbols)}",
        f"- N: {len(c.symbols)}",
        f"- Live eligibility: {'PASS' if item.get('live_eligible') else 'FAIL'}",
        f"- Eligibility reasons: {item.get('eligibility_reasons') or []}",
        "",
        "## Initial deployment",
        f"- Initial deployment date: {m.get('initial_deployment_date', '-')}",
        f"- Before TRAIN measurement boundary: {m.get('initial_deployment_before_measurement', '-')}",
        "",
        "## Annual recalibration times",
        f"- Events/year: {len(c.allocation_days)}",
        *[f"- T{i+1}: {d}" for i, d in enumerate(c.allocation_days)],
        f"- Partial-year scheduled events skipped: {m.get('n_skipped_allocations', 0)}",
        "",
        "## TRAIN",
        f"- Net TWR annualized: {m.get('net_twr_annualized_pct', '-')}%",
        f"- Net XIRR (measurement-window anchored): {m.get('net_xirr_pct', '-')}%",
        f"- Sharpe / Sortino / Calmar: {m.get('sharpe', '-')} / {m.get('sortino', '-')} / {m.get('calmar', '-')}",
        f"- Max drawdown: {m.get('max_drawdown_pct', '-')}%",
        f"- CDaR95: {m.get('cdar95_pct', '-')}%",
        f"- Underwater ratio: {m.get('underwater_ratio', '-')}",
        f"- Max underwater trading days: {m.get('max_underwater_days', '-')}",
        f"- Min / avg equity exposure: {m.get('min_equity_exposure', '-')} / {m.get('avg_equity_exposure', '-')}",
        f"- Turnover: {m.get('turnover_pct', '-')}% | Cost: {m.get('cost_pct_of_nav', '-')}% of NAV",
        "",
        "## ROLLING VALIDATION",
        f"- Median OOS net TWR: {r.get('median_net_twr', '-')}%",
        f"- P10 OOS net TWR: {r.get('p10_net_twr', '-')}%",
        f"- Worst OOS MDD: {r.get('worst_mdd', '-')}%",
        f"- Worst OOS CDaR95: {r.get('worst_cdar95', '-')}%",
        f"- Drawdown gate: {r.get('drawdown_gate_pct', '-')}%",
        f"- Robust return: {r.get('robust_return', '-')}",
        "",
        "## RECENT PRE-HOLDOUT VALIDATION (eligibility only)",
        f"- Net TWR annualized: {recent.get('net_twr_annualized_pct', '-')}%",
        f"- Net XIRR: {recent.get('net_xirr_pct', '-')}%",
        f"- MDD: {recent.get('max_drawdown_pct', '-')}%",
        f"- Initial deployment date: {recent.get('initial_deployment_date', '-')}",
        "",
        "## FINAL HOLDOUT",
        f"- Windows: {t.get('n_test_windows', '-')} / {t.get('required_test_windows', '-')} ({'PASS' if t.get('valid') else 'INVALID'})",
        f"- Net TWR annualized: {t.get('median_net_twr', '-')}%",
        f"- Net XIRR (window anchored): {tp.get('net_xirr_pct', '-')}%",
        f"- Measurement start NAV: {tp.get('measurement_start_nav', '-')}",
        f"- External contributions during holdout: {tp.get('measurement_external_contributions', '-')}",
        f"- Measurement profit: {tp.get('measurement_profit', '-')}",
        f"- Final NAV: {tp.get('final_nav', '-')}",
        f"- Worst MDD: {t.get('worst_mdd', '-')}%",
        f"- Worst CDaR95: {t.get('worst_cdar95', '-')}%",
        f"- Initial deployment date: {tp.get('initial_deployment_date', '-')}",
        "",
        "## Robustness",
        f"- Timing mean / median / std: {tr.get('mean', '-')} / {tr.get('median', '-')} / {tr.get('std', '-')}",
        f"- Timing isolated spike: {tr.get('isolated_spike', '-')}",
        f"- Symbol-neighbour mean: {sr.get('mean', '-')}",
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
