"""
Universal Financial Validation Standard (UFVS) — resolver pipeline (feedback.txt mới).

Pipeline:
    TCBS facts -> robust Z detection (§1) -> breadth A (§2) -> coherence C (§3)
    -> persistence P (§4) -> mean-reversion M (§5) -> universal decision table (§6)
    -> regime R / cycle CY / bad-data D (§7-9) -> materiality (§10) -> policy (§11)
    -> validation confidence V (§14) -> publication gate (§15)

Taxonomy (feedback.txt §6):
    NORMAL / SUSPICIOUS_ISOLATED / STRUCTURAL_REGIME_BREAK / CYCLICAL_EXTREME /
    EARNINGS_ONE_OFF_CANDIDATE / CASHFLOW_TIMING_CANDIDATE / SHARE_STRUCTURE_CHANGE /
    UNIT_MAPPING_ERROR_CANDIDATE / UNRESOLVED_MATERIAL
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, Iterable, List, Optional

from .anomaly_detector import (
    Z_NORMAL,
    Z_UNUSUAL,
    compute_year_metric_scores,
    detect_unit_jumps,
    numeric_layer_1_checks,
)
from .coherence_checker import pairwise_coherence
from .cycle_detector import detect_cycle_extremes, mean_reversion_score
from .materiality_checker import assess_materiality, is_blocking
from .regime_detector import detect_structural_breaks, latest_comparable_regime, persistence_score

# Operating metrics dùng để phân biệt share-structure / cashflow-timing / earnings-one-off.
OPERATING_METRICS = ("revenue", "net_profit", "operating_cash_flow")
SHARES_CHANGE_MATERIAL = 0.3

# feedback.txt §11 — normalization policy cho từng classification.
USE_MATRIX = {
    "STRUCTURAL_REGIME_BREAK": "SPLIT_REGIME",
    "CYCLICAL_EXTREME": "INCLUDE",
    "SHARE_STRUCTURE_CHANGE": "INCLUDE + PER_SHARE_ADJUST",
    "CASHFLOW_TIMING_CANDIDATE": "DOWNWEIGHT_CFO",
    "EARNINGS_ONE_OFF_CANDIDATE": "DOWNWEIGHT_EARNINGS",
    "SUSPICIOUS_ISOLATED": "EXCLUDE_METRIC_YEAR",
    "UNIT_MAPPING_ERROR_CANDIDATE": "REJECT_FACT",
    "UNRESOLVED_MATERIAL": "BLOCK_MODEL",
}

# Ngưỡng decision (feedback.txt §6): A breadth, C coherence, P persistence.
STRUCTURAL_A_MIN = 0.5
STRUCTURAL_C_MIN = 0.5
STRUCTURAL_P_MIN = 0.6
BAD_DATA_D_MIN = 0.6
ISOLATED_A_MAX = 0.4
ISOLATED_C_MAX = 0.4


@dataclass
class ValidationResult:
    resolutions: List[Dict[str, Any]] = field(default_factory=list)
    regimes: List[Dict[str, Any]] = field(default_factory=list)
    latest_regime_years: Optional[List[int]] = None
    numeric_confidence: str = "HIGH"
    cause_confidence: str = "UNKNOWN"
    unresolved_years: List[int] = field(default_factory=list)
    layer1_issues: List[Dict[str, Any]] = field(default_factory=list)
    data_status: str = "VALID"            # user-test.md §5
    regime_status: str = "SINGLE_REGIME"  # user-test.md §35
    validation_confidence: int = 100      # feedback.txt §14 — 0..100
    validation_confidence_level: str = "HIGH"  # HIGH>=90 MEDIUM 75-89 LOW 60-74 UNVERIFIED<60


def _rows_indexed(financial_history: Optional[List[Dict[str, Any]]]) -> Dict[int, Dict[str, Any]]:
    return {
        int(r["fiscal_year"]): r
        for r in (financial_history or [])
        if r and r.get("fiscal_year") is not None
    }


def _build_event_metrics(year: int, by_year: Dict[int, Dict[str, Any]], z_metrics: Dict[str, Dict[str, float]]) -> List[Dict[str, Any]]:
    prev = by_year.get(year - 1, {})
    curr = by_year.get(year, {})
    metrics = []
    for metric in sorted(z_metrics, key=lambda m: -abs(z_metrics[m].get("z", 0))):
        p = prev.get(metric)
        q = curr.get(metric)
        if p is None or q is None or p <= 0 or q <= 0:
            continue
        change_pct = (q - p) / p * 100.0
        metrics.append({
            "metric": metric,
            "previous": float(p),
            "current": float(q),
            "change_pct": round(change_pct, 1),
        })
    return metrics


def _classify_year(
    year: int,
    by_year: Dict[int, Dict[str, Any]],
    rows: List[Dict[str, Any]],
    z_table: Dict[int, Dict[str, Dict[str, float]]],
    break_years: Dict[int, Dict[str, Any]],
    cycle_years: List[int],
    unit_error_year: bool,
    materiality: Dict[str, Any],
) -> Dict[str, Any]:
    """Phân loại một năm theo decision table UFVS (§6) + ghi đủ score Z/A/C/P/M/R/CY/D."""
    z_by_metric = z_table.get(year, {})
    # Các metric có dữ liệu (kể cả Z thấp) dùng cho A/C.
    z_all = {m: float(info["z"]) for m, info in z_by_metric.items()}
    z_anom = {m: float(info["z"]) for m, info in z_by_metric.items() if info["severity"] != "NORMAL"}
    z_max = max((abs(z) for z in z_all.values()), default=0.0)
    A = len(z_anom) / len(z_all) if z_all else 0.0
    # Coherence C: dùng Z-capped (feedback §3 — magnitude similarity), cắt biên độ quá cao
    # để metric extreme (equity Z~18) không át metric khác.
    capped_z = {m: (1.0 if z > 0 else -1.0) * min(abs(z), Z_UNUSUAL) for m, z in z_all.items()}
    C = pairwise_coherence(capped_z) if capped_z else 0.0
    P = persistence_score(rows, year)
    M = mean_reversion_score(rows, year)
    R = round(A * C * P, 3)
    CY = round(A * C * M * (1.0 - P), 3)
    D = round(min(z_max / Z_UNUSUAL, 1.0) * (1.0 - C) * (1.0 - P), 3)

    classification = "SUSPICIOUS_ISOLATED"
    confidence = "MEDIUM"
    persistent = P >= 0.60
    include = True
    split_regime = False
    exclude_metric: Optional[List[str]] = None
    downweight_metric: Optional[List[str]] = None
    adjust_per_share = False
    block = False
    rule_name = "ISOLATED_METRIC_DISCORDANCE"
    rule_threshold = 0.0
    rule_score = round(1.0 - C, 3)

    anom_metrics = set(z_anom.keys())
    # "Strong" anomaly: |Z| >= 3.5 (STRONG_ANOMALY+) — dùng cho các branch đặc thù
    # (operating "ổn" = KHÔNG strong, tránh blip nhỏ trên baseline ổn định).
    strong_anom = {m for m, info in z_by_metric.items() if abs(float(info["z"])) >= Z_UNUSUAL}
    rev_anom = "revenue" in strong_anom
    profit_anom = "net_profit" in strong_anom
    cfo_anom = "operating_cash_flow" in strong_anom
    shares_anom = "shares_outstanding" in strong_anom

    mat_score = round(float(materiality.get("impact_pct") or 0.0) / 100.0, 3)
    iso_score = round((1.0 - A) * (1.0 - C), 3)

    # 1. Unit/mapping error (Layer 1) — REJECT_FACT.
    if unit_error_year:
        classification = "UNIT_MAPPING_ERROR_CANDIDATE"
        confidence = "LOW"
        include = False
        block = True
        exclude_metric = list(anom_metrics or ["revenue"])
        rule_name = "LAYER1_UNIT_OR_SCALE_JUMP"
        rule_score = 1.0
        rule_threshold = 0.60
    # 2. Structural regime break — MUST be confirmed in break_years (AC-3: Regime Single Source)
    elif year in break_years and R >= 0.08:
        classification = "STRUCTURAL_REGIME_BREAK"
        confidence = break_years[year].get("confidence", "HIGH")
        persistent = True
        split_regime = True
        rule_name = "CONFIRMED_REGIME_LEVEL_SHIFT"
        rule_score = R
        rule_threshold = 0.08
    # 2b. Structural break candidate (level shift not splitting final regime)
    elif R >= 0.15:
        classification = "STRUCTURAL_BREAK_CANDIDATE"
        confidence = "MEDIUM"
        persistent = True
        split_regime = False
        rule_name = "PERSISTENT_LEVEL_SHIFT_CANDIDATE"
        rule_score = R
        rule_threshold = 0.15
    # 3. Cyclical extreme — require genuine multi-metric cycle confirmation (A>=0.4, C>=0.4, CY>=0.05)
    elif CY >= 0.05 and A >= 0.35 and C >= 0.35:
        classification = "CYCLICAL_EXTREME"
        confidence = "HIGH"
        include = True
        rule_name = "COHERENT_MULTI_METRIC_PEAK_WITH_FORWARD_REVERSION"
        rule_score = CY
        rule_threshold = 0.05
    # 4. EARNINGS_ONE_OFF: profit anomaly cao, revenue/CFO ổn (A < 0.4).
    elif profit_anom and not rev_anom and not cfo_anom and A < 0.4:
        classification = "EARNINGS_ONE_OFF_CANDIDATE"
        include = False
        exclude_metric = ["net_profit"]
        rule_name = "ISOLATED_PROFIT_SPIKE_WITHOUT_REVENUE_CFO"
        rule_score = round(1.0 - A, 3)
        rule_threshold = 0.60
    # 5. CASHFLOW_TIMING: CFO anomaly cao, revenue/profit ổn (A < 0.4).
    elif cfo_anom and not rev_anom and not profit_anom and A < 0.4:
        classification = "CASHFLOW_TIMING_CANDIDATE"
        include = True
        downweight_metric = ["operating_cash_flow"]
        rule_name = "WORKING_CAPITAL_OR_CFO_TIMING_DISLOCATION"
        rule_score = round(1.0 - A, 3)
        rule_threshold = 0.60
    # 6. SHARE_STRUCTURE: shares anomaly cao, operating ổn.
    elif shares_anom and not rev_anom and not profit_anom and not cfo_anom:
        classification = "SHARE_STRUCTURE_CHANGE"
        include = True
        adjust_per_share = True
        rule_name = "ISOLATED_CAPITAL_OR_SHARE_CHANGE"
        rule_score = round(1.0 - A, 3)
        rule_threshold = 0.40
    # 7. Unresolved material: coherence thấp + materiality cao -> block model.
    elif is_blocking(materiality.get("grade")) and mat_score >= 0.15 and C < ISOLATED_C_MAX and A < 0.5:
        classification = "UNRESOLVED_MATERIAL"
        confidence = "LOW"
        include = False
        block = True
        rule_name = "MATERIAL_IMPACT_WITH_LOW_COHERENCE"
        rule_score = mat_score
        rule_threshold = 0.15
    # 8. Bad data score cao: extreme jump + related không xác nhận.
    elif D >= BAD_DATA_D_MIN and A < 0.5:
        classification = "UNIT_MAPPING_ERROR_CANDIDATE"
        confidence = "LOW"
        include = False
        block = True
        exclude_metric = list(anom_metrics)
        rule_name = "EXTREME_JUMP_WITH_ZERO_CONFIRMATION"
        rule_score = D
        rule_threshold = BAD_DATA_D_MIN
    # 9. Isolated: Z cao + A thấp + C thấp.
    elif A < ISOLATED_A_MAX and C < ISOLATED_C_MAX and iso_score >= 0.36:
        classification = "SUSPICIOUS_ISOLATED"
        include = not bool(anom_metrics) or False  # exclude affected metric-year
        if not include:
            exclude_metric = list(anom_metrics)
        confidence = "LOW" if not include else "MEDIUM"
        rule_name = "LOW_BREADTH_LOW_COHERENCE_ANOMALY"
        rule_score = iso_score
        rule_threshold = 0.36
    else:
        classification = "SUSPICIOUS_ISOLATED"
        confidence = "LOW"
        include = True
        rule_name = "FALLBACK_ISOLATED_ANOMALY"
        rule_score = iso_score
        rule_threshold = 0.0

    # Determine exact valuation relevance
    latest_row_year = max((int(r["fiscal_year"]) for r in rows if r.get("fiscal_year")), default=year)
    if year == latest_row_year:
        val_relevance = "VALUATION_INPUT"
    elif shares_anom:
        val_relevance = "PER_SHARE_INPUT"
    else:
        val_relevance = "NORMALIZATION_INPUT"

    # Materiality Provenance (AC-2):
    # - If val_relevance == "NOT_USED" or "QUALITY_ONLY": method = "NOT_APPLICABLE", impact_pct = 0.0, grade = "IMMATERIAL"
    # - If materiality was computed via counterfactual margin: method = "COUNTERFACTUAL_MARGIN", impact_pct = float, grade = ...
    # - If cannot be computed: method = "NOT_COMPUTED", impact_pct = None, grade = "UNKNOWN"
    if val_relevance in ("NOT_USED", "QUALITY_ONLY"):
        materiality = {
            "method": "NOT_APPLICABLE",
            "impact_pct": 0.0,
            "grade": "IMMATERIAL",
        }
    elif materiality.get("method") is None:
        materiality = {
            "method": "NOT_COMPUTED" if materiality.get("impact_pct") is None else "COUNTERFACTUAL_MARGIN",
            "impact_pct": materiality.get("impact_pct"),
            "grade": materiality.get("grade", "UNKNOWN"),
        }

    return {
        "fiscal_year": year,
        "detector_status": "EXTREME_ANOMALY" if z_max >= 5.0 else ("STRONG_ANOMALY" if z_max >= 3.5 else "UNUSUAL"),
        "metrics": _build_event_metrics(year, by_year, z_by_metric),
        "resolution": {
            "classification": classification,
            "confidence": confidence,
            "external_verified": False,
            "internal_coherence": round(C, 2),
            "numeric_coherence_score": int(round(C * 100)),
            "anomaly_score": round(z_max, 2),
            "breadth_score": A,
            "coherence_score": C,
            "persistence_score": P,
            "mean_reversion_score": M,
            "regime_score": R,
            "cycle_score": CY,
            "bad_data_score": D,
            "persistent": persistent,
            "classification_rule": rule_name,
            "rule_score": rule_score,
            "rule_threshold": rule_threshold,
            "valuation_relevance": val_relevance,
        },
        "valuation_handling": {
            "include": include,
            "use": USE_MATRIX.get(classification, "INCLUDE"),
            "split_regime": split_regime,
            "exclude_metric": exclude_metric,
            "downweight_metric": downweight_metric,
            "adjust_per_share": adjust_per_share,
            "block": block,
            "fact_rejected": not include or block,
            "model_blocked": block,
            "model_recomputed": True if not include else False,
            "valuation_relevance": val_relevance,
        },
        "materiality": materiality,
    }


def _validation_confidence(
    resolutions: List[Dict[str, Any]],
    layer1_issues: List[Dict[str, Any]],
    has_unit_error: bool,
    rows: List[Dict[str, Any]],
) -> int:
    """feedback.txt §14 — V = 0.2 Dq + 0.2 C + 0.15 Pq + 0.15 Ar + 0.15 Ms + 0.15 Hc."""
    Dq = 0.0 if (layer1_issues or has_unit_error) else 1.0
    coherence_vals = [r["resolution"].get("coherence_score") or 0 for r in resolutions]
    C = max(coherence_vals) if coherence_vals else 0.5
    unresolved = [r for r in resolutions if r["resolution"]["classification"] in ("UNRESOLVED_MATERIAL", "UNIT_MAPPING_ERROR_CANDIDATE")]
    Ar = 0.0 if (resolutions and len(unresolved) == len(resolutions)) else (1.0 - len(unresolved) / len(resolutions) if resolutions else 1.0)
    mat_impacts = [r.get("materiality", {}).get("impact_pct") for r in resolutions if r.get("materiality", {}).get("impact_pct") is not None]
    Ms = 1.0 - (max(mat_impacts) / 100.0 if mat_impacts else 0.0)
    Pq = 0.5 if any(r["resolution"]["classification"] == "STRUCTURAL_REGIME_BREAK" for r in resolutions) else 0.8
    Hc = min(len(rows) / 10.0, 1.0)
    V = 20 * Dq + 20 * C + 15 * Pq + 15 * Ar + 15 * Ms + 15 * Hc
    return int(round(max(0, min(100, V))))


def _confidence_level(v: int) -> str:
    if v >= 90:
        return "HIGH"
    if v >= 75:
        return "MEDIUM"
    if v >= 60:
        return "LOW"
    return "UNVERIFIED"


def run_validation_gate(
    financial_history: Optional[List[Dict[str, Any]]],
    is_financial: bool = False,
) -> ValidationResult:
    """Chạy UFVS pipeline trên lịch sử tài chính (feedback.txt mới).

    ``is_financial=True``: CFO bị bỏ qua (tổ chức tài chính — metric applicability TASK-082).
    """
    ignored: Iterable[str] = ("operating_cash_flow",) if is_financial else ()
    rows = sorted(
        (h for h in (financial_history or []) if h and h.get("fiscal_year") is not None),
        key=lambda r: int(r.get("fiscal_year") or 0),
    )
    if len(rows) < 2:
        return ValidationResult(
            numeric_confidence="HIGH",
            cause_confidence="N/A",
            latest_regime_years=None,
            data_status="INSUFFICIENT",
            regime_status="SINGLE_REGIME",
            validation_confidence=60,
            validation_confidence_level="LOW",
        )

    by_year = _rows_indexed(rows)
    layer1_issues = numeric_layer_1_checks(rows)
    z_table = compute_year_metric_scores(rows, ignore_metrics=ignored)
    unit_jumps = detect_unit_jumps(rows, ignore_metrics=ignored)
    has_unit_error = bool(unit_jumps)

    breaks = detect_structural_breaks(rows)
    break_years = {int(b["year"]): b for b in breaks}
    cycle_years = [int(c["fiscal_year"]) for c in detect_cycle_extremes(rows, ignore_metrics=ignored)]

    # Các năm đưa vào events = union(raw Z-anomalous, cycle years, break years, unit-jump years).
    z_anomalous_years = sorted({
        year for year, metrics in z_table.items()
        if any(info["severity"] != "NORMAL" for info in metrics.values())
    })
    unit_jump_years = sorted({a.fiscal_year for a in unit_jumps})
    event_years = sorted(set(z_anomalous_years) | set(cycle_years) | set(break_years.keys()) | set(unit_jump_years))

    latest = latest_comparable_regime(rows)
    window_years = latest["years"] if latest else None

    resolutions: List[Dict[str, Any]] = []
    for year in event_years:
        mat = assess_materiality(rows, year, window_years)
        resolutions.append(_classify_year(
            year, by_year, rows, z_table, break_years, cycle_years,
            unit_error_year=year in set(unit_jump_years), materiality=mat,
        ))

    unresolved_years = [
        r["fiscal_year"] for r in resolutions
        if r["resolution"]["classification"] == "UNRESOLVED_MATERIAL"
    ]
    suspicious_material = [
        r["fiscal_year"] for r in resolutions
        if r["resolution"]["classification"] == "SUSPICIOUS_ISOLATED"
        and r.get("materiality", {}).get("grade") in ("MATERIAL", "CRITICAL")
    ]

    if unresolved_years or has_unit_error:
        numeric_confidence = "LOW"
    elif suspicious_material:
        numeric_confidence = "MEDIUM"
    else:
        numeric_confidence = "HIGH"

    v = _validation_confidence(resolutions, layer1_issues, has_unit_error, rows)

    if has_unit_error or layer1_issues:
        data_status = "CONFLICTED"
    elif unresolved_years:
        data_status = "SUSPICIOUS"
    elif resolutions:
        data_status = "VALID_WITH_CLASSIFIED_EVENTS"
    else:
        data_status = "VALID"
    regime_status = "SPLIT_REGIME" if latest and len(latest["regimes"]) > 1 else "SINGLE_REGIME"

    return ValidationResult(
        resolutions=resolutions,
        regimes=latest["regimes"] if latest else [],
        latest_regime_years=latest["years"] if latest else None,
        numeric_confidence=numeric_confidence,
        cause_confidence="UNKNOWN" if resolutions else "N/A",
        unresolved_years=unresolved_years,
        layer1_issues=layer1_issues,
        data_status=data_status,
        regime_status=regime_status,
        validation_confidence=v,
        validation_confidence_level=_confidence_level(v),
    )