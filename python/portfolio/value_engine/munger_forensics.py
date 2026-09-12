"""Financial Forensics, Accounting Consistency, and Structural Deterioration Engine (Task 136).

Provides deterministic evidence-first forensics across:
- Accounting consistency & balance sheet equation integrity
- Earnings quality & profit vs cash flow divergence
- Receivables & inventory forensic checks (archetype-aware)
- Debt-funded expansion & leverage stress
- Share dilution vs per-share compounding
- Structural vs cyclical deterioration classification
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
    1. Assets ≈ Liabilities + Equity (BS)
    2. BS Cash vs CF Ending Cash / Cash flow continuity
    3. PBT - Tax ≈ PAT (IS)
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

    explanation = "Báo cáo tài chính tuân thủ các hằng đẳng thức kế toán cơ bản." if status == DimensionStatus.PASS.value else "Phát hiện bộc lộ bất bếnh hằng đẳng thức kế toán trong BCTC."

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
    """Analyze earnings quality and profit vs cash flow divergence."""
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
            if fpat > 0:
                cfo_pat_ratios.append(fcfo / fpat)

    if not cfo_pat_ratios:
        return FinancialDimensionResult(
            status=DimensionStatus.UNKNOWN.value,
            confidence=ConfidenceLevel.LOW.value,
            metrics={},
            findings=[],
            evidence=[],
            missing_data=["CFO_PAT_DATA"],
            not_applicable=[],
            explanation="Thiếu dữ liệu dòng tiền kinh doanh hoặc lợi nhuận ròng âm liên tục.",
        )

    avg_cfo_pat = sum(cfo_pat_ratios) / len(cfo_pat_ratios)
    negative_cfo_years = sum(1 for c in cfo_series if c < 0)

    # Calculate 5Y CAGR gap if available
    cagr_pat = None
    cagr_cfo = None
    if len(pat_series) >= 4:
        cagr_pat = (pat_series[-1] / pat_series[0]) ** (1.0 / (len(pat_series) - 1)) - 1.0 if pat_series[0] > 0 and pat_series[-1] > 0 else None
        cagr_cfo = (cfo_series[-1] / cfo_series[0]) ** (1.0 / (len(cfo_series) - 1)) - 1.0 if cfo_series[0] > 0 and cfo_series[-1] > 0 else None

    findings: List[FinancialFinding] = []
    status = DimensionStatus.PASS.value

    # Check Profit vs Cash Divergence
    if avg_cfo_pat < thresholds.NORMAL_CFO_PAT_WATCH_RATIO or negative_cfo_years >= thresholds.PERSISTENT_NEGATIVE_CFO_YEARS:
        status = DimensionStatus.FAIL.value
        findings.append(
            FinancialFinding(
                code="PROFIT_CASH_DIVERGENCE",
                category="EARNINGS_QUALITY",
                severity=FindingSeverity.HIGH.value,
                confidence=ConfidenceLevel.HIGH.value,
                status=DimensionStatus.FAIL.value,
                start_period=years[0],
                end_period=years[-1],
                metrics={"avg_cfo_pat": round(avg_cfo_pat, 2), "negative_cfo_years": negative_cfo_years},
                evidence_fact_ids=evidence_facts,
                explanation=f"Lợi nhuận và dòng tiền phân kỳ mạnh. Tỷ lệ CFO/PAT trung bình {avg_cfo_pat:.2f}x (< {thresholds.NORMAL_CFO_PAT_WATCH_RATIO}x) và CFO âm {negative_cfo_years} năm.",
                archetype=archetype,
                impact="HIGH_EARNINGS_QUALITY_RISK",
            )
        )
    elif avg_cfo_pat < thresholds.NORMAL_CFO_PAT_PASS_RATIO or (cagr_pat is not None and cagr_cfo is not None and (cagr_pat - cagr_cfo) > thresholds.PROFIT_CASH_DIVERGENCE_CAGR_GAP):
        status = DimensionStatus.WATCH.value
        findings.append(
            FinancialFinding(
                code="WEAK_CASH_CONVERSION",
                category="EARNINGS_QUALITY",
                severity=FindingSeverity.MEDIUM.value,
                confidence=ConfidenceLevel.HIGH.value,
                status=DimensionStatus.WATCH.value,
                start_period=years[0],
                end_period=years[-1],
                metrics={"avg_cfo_pat": round(avg_cfo_pat, 2), "cagr_pat": cagr_pat, "cagr_cfo": cagr_cfo},
                evidence_fact_ids=evidence_facts,
                explanation=f"Tốc độ tăng trưởng lợi nhuận vượt xa tốc độ tăng trưởng dòng tiền kinh doanh.",
                archetype=archetype,
                impact="MODERATE_EARNINGS_QUALITY_RISK",
            )
        )

    explanation = "Chất lượng lợi nhuận tốt, dòng tiền kinh doanh bảo chứng lợi nhuận." if status == DimensionStatus.PASS.value else "Lợi nhuận chưa được hỗ trợ đầy đủ bởi dòng tiền kinh doanh thực thu."

    return FinancialDimensionResult(
        status=status,
        confidence=ConfidenceLevel.HIGH.value if len(years) >= 5 else ConfidenceLevel.MEDIUM.value,
        metrics={
            "avg_cfo_pat": round(avg_cfo_pat, 2),
            "negative_cfo_years": negative_cfo_years,
            "cagr_pat": cagr_pat,
            "cagr_cfo": cagr_cfo,
        },
        findings=findings,
        evidence=evidence_facts,
        missing_data=[],
        not_applicable=[],
        explanation=explanation,
    )


def run_receivables_forensics(
    history_data: Dict[str, Any],
    archetype: str = "NORMAL_ENTERPRISE",
    thresholds: MungerThresholdPolicy = DEFAULT_MUNGER_THRESHOLD_POLICY,
) -> FinancialDimensionResult:
    """Analyze receivables growth vs revenue growth with 2-stage semantic validation."""
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

    # STAGE A — Canonical Semantic Validation
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
    evidence_facts: List[str] = []

    for y in years:
        ydict = by_year.get(y, {})
        rec = ydict.get("receivables")
        rev = ydict.get("revenue") or ydict.get("IS.REVENUE.TOTAL")
        cfo = ydict.get("cfo") or ydict.get("operating_cash_flow")
        pat = ydict.get("net_profit") or ydict.get("net_income")

        if rec is not None and rev is not None and float(rev) > 0:
            rec_series.append((y, float(rec)))
            rev_series.append((y, float(rev)))
            if cfo is not None:
                cfo_series.append((y, float(cfo)))
            if pat is not None:
                pat_series.append((y, float(pat)))
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

    # Calculate Receivable Intensity (receivables / revenue)
    ratios: List[Tuple[int, float]] = [(y, rec / rev) for y, rec in rec_series for y_rev, rev in rev_series if y == y_rev]
    ratio_vals = [r[1] for r in ratios]
    latest_rec_ratio = ratio_vals[-1] if ratio_vals else 0.0

    def calc_median(vals: List[float]) -> float:
        if not vals:
            return 0.0
        s = sorted(vals)
        n = len(s)
        return (s[n//2] if n % 2 != 0 else (s[n//2 - 1] + s[n//2]) / 2.0)

    ratio_3y_median = calc_median(ratio_vals[-3:])
    ratio_5y_median = calc_median(ratio_vals[-5:])
    ratio_hist_median = calc_median(ratio_vals)

    # Calculate DSO = (Avg Receivables / Annual Revenue) * 365
    dso_series: List[Tuple[int, float]] = []
    for i in range(1, len(rec_series)):
        y = rec_series[i][0]
        prev_rec = rec_series[i-1][1]
        curr_rec = rec_series[i][1]
        curr_rev = rev_series[i][1]
        avg_rec = (prev_rec + curr_rec) / 2.0
        if curr_rev > 0:
            dso = (avg_rec / curr_rev) * 365.0
            dso_series.append((y, dso))

    dso_vals = [d[1] for d in dso_series]
    latest_dso = dso_vals[-1] if dso_vals else None
    dso_3y_median = calc_median(dso_vals[-3:]) if dso_vals else None
    dso_5y_median = calc_median(dso_vals[-5:]) if dso_vals else None
    dso_hist_median = calc_median(dso_vals) if dso_vals else None
    dso_3y_change = (latest_dso - dso_vals[-3]) if len(dso_vals) >= 3 and latest_dso is not None else 0.0
    dso_5y_change = (latest_dso - dso_vals[-5]) if len(dso_vals) >= 5 and latest_dso is not None else 0.0

    # Consecutive worsening DSO years
    consecutive_worsening_dso_years = 0
    for i in range(len(dso_vals) - 1, 0, -1):
        if dso_vals[i] > dso_vals[i-1]:
            consecutive_worsening_dso_years += 1
        else:
            break

    # Multi-period CAGRs
    n_full = len(rec_series) - 1
    rec_cagr_full = (rec_series[-1][1] / rec_series[0][1]) ** (1.0 / n_full) - 1.0 if rec_series[0][1] > 0 and rec_series[-1][1] > 0 else 0.0
    rev_cagr_full = (rev_series[-1][1] / rev_series[0][1]) ** (1.0 / n_full) - 1.0 if rev_series[0][1] > 0 and rev_series[-1][1] > 0 else 0.0

    rec_cagr_3y = ((rec_series[-1][1] / rec_series[-4][1]) ** (1.0 / 3.0) - 1.0) if len(rec_series) >= 4 and rec_series[-4][1] > 0 and rec_series[-1][1] > 0 else rec_cagr_full
    rev_cagr_3y = ((rev_series[-1][1] / rev_series[-4][1]) ** (1.0 / 3.0) - 1.0) if len(rev_series) >= 4 and rev_series[-4][1] > 0 and rev_series[-1][1] > 0 else rev_cagr_full

    gap_3y = rec_cagr_3y - rev_cagr_3y
    gap_full = rec_cagr_full - rev_cagr_full

    # Corroborating Evidence: CFO / PAT
    recent_cfo_sum = sum(c[1] for c in cfo_series[-3:]) if len(cfo_series) >= 3 else (sum(c[1] for c in cfo_series) if cfo_series else 0)
    recent_pat_sum = sum(p[1] for p in pat_series[-3:]) if len(pat_series) >= 3 else (sum(p[1] for p in pat_series) if pat_series else 0)
    cash_conversion = (recent_cfo_sum / recent_pat_sum) if recent_pat_sum > 0 else 1.0

    # STAGE B — Economic Forensic Assessment & Persistence Check
    has_growth_gap = (gap_3y > thresholds.RECEIVABLES_VS_REVENUE_CAGR_GAP or gap_full > thresholds.RECEIVABLES_VS_REVENUE_CAGR_GAP)
    has_high_intensity = latest_rec_ratio > thresholds.RECEIVABLES_REVENUE_RATIO_HIGH
    is_persistent = (consecutive_worsening_dso_years >= 2 or dso_3y_change > 15.0 or (latest_rec_ratio > ratio_hist_median + 0.05))
    has_weak_cash_conversion = cash_conversion < 0.6 or recent_cfo_sum < 0

    status = DimensionStatus.PASS.value
    findings: List[FinancialFinding] = []
    explanation = "Khả năng thu hồi tiền bán hàng bình thường."

    if has_growth_gap or (has_high_intensity and is_persistent):
        # Default severity for persistent material divergence + worsening DSO + weak CFO
        if not is_total_proxy and is_persistent and has_weak_cash_conversion and latest_rec_ratio > 0.40:
            status = DimensionStatus.FAIL.value
            severity = FindingSeverity.HIGH.value
            explanation = (
                f"Khoản phải thu từ khách hàng tăng vượt doanh thu (gap 3Y {gap_3y*100:.1f}%), "
                f"thời gian thu tiền DSO tăng {dso_3y_change:.0f} ngày (hiện tại {latest_dso:.0f} ngày), "
                f"đồng thời dòng tiền kinh doanh yếu (CFO/PAT 3Y = {cash_conversion:.2f})."
            )
        else:
            status = DimensionStatus.WATCH.value
            severity = FindingSeverity.MEDIUM.value
            if is_total_proxy:
                explanation = (
                    f"Tổng các khoản phải thu (gồm cả chi phí trả trước/khác) tăng nhanh hơn doanh thu. "
                    f"Dữ liệu ở dạng tổng hợp (TOTAL_PROXY), cần theo dõi thêm."
                )
            else:
                dso_str = f"{latest_dso:.0f} ngày" if latest_dso is not None else "N/A"
                explanation = (
                    f"Khoản phải thu từ khách hàng tăng nhanh hơn doanh thu (gap 3Y {gap_3y*100:.1f}%), "
                    f"tỷ lệ Phải thu/Doanh thu ở mức {latest_rec_ratio*100:.1f}% (DSO = {dso_str})."
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
                    "rec_cagr_3y": rec_cagr_3y,
                    "rev_cagr_3y": rev_cagr_3y,
                    "gap_3y": gap_3y,
                    "latest_rec_ratio": latest_rec_ratio,
                    "latest_dso": latest_dso,
                    "dso_3y_change": dso_3y_change,
                    "cash_conversion_3y": cash_conversion,
                    "source_type": source_types[-1] if source_types else "UNKNOWN",
                },
                evidence_fact_ids=evidence_facts,
                explanation=explanation,
                archetype=archetype,
                impact="REVENUE_QUALITY_RISK" if severity == FindingSeverity.HIGH.value else "MODERATE_WORKING_CAPITAL_RISK",
            )
        )

    return FinancialDimensionResult(
        status=status,
        confidence=ConfidenceLevel.HIGH.value if (len(rec_series) >= 5 and not is_total_proxy) else ConfidenceLevel.MEDIUM.value,
        metrics={
            "rec_cagr_3y": rec_cagr_3y,
            "rev_cagr_3y": rev_cagr_3y,
            "gap_3y": gap_3y,
            "latest_rec_ratio": latest_rec_ratio,
            "ratio_3y_median": ratio_3y_median,
            "ratio_hist_median": ratio_hist_median,
            "latest_dso": latest_dso,
            "dso_3y_median": dso_3y_median,
            "dso_3y_change": dso_3y_change,
            "consecutive_worsening_dso_years": consecutive_worsening_dso_years,
            "cash_conversion_3y": cash_conversion,
            "receivables_source_type": source_types[-1] if source_types else "UNKNOWN",
        },
        findings=findings,
        evidence=evidence_facts,
        missing_data=[],
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
                    impact="WORKING_CAPITAL_STRESS",
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
                    impact="MODERATE_INVENTORY_RISK",
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

    # Invariant: A single working capital finding alone MUST NOT trigger POSSIBLY_STRUCTURAL or STRUCTURAL
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
