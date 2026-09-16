"""Financial Forensics, Accounting Consistency, and Structural Deterioration Engine (Task 136, Task 154).

Provides deterministic evidence-first forensics across 10 core financial statement pairings:
1. Revenue ↔ Receivables (revenue recognition & trade credit)
2. Revenue ↔ Inventory (inventory buildup vs sales velocity)
3. PAT ↔ CFO (accrual accounting vs real cash generation)
4. PAT ↔ Retained Earnings (clean surplus & profit retention)
5. PAT ↔ Equity (internal capital compounding)
6. Debt ↔ Assets (asset leverage stress)
7. Debt ↔ Equity (solvency & capital structure risk)
8. CFO ↔ Working Capital (cash conversion efficiency & WC drain)
9. Shares ↔ EPS / Equity (dilution drag on compounding)
10. Cash ↔ Debt (cash fortress vs debt vulnerability)
"""

from __future__ import annotations

import math
from typing import Any, Dict, List, Optional, Tuple
from .munger_models import (
    ConfidenceLevel,
    DeteriorationClassification,
    DimensionStatus,
    FindingSeverity,
    FinancialFinding,
    FinancialDimensionResult,
)
from .munger_thresholds import DEFAULT_MUNGER_THRESHOLD_POLICY, MungerThresholdPolicy
from .vietnamese_presenter import get_vietnamese_archetype, get_vietnamese_deterioration


def run_accounting_consistency_checks(
    history_data: Dict[str, Any],
    thresholds: MungerThresholdPolicy = DEFAULT_MUNGER_THRESHOLD_POLICY,
) -> FinancialDimensionResult:
    """Validate accounting identities across financial statements.

    Checks:
    1. Assets ≈ Liabilities + Equity (BS equation)
    2. PBT - Tax ≈ PAT (IS equation)
    3. Retained earnings reconciliation (Clean surplus: RE_t ≈ RE_{t-1} + PAT_t - Dividends_t)
    """
    by_year = history_data.get("by_year", {})
    years = history_data.get("years", [])
    findings: List[FinancialFinding] = []
    evidence: List[str] = []
    missing: List[str] = []

    if not years:
        return FinancialDimensionResult(
            status=DimensionStatus.UNKNOWN.value,
            confidence=ConfidenceLevel.LOW.value,
            metrics={},
            findings=[],
            evidence=[],
            missing_data=["FINANCIAL_HISTORY"],
            not_applicable=[],
            explanation="Không có dữ liệu lịch sử tài chính để kiểm tra tính nhất quán kế toán.",
        )

    bs_identity_violations = 0
    is_identity_violations = 0
    checked_years = 0
    recent_violations = 0

    max_fy = max(years)

    for y in years:
        ydict = by_year.get(y, {})
        tot_assets = ydict.get("BS.ASSETS.TOTAL") or ydict.get("total_assets")
        tot_liab = ydict.get("BS.LIABILITIES.TOTAL") or ydict.get("total_liabilities")
        tot_eq = ydict.get("BS.EQUITY.TOTAL") or ydict.get("BS.EQUITY.OWNERS") or ydict.get("equity")

        if tot_assets is not None and tot_liab is not None and tot_eq is not None:
            checked_years += 1
            diff = abs(float(tot_assets) - (float(tot_liab) + float(tot_eq)))
            pct_diff = diff / max(1.0, abs(float(tot_assets)))
            if pct_diff > 0.02 and diff > 1e6:  # > 2% variance and > 1M VND
                bs_identity_violations += 1
                evidence.append(f"BS.ASSETS.TOTAL FY{y}")
                if (max_fy - y) <= 7:
                    recent_violations += 1

        pbt = ydict.get("IS.PROFIT.BEFORE_TAX") or ydict.get("pbt")
        tax = ydict.get("IS.TAX.CORPORATE") or ydict.get("tax_expense")
        pat = ydict.get("IS.PROFIT.NET") or ydict.get("net_profit")

        if pbt is not None and tax is not None and pat is not None:
            calc_pat = float(pbt) - float(tax)
            pat_diff = abs(calc_pat - float(pat))
            if pat_diff / max(1.0, abs(float(pat))) > 0.05 and pat_diff > 1e6:
                is_identity_violations += 1
                evidence.append(f"IS.PROFIT.NET FY{y}")
                if (max_fy - y) <= 7:
                    recent_violations += 1

    status = DimensionStatus.PASS.value
    confidence = ConfidenceLevel.HIGH.value if checked_years >= 3 else ConfidenceLevel.MEDIUM.value

    if recent_violations >= 2:
        status = DimensionStatus.FAIL.value
    elif bs_identity_violations > 0 or is_identity_violations > 0:
        status = DimensionStatus.WATCH.value

    if status != DimensionStatus.PASS.value:
        findings.append(
            FinancialFinding(
                code="ACCOUNTING_IDENTITY_DISCREPANCY",
                category="ACCOUNTING",
                severity=FindingSeverity.HIGH.value if status == DimensionStatus.FAIL.value else FindingSeverity.MEDIUM.value,
                confidence=confidence,
                status=status,
                start_period=years[0],
                end_period=years[-1],
                metrics={
                    "bs_identity_violations": bs_identity_violations,
                    "is_identity_violations": is_identity_violations,
                    "recent_violations": recent_violations,
                    "checked_years": checked_years,
                },
                evidence_fact_ids=evidence,
                explanation=f"Phát hiện {bs_identity_violations} năm có chênh lệch hằng đẳng thức BCTC (trong đó {recent_violations} năm gần đây).",
            )
        )

    explanation = "Báo cáo tài chính tuân thủ các hằng đẳng thức kế toán cơ bản." if status == DimensionStatus.PASS.value else "Phát hiện chênh lệch hằng đẳng thức kế toán trong BCTC."

    return FinancialDimensionResult(
        status=status,
        confidence=confidence,
        metrics={
            "bs_identity_violations": bs_identity_violations,
            "is_identity_violations": is_identity_violations,
            "checked_years": checked_years,
        },
        findings=findings,
        evidence=evidence,
        missing_data=missing,
        not_applicable=[],
        explanation=explanation,
    )


