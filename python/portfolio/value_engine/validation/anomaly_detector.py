"""
Layer 1 — Pure numeric validation & raw anomaly detector (UFVS, feedback.txt §1-§2).

Dùng chuẩn Universal Financial Validation Standard:
  Δ_t = 2(X_t − X_{t−1}) / (|X_t| + |X_{t−1}| + ε)          (Symmetric % Change, bounded [-2,+2])
  Z_t = 0.6745 · (Δ_t − median(Δ)) / (MAD(Δ) + ε)          (robust Z-score)

  |Z| < 2.5   NORMAL
  2.5–3.5     UNUSUAL
  3.5–5.0     STRONG_ANOMALY
  >5.0        EXTREME_ANOMALY

Không có bất kỳ ticker-specific rule nào.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, Iterable, List, Optional

EPS = 1e-9

# Z-score ngưỡng (feedback.txt §1).
Z_NORMAL = 2.5
Z_UNUSUAL = 3.5
Z_STRONG = 5.0

# Core metrics (feedback.txt §2 core vector). financial_history KHÔNG có total_assets,
# nên dùng equity/total_debt/shares làm proxy scale.
CORE_METRICS = (
    "revenue",
    "net_profit",
    "operating_cash_flow",
    "equity",
    "total_debt",
    "shares_outstanding",
)
METRICS = (
    ("revenue", "revenue"),
    ("net_profit", "net_profit"),
    ("operating_cash_flow", "operating_cash_flow"),
    ("equity", "equity"),
    ("total_debt", "total_debt"),
    ("shares_outstanding", "shares_outstanding"),
)

# Unit-jump heuristic (feedback.txt §9/§7): metric đổi >100x nhưng related không đổi
# -> UNIT_MAPPING_ERROR_CANDIDATE.
UNIT_JUMP_RATIO = 100.0
RELATED_METRIC_MOVE_CAP = 0.2


@dataclass
class MetricAnomaly:
    """Một (năm, metric) vừa vượt ngưỡng robust Z — detector ban đầu."""

    fiscal_year: int
    metric: str
    previous: float
    current: float
    change_pct: float
    detector_status: str  # UNUSUAL | STRONG_ANOMALY | EXTREME_ANOMALY | UNIT_ERROR
    delta: float = 0.0        # symmetric % change
    z_score: float = 0.0      # robust Z
    severity: str = "UNUSUAL"
    previous_others: Dict[str, float] = field(default_factory=dict)
    current_others: Dict[str, float] = field(default_factory=dict)


def _num(value: Any) -> Optional[float]:
    try:
        v = float(value)
        return v if v == v else None  # NaN check
    except (TypeError, ValueError):
        return None


def _sorted_history(financial_history: Optional[List[Dict[str, Any]]]) -> List[Dict[str, Any]]:
    return sorted(
        (h for h in (financial_history or []) if h and h.get("fiscal_year") is not None),
        key=lambda r: int(r.get("fiscal_year") or 0),
    )


def _median(values: List[float]) -> float:
    ordered = sorted(values)
    n = len(ordered)
    if n == 0:
        return 0.0
    if n % 2 == 1:
        return ordered[n // 2]
    return (ordered[n // 2 - 1] + ordered[n // 2]) / 2.0


def symmetric_pct_change(p: float, q: float) -> float:
    """Δ = 2(X_t − X_{t−1}) / (|X_t| + |X_{t−1}| + ε), bounded [-2, +2] (UFVS §1)."""
    return 2.0 * (q - p) / (abs(p) + abs(q) + EPS)


def robust_z(deltas: List[float]) -> List[float]:
    """Z = 0.6745 · (Δ − median Δ) / (MAD Δ + ε). Cần >= 3 điểm; ngắn hơn -> 0.

    Cắt biên độ tại ±10 để tránh Z vô cùng khi MAD ≈ 0 (chuỗi gần như bất biến).
    """
    n = len(deltas)
    if n < 3:
        return [0.0] * n
    med = _median(deltas)
    mad = _median([abs(d - med) for d in deltas])
    if mad < EPS:
        mad = EPS
    return [max(-10.0, min(10.0, 0.6745 * (d - med) / mad)) for d in deltas]


def severity_from_z(z: float) -> str:
    az = abs(z)
    if az < Z_NORMAL:
        return "NORMAL"
    if az < Z_UNUSUAL:
        return "UNUSUAL"
    if az < Z_STRONG:
        return "STRONG_ANOMALY"
    return "EXTREME_ANOMALY"


def compute_year_metric_scores(
    financial_history: Optional[List[Dict[str, Any]]],
    ignore_metrics: Iterable[str] = (),
) -> Dict[int, Dict[str, Dict[str, float]]]:
    """Bảng {year: {metric: {value, delta, z, severity}}} cho MỌI năm/metric có dữ liệu.

    Đây là input cho breadth A, coherence C, persistence P, mean-reversion M.
    """
    ignored = set(ignore_metrics)
    rows = _sorted_history(financial_history)
    metric_z: Dict[str, Dict[int, float]] = {}
    metric_delta: Dict[str, Dict[int, float]] = {}
    metric_value: Dict[str, Dict[int, float]] = {}
    for metric, key in METRICS:
        if metric in ignored:
            continue
        series = [(int(r["fiscal_year"]), _num(r.get(key))) for r in rows]
        series = [(y, v) for y, v in series if v is not None and v > 0]
        deltas = []
        for i in range(1, len(series)):
            year = series[i][0]
            delta = symmetric_pct_change(series[i - 1][1], series[i][1])
            deltas.append((year, series[i][1], delta))
        zs = robust_z([d[2] for d in deltas])
        for (year, val, delta), z in zip(deltas, zs):
            metric_value.setdefault(metric, {})[year] = val
            metric_delta.setdefault(metric, {})[year] = delta
            metric_z.setdefault(metric, {})[year] = z
    years = sorted({y for m in metric_z for y in metric_z[m]})
    table: Dict[int, Dict[str, Dict[str, float]]] = {}
    for year in years:
        table[year] = {}
        for metric in metric_z:
            if year in metric_z.get(metric, {}):
                z = metric_z[metric][year]
                table[year][metric] = {
                    "value": metric_value.get(metric, {}).get(year),
                    "delta": metric_delta.get(metric, {}).get(year),
                    "z": z,
                    "severity": severity_from_z(z),
                }
    return table


def detect_large_changes(
    financial_history: Optional[List[Dict[str, Any]]],
    ignore_metrics: Iterable[str] = (),
) -> List[MetricAnomaly]:
    """Raw detector (UFVS §1): mọi (năm, metric) có |Z| >= 2.5 (UNUSUAL trở lên).

    ``ignore_metrics`` bỏ qua metric không áp dụng (vd CFO của tổ chức tài chính).
    """
    ignored = set(ignore_metrics)
    table = compute_year_metric_scores(financial_history, ignore_metrics=ignored)
    rows = _sorted_history(financial_history)
    by_year_prev: Dict[int, Dict[str, Any]] = {}
    for i in range(1, len(rows)):
        by_year_prev[int(rows[i]["fiscal_year"])] = rows[i - 1]
    anomalies: List[MetricAnomaly] = []
    for year, metrics in table.items():
        prev_row = by_year_prev.get(year, {})
        curr_row = next((r for r in rows if int(r["fiscal_year"]) == year), {})
        for metric, info in metrics.items():
            if info["severity"] == "NORMAL":
                continue
            p = _num(prev_row.get(metric))
            q = _num(curr_row.get(metric))
            change_pct = ((q - p) / p * 100.0) if (p and q and p > 0) else 0.0
            others_prev = {}
            others_curr = {}
            for other_metric, other_key in METRICS:
                if other_metric == metric or other_metric in ignored:
                    continue
                op = _num(prev_row.get(other_key))
                oq = _num(curr_row.get(other_key))
                if op is not None and oq is not None and op > 0:
                    others_prev[other_metric] = op
                    others_curr[other_metric] = oq
            anomalies.append(MetricAnomaly(
                fiscal_year=year,
                metric=metric,
                previous=p,
                current=q,
                change_pct=round(change_pct, 1),
                detector_status=info["severity"],
                delta=round(float(info["delta"]), 4),
                z_score=round(float(info["z"]), 3),
                severity=info["severity"],
                previous_others=others_prev,
                current_others=others_curr,
            ))
    return anomalies


def detect_unit_jumps(
    financial_history: Optional[List[Dict[str, Any]]],
    ignore_metrics: Iterable[str] = (),
) -> List[MetricAnomaly]:
    """Layer 1 — probable unit error: metric_t/metric_prev > 100x nhưng related không đổi."""
    ignored = set(ignore_metrics)
    rows = _sorted_history(financial_history)
    found: List[MetricAnomaly] = []
    for i in range(1, len(rows)):
        prev, curr = rows[i - 1], rows[i]
        for metric, key in (
            ("revenue", "revenue"),
            ("net_profit", "net_profit"),
            ("operating_cash_flow", "operating_cash_flow"),
        ):
            if metric in ignored:
                continue
            p = _num(prev.get(key))
            q = _num(curr.get(key))
            if p is None or q is None or p <= 0 or q <= 0:
                continue
            if q / p <= UNIT_JUMP_RATIO:
                continue
            others = []
            for other_metric, other_key in (
                ("revenue", "revenue"),
                ("net_profit", "net_profit"),
                ("operating_cash_flow", "operating_cash_flow"),
                ("equity", "equity"),
            ):
                if other_metric == metric or other_metric in ignored:
                    continue
                op = _num(prev.get(other_key))
                oq = _num(curr.get(other_key))
                if op is not None and oq is not None and op > 0:
                    rel = abs((oq - op) / op)
                    others.append(rel)
            if others and max(others) < RELATED_METRIC_MOVE_CAP:
                found.append(MetricAnomaly(
                    fiscal_year=int(curr["fiscal_year"]),
                    metric=metric,
                    previous=p,
                    current=q,
                    change_pct=round((q - p) / p * 100.0, 1),
                    detector_status="UNIT_ERROR",
                    severity="UNIT_ERROR",
                ))
    return found


def numeric_layer_1_checks(
    financial_history: Optional[List[Dict[str, Any]]],
) -> List[Dict[str, Any]]:
    """Layer 1 summary — shares<=0, equity impossible (âm trong khi tài sản dương, ...)."""
    rows = _sorted_history(financial_history)
    issues: List[Dict[str, Any]] = []
    for r in rows:
        year = int(r["fiscal_year"])
        shares = _num(r.get("shares_outstanding"))
        if shares is not None and shares <= 0:
            issues.append({"fiscal_year": year, "metric": "shares_outstanding", "issue": "SHARES_NON_POSITIVE"})
        equity = _num(r.get("equity"))
        revenue = _num(r.get("revenue"))
        if equity is not None and equity < 0 and revenue is not None and revenue > 0:
            issues.append({"fiscal_year": year, "metric": "equity", "issue": "EQUITY_IMPOSSIBLE_NEGATIVE"})
    return issues