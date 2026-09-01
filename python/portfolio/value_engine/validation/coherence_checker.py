"""
Layer 2 — Cross-metric coherence (feedback.txt §3).

Không nhìn một chỉ tiêu đơn lẻ. Nếu 1 metric biến động lớn nhưng phần còn lại không
xác nhận -> không nên gọi là business event. Điểm coherence 0..1 = tỷ lệ các core
metric xác nhận cùng hướng + biên độ tương xứng với move lớn nhất.
"""
from __future__ import annotations

from typing import Any, Dict, Iterable, List, Optional

COHERENCE_METRICS = (
    ("revenue", "revenue"),
    ("net_profit", "net_profit"),
    ("operating_cash_flow", "operating_cash_flow"),
    ("equity", "equity"),
    ("total_debt", "total_debt"),
)

# Biên độ tối thiểu của một metric để được coi là "xác nhận" move.
CONFIRM_MIN_MOVE = 0.2


def _rel(p: float, q: float) -> Optional[float]:
    if p is None or q is None or p == 0:
        return None
    return (q - p) / p


def year_relative_changes(
    prev: Dict[str, Any],
    curr: Dict[str, Any],
    exclude: Iterable[str] = (),
) -> Dict[str, float]:
    """Relative change của từng core metric giữa 2 năm (chỉ năm dương)."""
    excluded = set(exclude)
    out: Dict[str, float] = {}
    for metric, key in COHERENCE_METRICS:
        if metric in excluded:
            continue
        try:
            p = float(prev.get(key))
            q = float(curr.get(key))
        except (TypeError, ValueError):
            continue
        if p > 0 and q > 0:
            out[metric] = (q - p) / p
    return out


def coherence_score(
    prev: Dict[str, Any],
    curr: Dict[str, Any],
    exclude: Iterable[str] = (),
) -> float:
    """0..1 — mức độ các metric đi cùng nhau.

    Lấy move lớn nhất làm "dominant". Đếm số metric cùng dấu và có |move| >= 20%
    của |dominant|, chia cho tổng số metric có dữ liệu. Coherence cao khi cả
    revenue/profit/cfo/equity/debt cùng tăng (DGC 2018) thay vì chỉ 1 metric.
    """
    changes = year_relative_changes(prev, curr, exclude=exclude)
    if not changes:
        return 0.0
    dominant = max(changes.values(), key=abs)
    if dominant == 0:
        return 0.0
    sign = 1.0 if dominant > 0 else -1.0
    magnitude = abs(dominant)
    confirm = 0
    for value in changes.values():
        if value == 0:
            continue
        same_direction = (value > 0) == (sign > 0)
        proportional = abs(value) >= magnitude * CONFIRM_MIN_MOVE
        if same_direction and proportional:
            confirm += 1
    return round(confirm / len(changes), 2)


def internal_coherence_flag(coherence: float) -> str:
    """Phân loại coherence thành nhãn gọn (feedback §10 resolution.internal_coherence)."""
    if coherence >= 0.7:
        return "HIGH"
    if coherence >= 0.4:
        return "MEDIUM"
    return "LOW"


import math  # noqa: E402

# feedback.txt §3 — magnitude similarity scale: exp(-|Zi-Zj|/k).
MAGNITUDE_SIMILARITY_K = 2.0
COHERENCE_LOW = 0.39
COHERENCE_MEDIUM = 0.69


def pairwise_coherence(z_scores: Dict[str, float]) -> float:
    """C_t = Σ_{i<j} w_ij · DirectionMatch(i,j) · MagnitudeSimilarity(i,j) / Σ w_ij.

    DirectionMatch = 1 nếu Z_i, Z_j cùng dấu (cùng chiều), 0 nếu ngược.
    MagnitudeSimilarity = exp(-|Zi - Zj| / k).
    Output: 0..1; <0.40 LOW, 0.40–0.69 MEDIUM, >=0.70 HIGH (feedback.txt §3).
    """
    metrics = list(z_scores.keys())
    pairs = [(metrics[i], metrics[j]) for i in range(len(metrics)) for j in range(i + 1, len(metrics))]
    if not pairs:
        return 0.0
    total = 0.0
    weight_sum = 0.0
    for a, b in pairs:
        za = float(z_scores[a])
        zb = float(z_scores[b])
        if za == 0 or zb == 0:
            continue
        direction = 1.0 if (za > 0) == (zb > 0) else 0.0
        magnitude = math.exp(-abs(za - zb) / MAGNITUDE_SIMILARITY_K)
        total += direction * magnitude
        weight_sum += 1.0
    return round(total / weight_sum, 2) if weight_sum else 0.0


def coherence_class(c: float) -> str:
    if c >= 0.70:
        return "HIGH"
    if c >= 0.40:
        return "MEDIUM"
    return "LOW"


def numeric_coherence_score(
    prev: Dict[str, Any],
    curr: Dict[str, Any],
    persistent: bool = False,
) -> int:
    """numeric_coherence_score 0..100 (user-test.md §9).

    5 component × 20:
      - Revenue confirmation       20
      - Profit confirmation        20
      - Cash-flow confirmation     20
      - Balance-sheet confirmation 20 (equity + debt)
      - Persistence confirmation   20

    Threshold: >=80 HIGH · 60–79 MEDIUM · <60 LOW.
    """
    changes = year_relative_changes(prev, curr)
    if not changes:
        return 0
    dominant = max(changes.values(), key=abs)
    if dominant == 0:
        return 0
    sign = 1.0 if dominant > 0 else -1.0
    magnitude = abs(dominant)

    def _confirmed(metric: str) -> bool:
        value = changes.get(metric)
        if value is None or value == 0:
            return False
        same_direction = (value > 0) == (sign > 0)
        proportional = abs(value) >= magnitude * CONFIRM_MIN_MOVE
        return same_direction and proportional

    score = 0
    if _confirmed("revenue"):
        score += 20
    if _confirmed("net_profit"):
        score += 20
    if _confirmed("operating_cash_flow"):
        score += 20
    balance = [changes.get("equity"), changes.get("total_debt")]
    if any(v is not None for v in balance) and all(v is not None and ((v > 0) == (sign > 0)) and abs(v) >= magnitude * CONFIRM_MIN_MOVE for v in balance if v is not None):
        score += 20
    elif balance and all(v is not None for v in balance) and any(((v > 0) == (sign > 0)) and abs(v) >= magnitude * CONFIRM_MIN_MOVE for v in balance):
        score += 10
    if persistent:
        score += 20
    return score


def best_anchor_history(
    financial_history: List[Dict[str, Any]],
) -> Optional[Dict[str, Any]]:
    """Year tiêu biểu nhất (revenue lớn nhất) dùng làm anchor tham chiếu."""

    def _key(r: Dict[str, Any]) -> float:
        try:
            return float(r.get("revenue") or 0)
        except (TypeError, ValueError):
            return 0.0

    if not financial_history:
        return None
    return max(financial_history, key=_key)