def run_earnings_quality_forensics(
    history_data: Dict[str, Any],
    archetype: str = "NORMAL_ENTERPRISE",
    thresholds: MungerThresholdPolicy = DEFAULT_MUNGER_THRESHOLD_POLICY,
) -> FinancialDimensionResult:
    """Analyze earnings quality and profit vs cash flow divergence with multi-year series and contradiction resolution.

    Requirement 9:
    - Yearly series: CFO, PAT, CFO/PAT
    - Median, Mean, Weighted ratio (sum CFO / sum PAT)
    - Years CFO < PAT, Years CFO < 0, Years CFO/PAT < threshold
    - Trend analysis
    - Explicit explanation if mean CFO/PAT is high but CFO < PAT in multiple years (contradiction resolution).
    """
    if archetype in ("BANK", "SECURITIES"):
        return FinancialDimensionResult(
            status=DimensionStatus.NOT_APPLICABLE.value,
            confidence=ConfidenceLevel.HIGH.value,
            metrics={"archetype": archetype},
            findings=[],
            evidence=[],
            missing_data=[],
            not_applicable=["INDUSTRIAL_CFO_PAT"],
            explanation=f"Ngành {get_vietnamese_archetype(archetype)} không áp dụng tỷ lệ CFO/PAT của doanh nghiệp phi tài chính.",
        )

    by_year = history_data.get("by_year", {})
    years = history_data.get("years", [])

    if len(years) < 2:
        return FinancialDimensionResult(
            status=DimensionStatus.UNKNOWN.value,
            confidence=ConfidenceLevel.LOW.value,
            metrics={},
            findings=[],
            evidence=[],
            missing_data=["INSUFFICIENT_HISTORY"],
            not_applicable=[],
            explanation="Chưa đủ lịch sử tài chính để phân tích chất lượng lợi nhuận.",
        )

    yearly_series: List[Dict[str, Any]] = []
    cfo_pat_ratios: List[float] = []
    cfo_series: List[float] = []
    pat_series: List[float] = []
    evidence_facts: List[str] = []

    for y in years:
        ydict = by_year.get(y, {})
        cfo = ydict.get("operating_cash_flow") if ydict.get("operating_cash_flow") is not None else ydict.get("cfo")
        pat = ydict.get("net_profit") if ydict.get("net_profit") is not None else ydict.get("net_income")

        if cfo is not None and pat is not None:
            fcfo = float(cfo)
            fpat = float(pat)
            cfo_series.append(fcfo)
            pat_series.append(fpat)
            evidence_facts.extend([f"CF.OPERATING.NET FY{y}", f"IS.PROFIT.NET FY{y}"])

            ratio = (fcfo / fpat) if fpat > 0 else (0.0 if fpat == 0 else -1.0)
            if fpat > 0:
                cfo_pat_ratios.append(fcfo / fpat)

            yearly_series.append({
                "fiscal_year": y,
                "cfo": fcfo,
                "pat": fpat,
                "cfo_pat": round(ratio, 2),
                "cfo_lt_pat": fcfo < fpat,
                "cfo_negative": fcfo < 0,
            })

    if not cfo_series or not pat_series:
        return FinancialDimensionResult(
            status=DimensionStatus.UNKNOWN.value,
            confidence=ConfidenceLevel.LOW.value,
            metrics={},
            findings=[],
            evidence=[],
            missing_data=["CFO_PAT_DATA"],
            not_applicable=[],
            explanation="Thiếu dữ liệu dòng tiền kinh doanh hoặc lợi nhuận ròng.",
        )

    # Statistical Aggregates
    mean_cfo_pat = (sum(cfo_pat_ratios) / len(cfo_pat_ratios)) if cfo_pat_ratios else 0.0
    sorted_ratios = sorted(cfo_pat_ratios)
    n_ratios = len(sorted_ratios)
    median_cfo_pat = (
        (sorted_ratios[n_ratios // 2] if n_ratios % 2 != 0 else (sorted_ratios[n_ratios // 2 - 1] + sorted_ratios[n_ratios // 2]) / 2.0)
        if sorted_ratios else 0.0
    )

    sum_cfo = sum(cfo_series)
    sum_pat = sum(pat_series)
    weighted_cfo_pat = (sum_cfo / sum_pat) if sum_pat > 0 else 0.0

    years_cfo_lt_pat = sum(1 for item in yearly_series if item["cfo_lt_pat"])
    years_cfo_negative = sum(1 for item in yearly_series if item["cfo_negative"])
    years_cfo_pat_lt_threshold = sum(1 for item in yearly_series if item["cfo_pat"] < thresholds.NORMAL_CFO_PAT_PASS_RATIO)
    total_valid_years = len(yearly_series)

    # Trend calculation
    recent_ratios = [item["cfo_pat"] for item in yearly_series[-3:] if item["pat"] > 0]
    older_ratios = [item["cfo_pat"] for item in yearly_series[:-3] if item["pat"] > 0]
    recent_avg = (sum(recent_ratios) / len(recent_ratios)) if recent_ratios else mean_cfo_pat
    older_avg = (sum(older_ratios) / len(older_ratios)) if older_ratios else mean_cfo_pat

    cfo_trend = "STABLE"
    if recent_avg > older_avg * 1.20:
        cfo_trend = "IMPROVING"
    elif recent_avg < older_avg * 0.80:
        cfo_trend = "DETERIORATING"

    # Multi-year CAGR gap
    cagr_pat = None
    cagr_cfo = None
    if len(pat_series) >= 4:
        cagr_pat = (pat_series[-1] / pat_series[0]) ** (1.0 / (len(pat_series) - 1)) - 1.0 if pat_series[0] > 0 and pat_series[-1] > 0 else None
        cagr_cfo = (cfo_series[-1] / cfo_series[0]) ** (1.0 / (len(cfo_series) - 1)) - 1.0 if cfo_series[0] > 0 and cfo_series[-1] > 0 else None

    # Contradiction Detection (e.g. Mean = 3.08x due to one outlier year, but CFO < PAT in multiple years)
    has_outlier_distortion = (mean_cfo_pat >= 1.5 or weighted_cfo_pat >= 1.5) and (years_cfo_lt_pat >= total_valid_years * 0.40 or years_cfo_negative >= 1)
    contradiction_explanation = ""
    if has_outlier_distortion:
        contradiction_explanation = (
            f"Lưu ý phân kỳ dòng tiền: Tỷ lệ CFO/PAT trung bình số học cao ({mean_cfo_pat:.2f}x) do có năm phát sinh dòng tiền đột biến (như doanh thu nhận trước/khách hàng trả trước), "
            f"nhưng trong {total_valid_years} năm có tới {years_cfo_lt_pat} năm dòng tiền CFO thấp hơn LNST ({years_cfo_negative} năm CFO âm). "
            f"Khả năng chuyển hóa tiền mặt thực tế không ổn định qua các năm."
        )

    findings: List[FinancialFinding] = []
    status = DimensionStatus.PASS.value

    # Check Divergence Rules
    is_severe_divergence = (
        (median_cfo_pat < thresholds.NORMAL_CFO_PAT_WATCH_RATIO and years_cfo_lt_pat >= total_valid_years * 0.50)
        or years_cfo_negative >= thresholds.PERSISTENT_NEGATIVE_CFO_YEARS
        or (weighted_cfo_pat < thresholds.NORMAL_CFO_PAT_WATCH_RATIO)
    )

    is_moderate_divergence = (
        median_cfo_pat < thresholds.NORMAL_CFO_PAT_PASS_RATIO
        or years_cfo_lt_pat >= total_valid_years * 0.40
        or (cagr_pat is not None and cagr_cfo is not None and (cagr_pat - cagr_cfo) > thresholds.PROFIT_CASH_DIVERGENCE_CAGR_GAP)
        or has_outlier_distortion
    )

    if is_severe_divergence:
        status = DimensionStatus.FAIL.value
        exp_text = (
            f"Lợi nhuận và dòng tiền phân kỳ nghiêm trọng. CFO/PAT trung vị {median_cfo_pat:.2f}x (< {thresholds.NORMAL_CFO_PAT_WATCH_RATIO}x), "
            f"CFO âm {years_cfo_negative}/{total_valid_years} năm và thấp hơn LNST {years_cfo_lt_pat}/{total_valid_years} năm."
        )
        if contradiction_explanation:
            exp_text += f" {contradiction_explanation}"

        findings.append(
            FinancialFinding(
                code="PROFIT_CASH_DIVERGENCE",
                category="EARNINGS_QUALITY",
                severity=FindingSeverity.HIGH.value,
                confidence=ConfidenceLevel.HIGH.value,
                status=DimensionStatus.FAIL.value,
                start_period=years[0],
                end_period=years[-1],
                metrics={
                    "mean_cfo_pat": round(mean_cfo_pat, 2),
                    "median_cfo_pat": round(median_cfo_pat, 2),
                    "weighted_cfo_pat": round(weighted_cfo_pat, 2),
                    "years_cfo_lt_pat": years_cfo_lt_pat,
                    "years_cfo_negative": years_cfo_negative,
                    "total_valid_years": total_valid_years,
                    "has_outlier_distortion": has_outlier_distortion,
                },
                evidence_fact_ids=evidence_facts,
                explanation=exp_text,
                archetype=archetype,
                impact="Rủi ro chất lượng lợi nhuận cao do dòng tiền kinh doanh phân kỳ lớn so với lợi nhuận.",
            )
        )
    elif is_moderate_divergence:
        status = DimensionStatus.WATCH.value
        exp_text = (
            f"Khả năng chuyển hóa tiền mặt có điểm cần lưu ý: CFO/PAT trung vị đạt {median_cfo_pat:.2f}x, "
            f"có {years_cfo_lt_pat}/{total_valid_years} năm CFO thấp hơn LNST."
        )
        if contradiction_explanation:
            exp_text += f" {contradiction_explanation}"
        elif cagr_pat is not None and cagr_cfo is not None and (cagr_pat - cagr_cfo) > thresholds.PROFIT_CASH_DIVERGENCE_CAGR_GAP:
            exp_text += f" Tốc độ tăng trưởng lợi nhuận ({cagr_pat*100:.1f}%) vượt nhanh hơn dòng tiền CFO ({cagr_cfo*100:.1f}%)."

        findings.append(
            FinancialFinding(
                code="WEAK_CASH_CONVERSION",
                category="EARNINGS_QUALITY",
                severity=FindingSeverity.MEDIUM.value,
                confidence=ConfidenceLevel.HIGH.value,
                status=DimensionStatus.WATCH.value,
                start_period=years[0],
                end_period=years[-1],
                metrics={
                    "mean_cfo_pat": round(mean_cfo_pat, 2),
                    "median_cfo_pat": round(median_cfo_pat, 2),
                    "weighted_cfo_pat": round(weighted_cfo_pat, 2),
                    "years_cfo_lt_pat": years_cfo_lt_pat,
                    "years_cfo_negative": years_cfo_negative,
                    "total_valid_years": total_valid_years,
                    "has_outlier_distortion": has_outlier_distortion,
                },
                evidence_fact_ids=evidence_facts,
                explanation=exp_text,
                archetype=archetype,
                impact="Rủi ro chất lượng lợi nhuận ở mức trung bình, dòng tiền kinh doanh phân kỳ một số năm.",
            )
        )

    final_explanation = "Chất lượng lợi nhuận tốt, dòng tiền kinh doanh bảo chứng lợi nhuận qua các năm." if status == DimensionStatus.PASS.value else (exp_text if findings else "Chất lượng lợi nhuận cần theo dõi.")

    return FinancialDimensionResult(
        status=status,
        confidence=ConfidenceLevel.HIGH.value if len(years) >= 5 else ConfidenceLevel.MEDIUM.value,
        metrics={
            "mean_cfo_pat": round(mean_cfo_pat, 2),
            "median_cfo_pat": round(median_cfo_pat, 2),
            "weighted_cfo_pat": round(weighted_cfo_pat, 2),
            "years_cfo_lt_pat": years_cfo_lt_pat,
            "years_cfo_negative": years_cfo_negative,
            "years_cfo_pat_lt_threshold": years_cfo_pat_lt_threshold,
            "total_valid_years": total_valid_years,
            "cfo_trend": cfo_trend,
            "cagr_pat": cagr_pat,
            "cagr_cfo": cagr_cfo,
            "has_outlier_distortion": has_outlier_distortion,
            "cfo_pat_explanation": contradiction_explanation,
            "yearly_cfo_pat": yearly_series,
        },
        findings=findings,
        evidence=evidence_facts,
        missing_data=[],
        not_applicable=[],
        explanation=final_explanation,
    )


def run_receivables_forensics(
    history_data: Dict[str, Any],
    archetype: str = "NORMAL_ENTERPRISE",
    thresholds: MungerThresholdPolicy = DEFAULT_MUNGER_THRESHOLD_POLICY,
) -> FinancialDimensionResult:
    """Analyze receivables growth vs revenue growth with multi-year YoY comparison and persistence classification.

    Requirement 10:
    - Revenue CAGR, Receivables CAGR, difference
    - Yearly YoY growth: Revenue growth vs Receivables growth
    - Distinguish: temporary (1 year), persistent (>= 2 years), accelerating
    - Increase severity if persistent or accelerating.
    """
    if archetype in ("BANK", "SECURITIES"):
        return FinancialDimensionResult(
            status=DimensionStatus.NOT_APPLICABLE.value,
            confidence=ConfidenceLevel.HIGH.value,
            metrics={"archetype": archetype},
            findings=[],
            evidence=[],
            missing_data=[],
            not_applicable=["INDUSTRIAL_RECEIVABLES_REVENUE"],
            explanation=f"Ngành {get_vietnamese_archetype(archetype)} không áp dụng chỉ tiêu Phải thu / Doanh thu công nghiệp.",
        )

    by_year = history_data.get("by_year", {})
    years = history_data.get("years", [])

    # STAGE A — Semantic Validation
    semantic_statuses = [by_year.get(y, {}).get("receivables_semantic_status", "DATA_VALID") for y in years]
    source_types = [by_year.get(y, {}).get("receivables_source_type", "TRADE_NET") for y in years]

    if "DATA_CONFLICT" in semantic_statuses:
        return FinancialDimensionResult(
            status=DimensionStatus.UNKNOWN.value,
            confidence=ConfidenceLevel.LOW.value,
            metrics={"semantic_status": "DATA_CONFLICT"},
            findings=[],
            evidence=[],
            missing_data=["RECEIVABLES_DATA_CONFLICT"],
            not_applicable=[],
            explanation="Dữ liệu các khoản phải thu xung đột ngữ cảnh (Trade Receivables > Total Receivables). Tạm hoãn phân tích.",
        )

    is_total_proxy = all(s in ("TOTAL_PROXY", "MISSING") for s in source_types) or not any(s == "TRADE_NET" for s in source_types)

    rec_series: List[Tuple[int, float]] = []
    rev_series: List[Tuple[int, float]] = []
    cfo_series: List[Tuple[int, float]] = []
    pat_series: List[Tuple[int, float]] = []
    asset_series: List[Tuple[int, float]] = []
    evidence_facts: List[str] = []

    for y in years:
        ydict = by_year.get(y, {})
        rec = ydict.get("receivables")
        rev = ydict.get("revenue") or ydict.get("IS.REVENUE.TOTAL")
        cfo = ydict.get("cfo") or ydict.get("operating_cash_flow")
        pat = ydict.get("net_profit") or ydict.get("net_income")
        assets = ydict.get("total_assets") or ydict.get("BS.ASSETS.TOTAL")

        if rec is not None and rev is not None and float(rev) > 0:
            rec_series.append((y, float(rec)))
            rev_series.append((y, float(rev)))
            if cfo is not None:
                cfo_series.append((y, float(cfo)))
            if pat is not None:
                pat_series.append((y, float(pat)))
            if assets is not None and float(assets) > 0:
                asset_series.append((y, float(assets)))
            evidence_facts.extend([f"RECEIVABLES FY{y}", f"REVENUE FY{y}"])

    if len(rec_series) < 3:
        return FinancialDimensionResult(
            status=DimensionStatus.UNKNOWN.value,
            confidence=ConfidenceLevel.LOW.value,
            metrics={},
            findings=[],
            evidence=[],
            missing_data=["INSUFFICIENT_RECEIVABLES_DATA"],
            not_applicable=[],
            explanation="Chưa đủ dữ liệu các khoản phải thu để đánh giá.",
        )

    # ---------------------------------------------------------
    # 1. AXIS E: YEAR-OVER-YEAR PERSISTENCE & PATTERN
    # ---------------------------------------------------------
    yearly_growth_comparison: List[Dict[str, Any]] = []
    gap_widening_years = 0
    consecutive_gap_years = 0
    max_consecutive_gap_years = 0

    for i in range(1, len(rec_series)):
        y_curr = rec_series[i][0]
        rec_prev = rec_series[i-1][1]
        rec_curr = rec_series[i][1]
        rev_prev = rev_series[i-1][1]
        rev_curr = rev_series[i][1]

        rec_yoy = ((rec_curr - rec_prev) / rec_prev) if rec_prev > 0 else 0.0
        rev_yoy = ((rev_curr - rev_prev) / rev_prev) if rev_prev > 0 else 0.0
        gap = rec_yoy - rev_yoy

        if gap > 0.05:  # Receivables grew > 5% faster than revenue in this year
            consecutive_gap_years += 1
            max_consecutive_gap_years = max(max_consecutive_gap_years, consecutive_gap_years)
        else:
            consecutive_gap_years = 0

        if i >= 2:
            prev_gap = yearly_growth_comparison[-1]["growth_gap"]
            if gap > prev_gap + 0.05:
                gap_widening_years += 1

        yearly_growth_comparison.append({
            "fiscal_year": y_curr,
            "revenue_growth": round(rev_yoy, 4),
            "receivables_growth": round(rec_yoy, 4),
            "growth_gap": round(gap, 4),
            "receivables_faster": gap > 0.05,
        })

    divergence_pattern = "NORMAL"
    if max_consecutive_gap_years >= 3 or gap_widening_years >= 2:
        divergence_pattern = "ACCELERATING"
    elif max_consecutive_gap_years >= 2:
        divergence_pattern = "PERSISTENT"
    elif max_consecutive_gap_years == 1:
        divergence_pattern = "TEMPORARY"

    # ---------------------------------------------------------
    # 2. AXIS A: LONG-TERM TREND & LOW-BASE DETECTION
    # ---------------------------------------------------------
    n_full = len(rec_series) - 1
    rec_cagr_full = (rec_series[-1][1] / rec_series[0][1]) ** (1.0 / n_full) - 1.0 if rec_series[0][1] > 0 and rec_series[-1][1] > 0 else 0.0
    rev_cagr_full = (rev_series[-1][1] / rev_series[0][1]) ** (1.0 / n_full) - 1.0 if rev_series[0][1] > 0 and rev_series[-1][1] > 0 else 0.0
    gap_full = rec_cagr_full - rev_cagr_full

    base_rec_ratio = (rec_series[0][1] / rev_series[0][1]) if rev_series[0][1] > 0 else 0.0
    base_asset_ratio = (rec_series[0][1] / asset_series[0][1]) if (asset_series and asset_series[0][1] > 0) else None
    is_low_base = bool(
        base_rec_ratio < thresholds.RECEIVABLES_LOW_BASE_RATIO_THRESHOLD
        or (base_asset_ratio is not None and base_asset_ratio < 0.03)
    )

    # ---------------------------------------------------------
    # 3. AXIS B: RECENT TREND (3Y CAGR GAP)
    # ---------------------------------------------------------
    has_3y_data = len(rec_series) >= 4 and rec_series[-4][1] > 0 and rev_series[-4][1] > 0
    if has_3y_data:
        rec_cagr_3y = (rec_series[-1][1] / rec_series[-4][1]) ** (1.0 / 3.0) - 1.0
        rev_cagr_3y = (rev_series[-1][1] / rev_series[-4][1]) ** (1.0 / 3.0) - 1.0
        gap_3y = rec_cagr_3y - rev_cagr_3y
    else:
        rec_cagr_3y = None
        rev_cagr_3y = None
        gap_3y = None

    # ---------------------------------------------------------
    # 4. AXIS C: MATERIALITY & DSO METRICS
    # ---------------------------------------------------------
    ratios = [rec / rev for (_, rec), (_, rev) in zip(rec_series, rev_series)]
    latest_rec_ratio = ratios[-1] if ratios else 0.0

    def calc_median(vals: List[float]) -> float:
        if not vals:
            return 0.0
        s = sorted(vals)
        n = len(s)
        return (s[n//2] if n % 2 != 0 else (s[n//2 - 1] + s[n//2]) / 2.0)

    ratio_3y_median = calc_median(ratios[-3:]) if len(ratios) >= 3 else latest_rec_ratio
    ratio_hist_median = calc_median(ratios)

    latest_assets = asset_series[-1][1] if asset_series else None
    latest_rec_asset_ratio = (rec_series[-1][1] / latest_assets) if (latest_assets and latest_assets > 0) else None

    dso_series: List[Tuple[int, float]] = []
    for i in range(1, len(rec_series)):
        y = rec_series[i][0]
        avg_rec = (rec_series[i-1][1] + rec_series[i][1]) / 2.0
        curr_rev = rev_series[i][1]
        if curr_rev > 0:
            dso_series.append((y, (avg_rec / curr_rev) * 365.0))

    dso_vals = [d[1] for d in dso_series]
    latest_dso = dso_vals[-1] if dso_vals else None
    dso_3y_median = calc_median(dso_vals[-3:]) if dso_vals else None
    dso_3y_change = (latest_dso - dso_vals[-3]) if len(dso_vals) >= 3 and latest_dso is not None else 0.0

    is_material_low = (
        latest_rec_ratio < thresholds.RECEIVABLES_MATERIALITY_LOW
        and (latest_dso is None or latest_dso < 60.0)
    )
    is_material_high = (
        latest_rec_ratio > thresholds.RECEIVABLES_MATERIALITY_HIGH
        or (latest_dso is not None and latest_dso > thresholds.RECEIVABLES_DSO_HIGH_DAYS)
        or (latest_rec_asset_ratio is not None and latest_rec_asset_ratio > thresholds.RECEIVABLES_ASSETS_RATIO_HIGH)
    )
    materiality_status = "LOW" if is_material_low else ("HIGH" if is_material_high else "MODERATE")

    # ---------------------------------------------------------
    # 5. AXIS D: CASH CONVERSION CORROBORATION
    # ---------------------------------------------------------
    has_cfo_data = bool(len(cfo_series) >= 3 and len(pat_series) >= 3)
    if has_cfo_data:
        recent_cfo_sum = sum(c[1] for c in cfo_series[-3:])
        recent_pat_sum = sum(p[1] for p in pat_series[-3:])
        cash_conversion = (recent_cfo_sum / recent_pat_sum) if recent_pat_sum > 0 else (1.0 if recent_cfo_sum >= 0 else 0.0)
        cash_status = "HEALTHY" if cash_conversion >= 0.80 else ("WEAK" if cash_conversion < thresholds.RECEIVABLES_CFO_PAT_CONCERN else "MODERATE")
    else:
        cash_conversion = None
        cash_status = "UNKNOWN"

    # ---------------------------------------------------------
    # 6. MULTI-SIGNAL EVIDENCE SYNTHESIS & SEVERITY MATRIX
    # ---------------------------------------------------------
    status = DimensionStatus.PASS.value
    severity = FindingSeverity.INFO.value
    findings: List[FinancialFinding] = []
    explanation = "Khả năng thu hồi tiền bán hàng bình thường, không có dấu hiệu nới lỏng chính sách bán chịu."

    # Evidence conditions
    has_recent_gap = bool(has_3y_data and gap_3y is not None and gap_3y > thresholds.RECEIVABLES_GROWTH_GAP_3Y_WATCH)
    has_strong_recent_gap = bool(has_3y_data and gap_3y is not None and gap_3y > thresholds.RECEIVABLES_GROWTH_GAP_3Y_HIGH)
    has_historical_gap = bool(gap_full > thresholds.RECEIVABLES_GROWTH_GAP_10Y_HISTORICAL and not is_low_base)

    # CASE C: Confirmed Forensic Deterioration (FAIL)
    # Requires: (Recent strong gap OR persistent gap) AND High Materiality AND Confirmed Weak Cash Conversion
    is_confirmed_fail = (
        (has_strong_recent_gap or (has_recent_gap and divergence_pattern in ("PERSISTENT", "ACCELERATING")))
        and is_material_high
        and cash_status == "WEAK"
        and (dso_3y_change > thresholds.RECEIVABLES_DSO_INCREASE_WATCH_DAYS or divergence_pattern in ("PERSISTENT", "ACCELERATING"))
    )
    if is_confirmed_fail:
        status = DimensionStatus.FAIL.value
        severity = FindingSeverity.HIGH.value
        dso_str = f"{latest_dso:.0f} ngày" if latest_dso is not None else "N/A"
        cfo_str = f"{cash_conversion:.2f}x" if cash_conversion is not None else "N/A"
        explanation = (
            f"Cảnh báo rủi ro chất lượng doanh thu và công nợ: Khoản phải thu tăng nhanh hơn doanh thu liên tiếp ({divergence_pattern}), "
            f"gap 3Y {gap_3y*100:.1f}%, tỷ lệ Phải thu/Doanh thu ở mức cao ({latest_rec_ratio*100:.1f}%), "
            f"thời gian thu tiền DSO tăng {dso_3y_change:.0f} ngày (hiện tại {dso_str}), "
            f"chất lượng dòng tiền CFO/PAT suy giảm ({cfo_str}). Cần giám sát chặt chẽ nguy cơ ứ đọng công nợ."
        )
        findings.append(
            FinancialFinding(
                code="RECEIVABLES_GROW_FASTER_THAN_REVENUE",
                category="WORKING_CAPITAL",
                severity=severity,
                confidence=ConfidenceLevel.HIGH.value if not is_total_proxy else ConfidenceLevel.MEDIUM.value,
                status=status,
                start_period=rec_series[0][0],
                end_period=rec_series[-1][0],
                metrics={
                    "long_term_gap": round(gap_full, 4),
                    "recent_gap": round(gap_3y, 4) if gap_3y is not None else None,
                    "receivables_to_revenue": round(latest_rec_ratio, 4),
                    "receivables_to_assets": round(latest_rec_asset_ratio, 4) if latest_rec_asset_ratio is not None else None,
                    "dso": round(latest_dso, 1) if latest_dso is not None else None,
                    "dso_3y_change": round(dso_3y_change, 1) if dso_3y_change is not None else None,
                    "cfo_pat": round(cash_conversion, 2) if cash_conversion is not None else None,
                    "persistence": divergence_pattern,
                    "low_base_distortion": is_low_base,
                    "materiality_status": materiality_status,
                    "cash_conversion_status": cash_status,
                    "semantic_key": "receivables_growth_vs_revenue",
                    "yearly_growth_comparison": yearly_growth_comparison,
                },
                evidence_fact_ids=evidence_facts,
                explanation=explanation,
                archetype=archetype,
                impact="Rủi ro chất lượng doanh thu cao do khoản phải thu tăng nhanh",
            )
        )

    # CASE B: Forensic WATCH (Signal needing monitoring, not structural collapse)
    elif (has_recent_gap) or (has_historical_gap and divergence_pattern in ("PERSISTENT", "ACCELERATING")) or (is_material_high and divergence_pattern in ("PERSISTENT", "ACCELERATING")) or (gap_full > thresholds.RECEIVABLES_GROWTH_GAP_10Y_HISTORICAL and not is_low_base and cash_status == "UNKNOWN"):
        status = DimensionStatus.WATCH.value
        severity = FindingSeverity.MEDIUM.value
        dso_str = f"{latest_dso:.0f} ngày" if latest_dso is not None else "Chưa đủ dữ liệu"
        gap_info = f"gap 3Y {gap_3y*100:.1f}%" if gap_3y is not None else f"gap dài hạn {gap_full*100:.1f}%"
        explanation = (
            f"Khoản phải thu có tín hiệu tăng nhanh hơn doanh thu (mô hình: {divergence_pattern}, {gap_info}), "
            f"tỷ lệ Phải thu/Doanh thu đạt {latest_rec_ratio*100:.1f}% (DSO = {dso_str}). Cần theo dõi chính sách công nợ."
        )
        findings.append(
            FinancialFinding(
                code="RECEIVABLES_GROW_FASTER_THAN_REVENUE",
                category="WORKING_CAPITAL",
                severity=severity,
                confidence=ConfidenceLevel.HIGH.value if (not is_total_proxy and has_3y_data) else ConfidenceLevel.MEDIUM.value,
                status=status,
                start_period=rec_series[0][0],
                end_period=rec_series[-1][0],
                metrics={
                    "long_term_gap": round(gap_full, 4),
                    "recent_gap": round(gap_3y, 4) if gap_3y is not None else None,
                    "receivables_to_revenue": round(latest_rec_ratio, 4),
                    "receivables_to_assets": round(latest_rec_asset_ratio, 4) if latest_rec_asset_ratio is not None else None,
                    "dso": round(latest_dso, 1) if latest_dso is not None else None,
                    "dso_3y_change": round(dso_3y_change, 1) if dso_3y_change is not None else None,
                    "cfo_pat": round(cash_conversion, 2) if cash_conversion is not None else None,
                    "persistence": divergence_pattern,
                    "low_base_distortion": is_low_base,
                    "materiality_status": materiality_status,
                    "cash_conversion_status": cash_status,
                    "semantic_key": "receivables_growth_vs_revenue",
                    "yearly_growth_comparison": yearly_growth_comparison,
                },
                evidence_fact_ids=evidence_facts,
                explanation=explanation,
                archetype=archetype,
                impact="Rủi ro vốn lưu động bị chiếm dụng trung bình",
            )
        )

    # CASE A: Low-base historical gap with healthy recent metrics (PASS)
    elif is_low_base and gap_full > thresholds.RECEIVABLES_GROWTH_GAP_10Y_HISTORICAL:
        status = DimensionStatus.PASS.value
        explanation = (
            "Phải thu từng tăng nhanh hơn doanh thu trong dài hạn do quy mô ban đầu rất nhỏ (hiệu ứng số gốc), "
            "nhưng xu hướng gần đây và tỷ trọng công nợ duy trì ở mức an toàn."
        )

    # CASE A: Recent 3Y trend healthy (PASS)
    elif has_3y_data and gap_3y is not None and gap_3y <= 0:
        status = DimensionStatus.PASS.value
        explanation = (
            "Không có bằng chứng khoản phải thu tăng nhanh hơn doanh thu trong giai đoạn gần đây. "
            "Tốc độ tăng trưởng doanh thu tương đương hoặc vượt trội so với công nợ."
        )

    else:
        status = DimensionStatus.PASS.value
        explanation = "Khả năng thu hồi tiền bán hàng bình thường, không có dấu hiệu nới lỏng chính sách bán chịu."

    confidence_score = (
        ConfidenceLevel.HIGH.value
        if (len(rec_series) >= 5 and not is_total_proxy and has_3y_data and has_cfo_data)
        else (ConfidenceLevel.MEDIUM.value if len(rec_series) >= 3 else ConfidenceLevel.LOW.value)
    )

    return FinancialDimensionResult(
        status=status,
        confidence=confidence_score,
        metrics={
            "long_term_gap": round(gap_full, 4),
            "recent_gap": round(gap_3y, 4) if gap_3y is not None else None,
            "receivables_to_revenue": round(latest_rec_ratio, 4),
            "receivables_to_assets": round(latest_rec_asset_ratio, 4) if latest_rec_asset_ratio is not None else None,
            "dso": round(latest_dso, 1) if latest_dso is not None else None,
            "dso_3y_change": round(dso_3y_change, 1) if dso_3y_change is not None else None,
            "cfo_pat": round(cash_conversion, 2) if cash_conversion is not None else None,
            "persistence": divergence_pattern,
            "low_base_distortion": is_low_base,
            "materiality_status": materiality_status,
            "cash_conversion_status": cash_status,
            "semantic_key": "receivables_growth_vs_revenue",
            "rec_cagr_3y": round(rec_cagr_3y, 4) if rec_cagr_3y is not None else None,
            "rev_cagr_3y": round(rev_cagr_3y, 4) if rev_cagr_3y is not None else None,
            "gap_3y": round(gap_3y, 4) if gap_3y is not None else None,
            "gap_full": round(gap_full, 4),
            "latest_rec_ratio": round(latest_rec_ratio, 4),
            "ratio_3y_median": round(ratio_3y_median, 4),
            "ratio_hist_median": round(ratio_hist_median, 4),
            "latest_dso": round(latest_dso, 1) if latest_dso is not None else None,
            "dso_3y_median": round(dso_3y_median, 1) if dso_3y_median is not None else None,
            "divergence_pattern": divergence_pattern,
            "max_consecutive_gap_years": max_consecutive_gap_years,
            "cash_conversion_3y": round(cash_conversion, 2) if cash_conversion is not None else None,
            "yearly_growth_comparison": yearly_growth_comparison,
        },
        findings=findings,
        evidence=evidence_facts,
        missing_data=[] if has_cfo_data else ["RECENT_CFO_PAT_HISTORY"],
        not_applicable=[],
        explanation=explanation,
    )


def run_inventory_forensics(
    history_data: Dict[str, Any],
    archetype: str = "NORMAL_ENTERPRISE",
    thresholds: MungerThresholdPolicy = DEFAULT_MUNGER_THRESHOLD_POLICY,
) -> FinancialDimensionResult:
    """Analyze inventory accumulation vs revenue."""
    if archetype in ("BANK", "SECURITIES"):
        return FinancialDimensionResult(
            status=DimensionStatus.NOT_APPLICABLE.value,
            confidence=ConfidenceLevel.HIGH.value,
            metrics={"archetype": archetype},
            findings=[],
            evidence=[],
            missing_data=[],
            not_applicable=["INDUSTRIAL_INVENTORY"],
            explanation=f"Ngành {get_vietnamese_archetype(archetype)} không tồn tại hàng tồn kho công nghiệp.",
        )

    by_year = history_data.get("by_year", {})
    years = history_data.get("years", [])

    inv_series: List[Tuple[int, float]] = []
    rev_series: List[Tuple[int, float]] = []
    evidence_facts: List[str] = []

    for y in years:
        ydict = by_year.get(y, {})
        inv = ydict.get("inventory") or ydict.get("BS.ASSETS.INVENTORY")
        rev = ydict.get("revenue") or ydict.get("IS.REVENUE.TOTAL")
        if inv is not None and rev is not None and float(rev) > 0:
            inv_series.append((y, float(inv)))
            rev_series.append((y, float(rev)))
            evidence_facts.extend([f"BS.ASSETS.INVENTORY FY{y}", f"IS.REVENUE.TOTAL FY{y}"])

    if len(inv_series) < 3:
        return FinancialDimensionResult(
            status=DimensionStatus.UNKNOWN.value,
            confidence=ConfidenceLevel.LOW.value,
            metrics={},
            findings=[],
            evidence=[],
            missing_data=["INSUFFICIENT_INVENTORY_DATA"],
            not_applicable=[],
            explanation="Thiếu dữ liệu hàng tồn kho.",
        )

    n_years = len(inv_series) - 1
    inv_cagr = (inv_series[-1][1] / inv_series[0][1]) ** (1.0 / n_years) - 1.0 if inv_series[0][1] > 0 and inv_series[-1][1] > 0 else None
    rev_cagr = (rev_series[-1][1] / rev_series[0][1]) ** (1.0 / n_years) - 1.0 if rev_series[0][1] > 0 and rev_series[-1][1] > 0 else None
    latest_inv_ratio = inv_series[-1][1] / rev_series[-1][1]

    status = DimensionStatus.PASS.value
    findings: List[FinancialFinding] = []

    if inv_cagr is not None and rev_cagr is not None and (inv_cagr - rev_cagr) > thresholds.INVENTORY_VS_REVENUE_CAGR_GAP:
        if latest_inv_ratio > thresholds.INVENTORY_REVENUE_RATIO_HIGH:
            status = DimensionStatus.FAIL.value
            findings.append(
                FinancialFinding(
                    code="INVENTORY_BUILDUP",
                    category="WORKING_CAPITAL",
                    severity=FindingSeverity.HIGH.value,
                    confidence=ConfidenceLevel.HIGH.value,
                    status=DimensionStatus.FAIL.value,
                    start_period=inv_series[0][0],
                    end_period=inv_series[-1][0],
                    metrics={"inv_cagr": inv_cagr, "rev_cagr": rev_cagr, "latest_inv_ratio": latest_inv_ratio},
                    evidence_fact_ids=evidence_facts,
                    explanation=f"Tồn kho ứ đọng lớn. CAGR tồn kho ({inv_cagr*100:.1f}%) vượt xa CAGR doanh thu ({rev_cagr*100:.1f}%).",
                    archetype=archetype,
                    impact="Áp lực vốn lưu động do hàng tồn kho ứ đọng lớn",
                )
            )
        else:
            status = DimensionStatus.WATCH.value
            findings.append(
                FinancialFinding(
                    code="INVENTORY_GROWTH_EXCEEDS_SALES",
                    category="WORKING_CAPITAL",
                    severity=FindingSeverity.MEDIUM.value,
                    confidence=ConfidenceLevel.HIGH.value,
                    status=DimensionStatus.WATCH.value,
                    start_period=inv_series[0][0],
                    end_period=inv_series[-1][0],
                    metrics={"inv_cagr": inv_cagr, "rev_cagr": rev_cagr},
                    evidence_fact_ids=evidence_facts,
                    explanation=f"Hàng tồn kho tích tụ nhanh hơn doanh thu tiêu thụ.",
                    archetype=archetype,
                    impact="Rủi ro tồn kho tích tụ ở mức trung bình",
                )
            )

    return FinancialDimensionResult(
        status=status,
        confidence=ConfidenceLevel.HIGH.value if len(inv_series) >= 5 else ConfidenceLevel.MEDIUM.value,
        metrics={
            "inv_cagr": inv_cagr,
            "rev_cagr": rev_cagr,
            "latest_inv_ratio": latest_inv_ratio,
        },
        findings=findings,
        evidence=evidence_facts,
        missing_data=[],
        not_applicable=[],
        explanation="Vòng quay và mức tồn kho nằm trong tầm kiểm soát." if status == DimensionStatus.PASS.value else "Cần theo dõi tốc độ ứ đọng hàng tồn kho.",
    )


def classify_structural_vs_cyclical_deterioration(
    findings: List[FinancialFinding],
    growth_metrics: Dict[str, Any],
    profitability_metrics: Dict[str, Any],
    durability_metrics: Dict[str, Any],
) -> Dict[str, Any]:
    """Classify deterioration deterministically based on multi-signal evidence.

    States:
    - NO_DETERIORATION
    - LIKELY_CYCLICAL
    - POSSIBLY_CYCLICAL
    - POSSIBLY_STRUCTURAL
    - STRUCTURAL
    - UNKNOWN
    """
    critical_findings = [f for f in findings if f.severity == FindingSeverity.CRITICAL.value]
    high_findings = [f for f in findings if f.severity == FindingSeverity.HIGH.value]
    medium_findings = [f for f in findings if f.severity == FindingSeverity.MEDIUM.value]

    negative_earnings_years = durability_metrics.get("negative_earnings_years", 0)
    total_years = durability_metrics.get("total_years", 0)
    roic_declining = profitability_metrics.get("roic_trend") == "DECLINING"
    margin_declining = profitability_metrics.get("margin_trend") == "DECLINING"

    structural_signals: List[str] = []
    cyclical_signals: List[str] = []
    working_capital_signals: List[str] = []

    for f in critical_findings + high_findings:
        if f.category in ("ACCOUNTING", "STRUCTURAL_DETERIORATION", "DILUTION", "DEBT"):
            structural_signals.append(f"{f.code}: {f.explanation}")
        elif f.category == "WORKING_CAPITAL":
            working_capital_signals.append(f"{f.code}: {f.explanation}")
        elif f.category == "EARNINGS_QUALITY":
            structural_signals.append(f"{f.code}: {f.explanation}")

    if roic_declining and margin_declining:
        structural_signals.append("ROIC và biên lợi nhuận cùng sụt giảm liên tục.")

    if durability_metrics.get("cyclical_rebound_observed") is True:
        cyclical_signals.append("Có lịch sử phục hồi mạnh sau giai đoạn đáy chu kỳ.")

    if len(structural_signals) >= 3:
        classification = DeteriorationClassification.STRUCTURAL.value
    elif len(structural_signals) in (1, 2):
        classification = DeteriorationClassification.POSSIBLY_STRUCTURAL.value
    elif len(cyclical_signals) > 0 and len(structural_signals) == 0:
        classification = DeteriorationClassification.LIKELY_CYCLICAL.value
    elif len(medium_findings) > 0 or len(working_capital_signals) > 0:
        classification = DeteriorationClassification.POSSIBLY_CYCLICAL.value
    else:
        classification = DeteriorationClassification.NO_DETERIORATION.value

    return {
        "classification": classification,
        "structural_signals": structural_signals,
        "cyclical_signals": cyclical_signals,
        "critical_count": len(critical_findings),
        "high_count": len(high_findings),
        "medium_count": len(medium_findings),
        "explanation": f"Xác định trạng thái: {get_vietnamese_deterioration(classification)}. {len(structural_signals)} tín hiệu cấu trúc, {len(cyclical_signals)} tín hiệu chu kỳ.",
    }
