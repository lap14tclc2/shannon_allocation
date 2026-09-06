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


def build_report_text(result: dict) -> str:
    ic = result.get("rank_ic") or {}
    quant = result.get("quantiles") or {}
    quant_map = quant.get("quantiles") or {}
    q_labels = sorted(quant_map)
    top = q_labels[-1] if q_labels else None
    bottom = q_labels[0] if q_labels else None
    lines = [
        f"Factor: {result.get('factor')}",
        f"Horizon (sessions): {result.get('horizon_sessions')}",
        f"Benchmark: {result.get('benchmark', 'VNINDEX')}",
        f"Observations: {result.get('observations')}",
        f"Sealed-OOS observations: {result.get('sealed_observations')}",
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
        "Walk-forward windows:",
    ]
    for window in result.get("walk_forward_windows") or []:
        lines.append(
            f"  train {window['train_start']}..{window['train_end']} -> "
            f"validate {window['valid_start']}..{window['valid_end']}"
        )
    lines.append("")
    lines.append("Limitations:")
    for limitation in result.get("limitations") or []:
        lines.append(f"  - {limitation}")
    return "\n".join(lines)