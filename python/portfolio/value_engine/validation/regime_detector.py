"""
Layer 3 — Structural regime break detection & persistence test (feedback.txt §4-§6).

DGC 2017→2018: revenue/profit/equity/debt/shares cùng nhảy lớn và new level persists
-> STRUCTURAL_REGIME_BREAK. Không cần biết nguyên nhân (TCBS-only); chỉ nói
"thay đổi chế độ/quy mô doanh nghiệp".
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional

# Core scale metrics tham gia phát hiện regime break (khớp ví dụ DGC §14).
REGIME_METRICS = (
    ("revenue", "revenue"),
    ("net_profit", "net_profit"),
    ("equity", "equity"),
    ("total_debt", "total_debt"),
)
# Ngưỡng "large change" cho từng metric trong regime detection.
REGIME_METRIC_THRESHOLD: Dict[str, float] = {
    "revenue": 0.6,
    "net_profit": 0.6,
    "equity": 0.5,
    "total_debt": 0.5,
}
LARGE_CHANGES_REQUIRED = 3
# Persistence: pre_level = median(t-2, t-1); post_level = median(t, t+1, t+2).
PERSISTENCE_SHIFT = 0.5
SHARES_CHANGE_MATERIAL = 0.3
EPS = 1e-9


def persistence_score(
    financial_history: Optional[List[Dict[str, Any]]],
    year: int,
    k: int = 2,
    shift_threshold: float = PERSISTENCE_SHIFT,
) -> float:
    """P_t = Σ w_i I(Shift_i > threshold) / Σ w_i (UFVS feedback.txt §4).

    Pre_i = median(X_{t-k}..X_{t-1}); Post_i = median(X_t..X_{t+k});
    Shift_i = |Post-Pre| / (|Pre| + ε).
    Interpretation: P<0.30 temporary · 0.30–0.60 mixed · >0.60 persistent new regime.
    """
    rows = sorted(
        (h for h in (financial_history or []) if h and h.get("fiscal_year") is not None),
        key=lambda r: int(r.get("fiscal_year") or 0),
    )
    by_year = {int(r["fiscal_year"]): r for r in rows}
    confirm = 0
    total = 0
    for metric, key in REGIME_METRICS:
        pre = [float(by_year[y][key]) for y in range(year - k, year) if y in by_year and by_year[y].get(key) is not None]
        post = [float(by_year[y][key]) for y in range(year, year + k + 1) if y in by_year and by_year[y].get(key) is not None]
        pre_m = _median(pre)
        post_m = _median(post)
        if pre_m is None or post_m is None or pre_m <= 0:
            continue
        total += 1
        shift = abs(post_m - pre_m) / (abs(pre_m) + EPS)
        if shift > shift_threshold:
            confirm += 1
    return round(confirm / total, 2) if total else 0.0


@dataclass
class Regime:
    start_year: int
    end_year: int
    structural_break_year: Optional[int] = None
    break_confidence: str = "LOW"


def _num(value: Any) -> Optional[float]:
    try:
        v = float(value)
        return v if v == v else None
    except (TypeError, ValueError):
        return None


def _median(values: List[float]) -> Optional[float]:
    ordered = sorted(values)
    if not ordered:
        return None
    n = len(ordered)
    if n % 2 == 1:
        return ordered[n // 2]
    return (ordered[n // 2 - 1] + ordered[n // 2]) / 2.0


def year_changes(
    prev: Dict[str, Any],
    curr: Dict[str, Any],
) -> Dict[str, float]:
    out: Dict[str, float] = {}
    for metric, key in REGIME_METRICS:
        p = _num(prev.get(key))
        q = _num(curr.get(key))
        if p is not None and q is not None and p > 0 and q > 0:
            out[metric] = (q - p) / p
    return out


def _persistent_shift(rows: List[Dict[str, Any]], break_idx: int, key: str = "revenue") -> bool:
    """feedback §5: pre_level = median(t-2,t-1), post_level = median(t,t+1,t+2)."""
    pre = [float(rows[j][key]) for j in range(max(0, break_idx - 2), break_idx) if rows[j].get(key) is not None]
    post = [float(rows[j][key]) for j in range(break_idx, min(len(rows), break_idx + 3)) if rows[j].get(key) is not None]
    pre_m = _median(pre)
    post_m = _median(post)
    if pre_m is None or post_m is None or pre_m <= 0:
        return False
    return abs(post_m / pre_m - 1.0) > PERSISTENCE_SHIFT


def detect_structural_breaks(
    financial_history: Optional[List[Dict[str, Any]]],
) -> List[Dict[str, Any]]:
    """Trả list break candidates: {year, large_changes, persistent, confidence}."""
    rows = sorted(
        (h for h in (financial_history or []) if h and h.get("fiscal_year") is not None),
        key=lambda r: int(r.get("fiscal_year") or 0),
    )
    breaks: List[Dict[str, Any]] = []
    for i in range(1, len(rows)):
        changes = year_changes(rows[i - 1], rows[i])
        # Regime break là thay đổi QUY MÔ: bắt buộc revenue đổi lớn (không chỉ profit).
        if abs(changes.get("revenue", 0.0)) < REGIME_METRIC_THRESHOLD["revenue"]:
            continue
        large = sum(
            1 for metric, ch in changes.items()
            if abs(ch) >= REGIME_METRIC_THRESHOLD.get(metric, 0.6)
        )
        if large < LARGE_CHANGES_REQUIRED:
            continue
        persistent = _persistent_shift(rows, i)
        if not persistent:
            continue

        # Post-level phải ỔN ĐỊNH (không phải ramp vào break kế tiếp). DGC 2017 là
        # đáy (626B) rồi 2018 nhảy 6T: max/min post quá lớn -> không phải regime mới.
        post_revs = [
            float(rows[j]["revenue"])
            for j in range(i, min(len(rows), i + 3))
            if rows[j].get("revenue") is not None
        ]
        if len(post_revs) >= 2 and min(post_revs) > 0 and max(post_revs) / min(post_revs) > 2.5:
            continue

        # Cycle-pattern guard: profit tăng >=100% rồi revert >=40% trong 3 năm sau
        # -> CYCLICAL_EXTREME (HPG 2021: 34.5T -> 8.4T), KHÔNG phải regime break.
        profit_prev = _num(rows[i - 1].get("net_profit"))
        profit_curr = _num(rows[i].get("net_profit"))
        if profit_prev and profit_curr and profit_prev > 0 and profit_curr > 0:
            pchange = (profit_curr - profit_prev) / profit_prev
            if pchange >= 1.0:
                peak_profit = profit_curr
                reverted = False
                for j in range(i + 1, min(len(rows), i + 4)):
                    pj = _num(rows[j].get("net_profit"))
                    if pj is not None and pj > 0 and peak_profit > 0 and pj <= peak_profit * 0.6:
                        reverted = True
                        break
                if reverted:
                    continue

        shares_old = _num(rows[i - 1].get("shares_outstanding"))
        shares_new = _num(rows[i].get("shares_outstanding"))
        shares_changed = (
            shares_old is not None and shares_new is not None and shares_old > 0
            and abs(shares_new / shares_old - 1.0) >= SHARES_CHANGE_MATERIAL
        )
        equity_also_jumps = abs(changes.get("equity", 0.0)) >= REGIME_METRIC_THRESHOLD["equity"]
        if large >= 4 or (large >= 3 and (shares_changed or equity_also_jumps)):
            confidence = "HIGH"
        else:
            confidence = "MEDIUM"
        breaks.append({
            "year": int(rows[i]["fiscal_year"]),
            "large_changes": large,
            "persistent": persistent,
            "shares_changed": shares_changed,
            "confidence": confidence,
        })
    return breaks


def build_regimes(financial_history: Optional[List[Dict[str, Any]]]) -> List[Regime]:
    """Split history thành các regime tại các structural break.

    Break tại năm B chia: Regime trước = [start, B-1], Regime sau bắt đầu từ B.
    Chỉ break khi có năm trước đó (i>=1) và persistence. Break ở năm đầu lịch sử bị bỏ.
    """
    rows = sorted(
        (h for h in (financial_history or []) if h and h.get("fiscal_year") is not None),
        key=lambda r: int(r.get("fiscal_year") or 0),
    )
    if not rows:
        return []
    years = [int(r["fiscal_year"]) for r in rows]
    breaks = detect_structural_breaks(financial_history)
    break_years = sorted({int(b["year"]) for b in breaks if int(b["year"]) > years[0]})
    regimes: List[Regime] = []
    start = years[0]
    for by in break_years:
        if by <= start:
            continue
        regimes.append(Regime(
            start_year=start,
            end_year=by - 1,
            structural_break_year=by,
            break_confidence=next((b["confidence"] for b in breaks if int(b["year"]) == by), "LOW"),
        ))
        start = by
    regimes.append(Regime(
        start_year=start,
        end_year=years[-1],
        structural_break_year=None,
        break_confidence="",
    ))
    return regimes


def latest_comparable_regime(
    financial_history: Optional[List[Dict[str, Any]]],
) -> Optional[Dict[str, Any]]:
    """Regime chứa năm mới nhất — dùng cho mid-cycle normalization (feedback §6)."""
    regimes = build_regimes(financial_history)
    if not regimes:
        return None
    latest = regimes[-1]
    return {
        "label": chr(ord("A") + len(regimes) - 1),
        "start_year": latest.start_year,
        "end_year": latest.end_year,
        "structural_break_year": latest.structural_break_year,
        "break_confidence": latest.break_confidence,
        "years": list(range(latest.start_year, latest.end_year + 1)),
        "regimes": [
            {
                "label": chr(ord("A") + idx),
                "start_year": r.start_year,
                "end_year": r.end_year,
                "structural_break_year": r.structural_break_year,
                "break_confidence": r.break_confidence,
            }
            for idx, r in enumerate(regimes)
        ],
    }