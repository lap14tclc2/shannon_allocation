"""
Materiality analysis (feedback.txt §10 / UFVS).

Không phải anomaly nào cũng đáng block valuation. Ước lượng impact của năm anomalous
lên mid-cycle normalization bằng proxy rẻ: so median net margin trong window có/không
có năm đó. (Không re-run toàn engine cho từng năm — đủ để xếp hạng materiality.)

  IV impact < 5%        -> IMMATERIAL
  5–15%                 -> LOW
  15–25%                -> MATERIAL
  >25%                  -> CRITICAL
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

IMMATERIAL_CAP = 0.05
LOW_CAP = 0.15
MATERIAL_CAP = 0.25


def _margin(rows: List[Dict[str, Any]]) -> List[float]:
    """Net margin của từng năm dương hợp lệ."""
    values: List[float] = []
    for r in rows:
        try:
            p = float(r.get("net_profit"))
            rev = float(r.get("revenue"))
        except (TypeError, ValueError):
            continue
        if p > 0 and rev > 0:
            values.append(p / rev)
    return values


def median(values: List[float]) -> Optional[float]:
    ordered = sorted(values)
    if not ordered:
        return None
    n = len(ordered)
    if n % 2 == 1:
        return ordered[n // 2]
    return (ordered[n // 2 - 1] + ordered[n // 2]) / 2.0


def assess_materiality(
    financial_history: List[Dict[str, Any]],
    anomalous_year: int,
    window_years: Optional[List[int]] = None,
) -> Dict[str, Any]:
    """Impact của việc bỏ năm anomalous lên median net margin trong window."""
    rows = [r for r in financial_history if r and r.get("fiscal_year") is not None]
    if window_years:
        rows = [r for r in rows if int(r["fiscal_year"]) in set(window_years)]
    margins = _margin(rows)
    if len(margins) < 3:
        return {"method": "NOT_COMPUTED", "impact_pct": None, "grade": "UNKNOWN"}
    base_median = median(margins)
    without = [m for r, m in zip(rows, margins) if int(r["fiscal_year"]) != anomalous_year]
    if not without or base_median is None or base_median == 0:
        return {"method": "NOT_COMPUTED", "impact_pct": None, "grade": "UNKNOWN"}
    alt_median = median(without)
    impact = abs((alt_median - base_median) / base_median)
    if impact < IMMATERIAL_CAP:
        grade = "IMMATERIAL"
    elif impact < LOW_CAP:
        grade = "LOW"
    elif impact < MATERIAL_CAP:
        grade = "MATERIAL"
    else:
        grade = "CRITICAL"
    return {
        "method": "COUNTERFACTUAL_MARGIN",
        "impact_pct": round(impact * 100.0, 1),
        "grade": grade,
    }


def is_blocking(grade: Optional[str]) -> bool:
    """Anomaly đáng block/partial khi MATERIAL trở lên và chưa resolve."""
    return grade in ("MATERIAL", "CRITICAL")