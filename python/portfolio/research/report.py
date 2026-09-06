"""Deterministic research report builder (no marketing language)."""
from __future__ import annotations

from typing import Any


def _fmt(value: Any, digits: int = 4) -> str:
    if value is None:
        return "N/A"
    try:
        return f"{float(value):.{digits}f}"
    except (TypeError, ValueError):
        return str(value)


def _pct(value: Any) -> str:
    if value is None:
        return "N/A"
    return f"{float(value) * 100:.2f}%"


def build_full_report_markdown(run: dict) -> str:
    """Build the end-to-end research Markdown report from a ``run_full_research`` result."""
    universe_stats = run.get("universe_stats") or {}
    price_coverage = run.get("price_coverage") or {}
    results = run.get("results") or []
    config = run.get("config") or {}
    cost = run.get("cost_model") or {}
    by_factor: dict[str, list[dict]] = {}
    for r in results:
        by_factor.setdefault(r["factor"], []).append(r)

    lines = [
        "# QPort Buffett-Thorp Factor Research",
        "",
        f"_run_id: {run.get('run_id')} | generated: 2026-09-06_",
        "",
        "## 1. Data Readiness",
        f"- Universe candidates (securities): {universe_stats.get('total_candidates', 'N/A')}",
        f"- Universe selected: {len(run.get('universe') or [])}",
        f"- Excluded reasons: {universe_stats.get('excluded_reason', {})}",
        f"- Price fetch: {price_coverage.get('fetched', 'N/A')}/{price_coverage.get('universe_requested', 'N/A')} symbols",
        f"- Failed fetches: {list((price_coverage.get('failed') or {}).keys()) or 'none'}",
        f"- Benchmark rows: {price_coverage.get('benchmark_rows', 'N/A')} (VNINDEX, {price_coverage.get('benchmark_span')})",
        f"- Snapshot dates: {len(run.get('snapshot_dates') or [])} (monthly last-trading-day)",
        f"- Snapshots built: {run.get('snapshot_count')}",
        f"- Outcome rows: {run.get('outcome_count')}",
        "",
        "## 2. PIT Integrity",
        "- Facts filtered by `available_from <= as_of` (inferred 45d quarter / 90d annual governance lags).",
        "- `fetched_at` is never used as publication time.",
        "- Verified publication metadata is absent in the DB -> 100% inferred availability.",
        "",
        "## 3. Universe Definition",
        "- HOSE/HNX/UPCOM, 3-4 letter tickers (warrants/derivatives excluded), active securities.",
        f"- Top {len(run.get('universe') or [])} by 20D average traded value.",
        "- `SURVIVORSHIP_BIAS_NOT_FULLY_CONTROLLED`: historical membership cannot be reconstructed.",
        "",
        "## 4. Benchmark Coverage",
        f"- VNINDEX: {price_coverage.get('benchmark_rows', 'N/A')} sessions fetched from VNDIRECT.",
        "- Index points (not VND); provider mapping verified at fetch time.",
        "",
        "## 5. Cost Assumptions",
        f"- commission: {_pct(cost.get('commission_rate'))} per side",
        f"- sell tax: {_pct(cost.get('sell_tax_rate'))}",
        f"- slippage: {_pct(cost.get('slippage_rate'))} per side",
        f"- round-trip cost: {_pct(2 * float(cost.get('commission_rate') or 0) + float(cost.get('sell_tax_rate') or 0) + 2 * float(cost.get('slippage_rate') or 0))}",
        f"- note: {cost.get('assumptions', '')}",
        "",
        "## Research periods",
        f"- research_start: {config.get('research_start')}",
        f"- research_end: {config.get('research_end')}",
        f"- train_years: {config.get('train_years')} | validation_years: {config.get('validation_years')}",
        f"- sealed_oos: {config.get('sealed_oos_start')} -> {config.get('sealed_oos_end')}",
        "",
        "## Factor Results (all horizons)",
        "",
    ]

    summary = [
        "| Factor | Horizon | Obs | Mean IC | Pos IC | Q5-Q1 gross | after-cost | Sealed IC | Verdict |",
        "|---|---|---|---|---|---|---|---|---|",
    ]
    for factor_name in sorted(by_factor):
        for r in by_factor[factor_name]:
            ic = r.get("rank_ic") or {}
            summary.append(
                f"| {factor_name} | {r['horizon_sessions']} | {r['observations']} "
                f"| {_fmt(ic.get('mean_ic'))} | {_fmt(ic.get('positive_ic_ratio'))} "
                f"| {_fmt(r.get('gross_spread'))} | {_fmt(r.get('after_cost_spread'))} "
                f"| {_fmt(r.get('sealed_oos_mean_ic'))} | {r['verdict']} |"
            )
    lines += summary
    lines += ["", "### Detail per factor"]

    for factor_name in sorted(by_factor):
        for r in by_factor[factor_name]:
            ic = r.get("rank_ic") or {}
            quant = r.get("quantiles") or {}
            qm = quant.get("quantiles") or {}
            lines += [
                f"#### {factor_name} x {r['horizon_sessions']} sessions",
                f"- mean IC: {_fmt(ic.get('mean_ic'))} | median: {_fmt(ic.get('median_ic'))} | std: {_fmt(ic.get('ic_std'))} | positive ratio: {_fmt(ic.get('positive_ic_ratio'))} | n_dates: {ic.get('count')}",
                f"- Q1..Q5 excess: {', '.join(f'{k}={_fmt(qm.get(k))}' for k in sorted(qm))}",
                f"- gross spread: {_fmt(r.get('gross_spread'))} | after-cost: {_fmt(r.get('after_cost_spread'))}",
                f"- walk-forward windows: {len(r.get('walk_forward_windows') or [])} | walk-forward mean IC: {_fmt(r.get('walk_forward_mean_ic'))}",
                f"- sealed OOS mean IC: {_fmt(r.get('sealed_oos_mean_ic'))} | sealed evaluated: {r.get('periods', {}).get('sealed_evaluated')} | sealed used for tuning: {r.get('periods', {}).get('sealed_used_for_tuning')}",
                f"- **verdict: {r['verdict']}**",
                "",
            ]

    # Verdict summary + production readiness.
    verdict_counts: dict[str, int] = {}
    validated_by_factor: dict[str, int] = {}
    for r in results:
        verdict_counts[r["verdict"]] = verdict_counts.get(r["verdict"], 0) + 1
        if r["verdict"] == "VALIDATED":
            validated_by_factor[r["factor"]] = validated_by_factor.get(r["factor"], 0) + 1
    lines += [
        "## 12. Factor Verdicts",
        f"- verdict counts: {verdict_counts}",
        f"- VALIDATED horizons per factor: {validated_by_factor}",
        "",
        "## 13. Limitations",
        "- Historical universe membership not reconstructible; survivorship bias not fully controlled.",
        "- Inferred publication dates are governance assumptions, not verified filing dates.",
        "- Cost model is a research simplification, not live-realistic.",
        "- Missing/late data yields missing factor values (never fabricated).",
        "",
        "## 14. Production Readiness Decision",
        "- No factor is connected to production allocation in this milestone.",
        "- Expected Alpha and Kelly remain disabled.",
    ]
    # Conservative: a factor is considered a candidate only if VALIDATED across
    # most tested horizons (>= 3 of 4). A single validating horizon is NOT robust.
    robust = sorted(f for f, n in validated_by_factor.items() if n >= 3)
    partial = sorted(f for f, n in validated_by_factor.items() if 0 < n < 3)
    if robust:
        lines.append(
            f"- Robustly validated across horizons (>=3 of 4): {robust}. "
            "Subject to further PIT/cost/survivorship validation before any "
            "production calibration."
        )
    if partial:
        lines.append(
            f"- VALIDATED at only a subset of horizons (NOT robust): {partial}. "
            "Treated as WEAK/UNSTABLE for production purposes."
        )
    if not robust:
        lines.append("- No factor currently proven robust after costs and sealed OOS. Answer: **NONE**.")
    lines.append("")
    return "\n".join(lines)


