"""
Cycle extreme detection (feedback.txt §7).

DGC 2021–2022: revenue/profit/cfo cùng tăng, spike 1–3 năm rồi mean-revert về mức
bình thường, không có scale reset vĩnh viễn -> CYCLICAL_EXTREME. PHẢI GIỮ năm peak
trong full-cycle normalization (nếu bỏ peak, median cycle bị bias).
"""
from __future__ import annotations

from typing import Any, Dict, Iterable, List, Optional

SPIKE_MIN_PROFIT = 1.0          # profit tăng >= 100%
SPIKE_MIN_CFO = 1.0             # CFO tăng >= 100%
SPIKE_MAX_SPAN = 3              # spike kéo dài tối đa 3 năm
REVERT_TOLERANCE = 0.4          # profit sau đó phải giảm >= 40% so với đỉnh
REVERT_WINDOW = 3               # trong 3 năm sau
EPS = 1e-9

# Metrics aggregate cho mean-reversion score (feedback.txt §5).
MR_METRICS = (
    ("revenue", "revenue"),
    ("net_profit", "net_profit"),
    ("operating_cash_flow", "operating_cash_flow"),
)


def mean_reversion_score(
    financial_history: Optional[List[Dict[str, Any]]],
    year: int,
    n: int = 2,
) -> float:
    """M_t ∈ [0,1] — mức độ năm sau quay lại median trước anomaly (UFVS feedback.txt §5).

    M = 1 − |X_{t+n} − PreMedian| / (|X_t − PreMedian| + ε), aggregate revenue/profit/CFO.
    Cao khi sau peak, X_{t+n} quay gần mức trước; thấp khi level mới giữ nguyên.
    """
    rows = sorted(
        (h for h in (financial_history or []) if h and h.get("fiscal_year") is not None),
        key=lambda r: int(r.get("fiscal_year") or 0),
    )
    by_year = {int(r["fiscal_year"]): r for r in rows}
    scores = []
    for metric, key in MR_METRICS:
        pre_vals = [float(by_year[y][key]) for y in range(year - 2, year) if y in by_year and by_year[y].get(key) is not None]
        x_t = _num((by_year.get(year) or {}).get(key))
        x_tn = _num((by_year.get(year + n) or {}).get(key))
        if not pre_vals or x_t is None or x_tn is None:
            continue
        pre_m = _median(pre_vals)
        denom = abs(x_t - pre_m) + EPS
        if denom < EPS:
            scores.append(1.0)
            continue
        scores.append(max(0.0, min(1.0, 1.0 - abs(x_tn - pre_m) / denom)))
    return round(sum(scores) / len(scores), 2) if scores else 0.0


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


def detect_cycle_extremes(
    financial_history: Optional[List[Dict[str, Any]]],
    ignore_metrics: Iterable[str] = (),
) -> List[Dict[str, Any]]:
    """Trả list năm được phân loại CYCLICAL_EXTREME.

    Điều kiện:
      - profit (và CFO, revenue) tăng mạnh cùng nhau (profit + cfo đều >= 100%).
      - spike kéo dài <= 3 năm.
      - profit sau đó mean-revert (giảm >= 60% so với đỉnh trong 3 năm sau).
      - không có permanent scale reset (revenue sau đó không giữ ở mức đỉnh mới gấp bội).

    ``ignore_metrics`` bỏ qua metric không áp dụng (vd CFO của tổ chức tài chính).
    """
    ignored = set(ignore_metrics)
    rows = sorted(
        (h for h in (financial_history or []) if h and h.get("fiscal_year") is not None),
        key=lambda r: int(r.get("fiscal_year") or 0),
    )
    extremes: List[Dict[str, Any]] = []
    for i in range(1, len(rows)):
        year = int(rows[i]["fiscal_year"])
        profit_prev = _num(rows[i - 1].get("net_profit"))
        profit_curr = _num(rows[i].get("net_profit"))
        cfo_prev = _num(rows[i - 1].get("operating_cash_flow"))
        cfo_curr = _num(rows[i].get("operating_cash_flow"))
        revenue_prev = _num(rows[i - 1].get("revenue"))
        revenue_curr = _num(rows[i].get("revenue"))
        if not (profit_prev and profit_curr and profit_prev > 0 and profit_curr > 0):
            continue
        profit_change = (profit_curr - profit_prev) / profit_prev
        if profit_change < SPIKE_MIN_PROFIT:
            continue
        # CFO phải xác nhận (nếu có dữ liệu và không bị ignore).
        if "operating_cash_flow" not in ignored and cfo_prev and cfo_curr and cfo_prev > 0 and cfo_curr > 0:
            cfo_change = (cfo_curr - cfo_prev) / cfo_prev
            if cfo_change < SPIKE_MIN_CFO:
                continue
        # revenue cũng tăng (dương) — chu kỳ lên.
        if revenue_prev and revenue_curr and revenue_prev > 0 and revenue_curr <= revenue_prev:
            continue

        # Spike kéo dài <= 3 năm: profit vẫn ở mức cao trong tối đa 3 năm liên tiếp.
        peak_span = 1
        for j in range(i + 1, min(len(rows), i + 1 + SPIKE_MAX_SPAN - 1)):
            pj = _num(rows[j].get("net_profit"))
            if pj is not None and pj > 0 and pj >= profit_prev * 1.5:
                peak_span += 1
            else:
                break
        if peak_span > SPIKE_MAX_SPAN:
            continue

        # Mean reversion: trong 3 năm sau, profit giảm >= 60% so với đỉnh.
        peak_profit = max(
            [float(_num(rows[k].get("net_profit")) or 0) for k in range(i, min(len(rows), i + peak_span))] or [0.0]
        )
        reverted = False
        for j in range(i + peak_span, min(len(rows), i + peak_span + REVERT_WINDOW)):
            pj = _num(rows[j].get("net_profit"))
            if pj is not None and pj > 0 and peak_profit > 0:
                if pj <= peak_profit * (1.0 - REVERT_TOLERANCE):
                    reverted = True
                    break
        if not reverted:
            continue

        # Không permanent scale reset: median revenue 3 năm sau < 2x revenue đỉnh.
        post_revs = [
            float(rows[k]["revenue"])
            for k in range(i + peak_span, min(len(rows), i + peak_span + REVERT_WINDOW))
            if rows[k].get("revenue") is not None
        ]
        scale_reset = False
        if post_revs and revenue_curr:
            if _median(post_revs) >= revenue_curr * 2.0:
                scale_reset = True
        if scale_reset:
            continue

        extremes.append({
            "fiscal_year": year,
            "peak_span_years": peak_span,
            "profit_change_pct": round(profit_change * 100.0, 1),
        })
    return extremes