def build_report_text(result: dict) -> str:
    ic = result.get("rank_ic") or {}
    quant = result.get("quantiles") or {}
    quant_map = quant.get("quantiles") or {}
    q_labels = sorted(quant_map)
    top = q_labels[-1] if q_labels else None
    bottom = q_labels[0] if q_labels else None
    periods = result.get("periods") or {}
    lines = [
        f"Factor: {result.get('factor')}",
        f"Horizon (sessions): {result.get('horizon_sessions')}",
        f"Benchmark: {result.get('benchmark', 'VNINDEX')}",
        f"Observations (tuning): {result.get('observations')}",
        f"Sealed-OOS observations: {result.get('sealed_observations')}",
        "",
        "Research periods:",
        f"  In-sample range: {periods.get('in_sample_range')}",
        f"  Sealed OOS range: {periods.get('sealed_range')}",
        f"  Research cutoff (train/validate upper bound): {periods.get('research_cutoff')}",
        f"  Sealed OOS evaluated: {periods.get('sealed_evaluated')}",
        f"  Sealed OOS used for tuning: {periods.get('sealed_used_for_tuning')}",
        "",
        "Rank IC:",
        f"  mean: {_fmt(ic.get('mean_ic'))}",
        f"  median: {_fmt(ic.get('median_ic'))}",
        f"  std: {_fmt(ic.get('ic_std'))}",
        f"  positive ratio: {_fmt(ic.get('positive_ic_ratio'))}",
        f"  count: {ic.get('count')}",
        "",
        "Quantiles (mean forward excess return):",
    ]
    for label in q_labels:
        lines.append(f"  {label}: {_fmt(quant_map.get(label))}")
    lines += [
        f"  {top}-minus-{bottom} gross spread: {_fmt(result.get('gross_spread'))}",
        f"  after-cost spread: {_fmt(result.get('after_cost_spread'))}",
        "",
        f"Sealed-OOS mean rank IC: {_fmt(result.get('sealed_oos_mean_ic'))}",
        f"Verdict: {result.get('verdict')}",
        "",
        "Walk-forward windows (none may touch sealed OOS):",
    ]
    for window in result.get("walk_forward_windows") or []:
        lines.append(
            f"  train {window['train_start']}..{window['train_end']} -> "
            f"validate {window['valid_start']}..{window['valid_end']}"
        )
    if not (result.get("walk_forward_windows") or []):
        lines.append("  (no walk-forward window fits before the sealed OOS boundary)")
    lines.append("")
    lines.append("Limitations:")
    for limitation in result.get("limitations") or []:
        lines.append(f"  - {limitation}")
    return "\n".join(lines)