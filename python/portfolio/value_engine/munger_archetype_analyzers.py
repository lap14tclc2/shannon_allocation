"""Archetype-Specific Financial Statement Analyzers (Task 136, Task 144).

Provides tailored financial statement analysis for:
- NORMAL_ENTERPRISE (AAA, DGC, FPT, etc.)
- BANK (ACB, VCB, MBB, etc.)
- SECURITIES (VIX, SSI, VND, etc.)
"""

from __future__ import annotations

import math
from typing import Any, Dict, List, Optional
from .munger_models import (
    ConfidenceLevel,
    DimensionStatus,
    FindingSeverity,
    FinancialDimensionResult,
    FinancialFinding,
)
from .munger_thresholds import DEFAULT_MUNGER_THRESHOLD_POLICY, MungerThresholdPolicy
from .vietnamese_presenter import MARGIN_TREND_VIETNAMESE


def analyze_normal_enterprise(
    history_data: Dict[str, Any],
    thresholds: MungerThresholdPolicy = DEFAULT_MUNGER_THRESHOLD_POLICY,
) -> Dict[str, FinancialDimensionResult]:
    """Run full financial statement analysis for a NORMAL_ENTERPRISE."""
    by_year = history_data.get("by_year", {})
    years = history_data.get("years", [])

    if not years:
        empty_res = FinancialDimensionResult(
            status=DimensionStatus.UNKNOWN.value,
            confidence=ConfidenceLevel.LOW.value,
            metrics={},
            findings=[],
            evidence=[],
            missing_data=["FINANCIAL_HISTORY"],
            not_applicable=[],
            explanation="Không có dữ liệu lịch sử tài chính.",
        )
        return {
            "growth": empty_res,
            "profitability": empty_res,
            "durability": empty_res,
            "balance_sheet": empty_res,
            "debt_liquidity": empty_res,
            "capital_efficiency": empty_res,
            "capital_allocation": empty_res,
            "dilution": empty_res,
        }

    # 1. Growth Analysis
    rev_list = [by_year[y].get("revenue") for y in years if by_year[y].get("revenue") is not None]
    pat_list = [by_year[y].get("net_profit") for y in years if by_year[y].get("net_profit") is not None]
    eq_list = [(by_year[y].get("equity") or by_year[y].get("total_equity")) for y in years if (by_year[y].get("equity") or by_year[y].get("total_equity")) is not None]
    sh_list = [(by_year[y].get("outstanding_shares") or by_year[y].get("shares_outstanding")) for y in years if (by_year[y].get("outstanding_shares") or by_year[y].get("shares_outstanding")) is not None]

    rev_cagr = (rev_list[-1] / rev_list[0]) ** (1.0 / (len(rev_list) - 1)) - 1.0 if len(rev_list) >= 2 and rev_list[0] > 0 and rev_list[-1] > 0 else None
    pat_cagr = (pat_list[-1] / pat_list[0]) ** (1.0 / (len(pat_list) - 1)) - 1.0 if len(pat_list) >= 2 and pat_list[0] > 0 and pat_list[-1] > 0 else None
    eq_cagr = (eq_list[-1] / eq_list[0]) ** (1.0 / (len(eq_list) - 1)) - 1.0 if len(eq_list) >= 2 and eq_list[0] > 0 and eq_list[-1] > 0 else None
    share_cagr = (sh_list[-1] / sh_list[0]) ** (1.0 / (len(sh_list) - 1)) - 1.0 if len(sh_list) >= 2 and sh_list[0] > 0 and sh_list[-1] > 0 else None

    latest_shares = float(sh_list[-1]) if (sh_list and float(sh_list[-1]) > 0) else None
    eps_list = []
    for y in years:
        p = by_year[y].get("net_profit")
        if p is not None:
            if latest_shares:
                eps_list.append(float(p) / latest_shares)
            else:
                s = by_year[y].get("outstanding_shares")
                if s is not None and float(s) > 0:
                    eps_list.append(float(p) / float(s))
    eps_cagr = (eps_list[-1] / eps_list[0]) ** (1.0 / (len(eps_list) - 1)) - 1.0 if len(eps_list) >= 2 and eps_list[0] > 0 and eps_list[-1] > 0 else None

    growth_findings: List[FinancialFinding] = []
    growth_status = DimensionStatus.PASS.value
    if pat_cagr is not None and eps_cagr is not None and (pat_cagr - eps_cagr) > thresholds.PER_SHARE_DILUTION_PAT_GAP:
        growth_status = DimensionStatus.WATCH.value
        growth_findings.append(
            FinancialFinding(
                code="PER_SHARE_VALUE_DILUTION",
                category="DILUTION",
                severity=FindingSeverity.MEDIUM.value,
                confidence=ConfidenceLevel.HIGH.value,
                status=DimensionStatus.WATCH.value,
                start_period=years[0],
                end_period=years[-1],
                metrics={"pat_cagr": pat_cagr, "eps_cagr": eps_cagr, "share_cagr": share_cagr},
                evidence_fact_ids=[f"IS.PROFIT.NET FY{years[-1]}", f"IS.SHARES.OUTSTANDING FY{years[-1]}"],
                explanation=f"Tăng trưởng LNST tổng ({pat_cagr*100:.1f}%) nhanh hơn tăng trưởng EPS trên mỗi cổ phần ({eps_cagr*100:.1f}%) do pha loãng cổ phiếu ({share_cagr*100:.1f}%/năm).",
                archetype="NORMAL_ENTERPRISE",
            )
        )

    growth_res = FinancialDimensionResult(
        status=growth_status,
        confidence=ConfidenceLevel.HIGH.value if len(years) >= 5 else ConfidenceLevel.MEDIUM.value,
        metrics={
            "revenue_cagr": rev_cagr,
            "net_profit_cagr": pat_cagr,
            "equity_cagr": eq_cagr,
            "eps_cagr": eps_cagr,
            "annual_share_growth": share_cagr,
            "share_cagr": share_cagr,
        },
        findings=growth_findings,
        evidence=[f"IS.REVENUE.TOTAL FY{years[-1]}", f"IS.PROFIT.NET FY{years[-1]}"],
        missing_data=[],
        not_applicable=[],
        explanation=f"Doanh thu CAGR {(rev_cagr*100):.1f}%" if rev_cagr is not None else "Tăng trưởng doanh thu duy trì ổn định." + (f", LNST CAGR {(pat_cagr*100):.1f}%" if pat_cagr is not None else ""),
    )

    # 2. Profitability Analysis
    roe_series = []
    roic_series = []
    margin_series = []

    for y in years:
        ydict = by_year[y]
        p = ydict.get("net_profit")
        e = ydict.get("equity") or ydict.get("total_equity")
        r = ydict.get("revenue")
        d = ydict.get("total_debt") or 0.0
        op = ydict.get("operating_profit") or p or 0.0

        if p is not None and e is not None and float(e) > 0:
            roe_series.append(float(p) / float(e))
        if op is not None and e is not None and (float(e) + float(d)) > 0:
            roic_series.append(float(op) / (float(e) + float(d)))
        if p is not None and r is not None and float(r) > 0:
            margin_series.append(float(p) / float(r))

    med_roe = sorted(roe_series)[len(roe_series)//2] if roe_series else None
    med_roic = sorted(roic_series)[len(roic_series)//2] if roic_series else None
    med_margin = sorted(margin_series)[len(margin_series)//2] if margin_series else None

    margin_trend = "STABLE"
    if len(margin_series) >= 2:
        rec_3y_m = sum(margin_series[-3:]) / len(margin_series[-3:])
        hist_m = sum(margin_series) / len(margin_series)
        if rec_3y_m > hist_m + 0.005:
            margin_trend = "EXPANDING"
        elif rec_3y_m < hist_m - 0.005:
            margin_trend = "DECLINING"

    prof_status = DimensionStatus.PASS.value
    prof_findings: List[FinancialFinding] = []
    if med_roe is not None and med_roe < thresholds.ROE_WATCH:
        prof_status = DimensionStatus.FAIL.value
        prof_findings.append(
            FinancialFinding(
                code="WEAK_PROFITABILITY_ROE",
                category="PROFITABILITY",
                severity=FindingSeverity.HIGH.value,
                confidence=ConfidenceLevel.HIGH.value,
                status=DimensionStatus.FAIL.value,
                start_period=years[0],
                end_period=years[-1],
                metrics={"median_roe": med_roe, "margin_trend": margin_trend},
                evidence_fact_ids=[f"IS.PROFIT.NET FY{years[-1]}", f"BS.EQUITY.TOTAL FY{years[-1]}"],
                explanation=f"Tỷ suất sinh lời trên vốn chủ sở hữu (ROE) trung vị {med_roe*100:.1f}% thấp hơn ngưỡng yêu cầu ({thresholds.ROE_WATCH*100:.1f}%).",
                archetype="NORMAL_ENTERPRISE",
            )
        )
    elif med_roe is not None and med_roe < thresholds.ROE_PASS:
        prof_status = DimensionStatus.WATCH.value

    prof_res = FinancialDimensionResult(
        status=prof_status,
        confidence=ConfidenceLevel.HIGH.value if len(years) >= 5 else ConfidenceLevel.MEDIUM.value,
        metrics={
            "median_roe": med_roe,
            "median_roic": med_roic,
            "median_net_margin": med_margin,
            "margin_trend": margin_trend,
        },
        findings=prof_findings,
        evidence=[f"IS.PROFIT.NET FY{years[-1]}"],
        missing_data=[],
        not_applicable=[],
        explanation=f"ROE trung vị: {med_roe*100:.1f}% nếu có, ROIC trung vị: {med_roic*100:.1f}% nếu có, Xu hướng biên LN: {MARGIN_TREND_VIETNAMESE.get(margin_trend, margin_trend)}." if med_roe is not None else "Thiếu dữ liệu tỷ suất lợi nhuận.",
    )

    # 3. Durability & Stability
    profitable_years = sum(1 for p in pat_list if p is not None and p > 0)
    negative_years = sum(1 for p in pat_list if p is not None and p <= 0)
    total_y = len(pat_list)

    pat_vol = None
    if len(pat_list) >= 3:
        mean_p = sum(pat_list) / len(pat_list)
        if mean_p != 0:
            var_p = sum((p - mean_p) ** 2 for p in pat_list) / len(pat_list)
            std_p = math.sqrt(var_p)
            pat_vol = std_p / abs(mean_p)

    durability_status = DimensionStatus.PASS.value
    durability_findings: List[FinancialFinding] = []
    if negative_years > 0:
        if negative_years >= 2 or (total_y > 0 and negative_years / total_y >= 0.3):
            durability_status = DimensionStatus.FAIL.value
            durability_findings.append(
                FinancialFinding(
                    code="UNSTABLE_EARNINGS_HISTORY",
                    category="DURABILITY",
                    severity=FindingSeverity.HIGH.value,
                    confidence=ConfidenceLevel.HIGH.value,
                    status=DimensionStatus.FAIL.value,
                    start_period=years[0],
                    end_period=years[-1],
                    metrics={"negative_years": negative_years, "total_years": total_y, "pat_volatility": pat_vol},
                    evidence_fact_ids=[f"IS.PROFIT.NET FY{y}" for y in years],
                    explanation=f"Lịch sử lợi nhuận không ổn định với {negative_years}/{total_y} năm bị thua lỗ.",
                    archetype="NORMAL_ENTERPRISE",
                )
            )
        else:
            durability_status = DimensionStatus.WATCH.value

    durability_res = FinancialDimensionResult(
        status=durability_status,
        confidence=ConfidenceLevel.HIGH.value if total_y >= 5 else ConfidenceLevel.MEDIUM.value,
        metrics={
            "profitable_years": profitable_years,
            "negative_earnings_years": negative_years,
            "total_years": total_y,
            "earnings_persistence_rate": (profitable_years / total_y) if total_y > 0 else None,
            "pat_volatility": pat_vol,
            "profit_volatility": pat_vol,
            "volatility_interpretation": "HIGH" if (pat_vol and pat_vol >= 0.40) else ("MODERATE" if (pat_vol and pat_vol >= 0.25) else "LOW"),
        },
        findings=durability_findings,
        evidence=[f"IS.PROFIT.NET FY{y}" for y in years],
        missing_data=[],
        not_applicable=[],
        explanation=f"Lợi nhuận dương {profitable_years}/{total_y} năm quan sát (tính bền bỉ đạt chuẩn); Hệ số biến động LNST: {pat_vol*100:.1f}%." if pat_vol is not None else f"Lợi nhuận dương {profitable_years}/{total_y} năm quan sát.",
    )

    # 4. Balance Sheet & Debt
    last_ydict = by_year[years[-1]]
    raw_debt = last_ydict.get("total_debt")
    raw_eq = last_ydict.get("equity")
    interest_exp = last_ydict.get("interest_expense") or 0.0
    op_prof = last_ydict.get("operating_profit") or last_ydict.get("net_profit") or 0.0
    cash_val = last_ydict.get("cash") or 0.0

    tot_debt = float(raw_debt) if raw_debt is not None else None
    tot_eq = float(raw_eq) if raw_eq is not None else None
    de_ratio = (tot_debt / tot_eq) if (tot_debt is not None and tot_eq is not None and tot_eq > 0) else None
    interest_coverage = float(op_prof) / float(interest_exp) if (interest_exp > 0 and op_prof is not None) else None
    cash_debt = (float(cash_val) / tot_debt) if (tot_debt is not None and tot_debt > 0) else None

    bs_status = DimensionStatus.PASS.value
    bs_findings: List[FinancialFinding] = []
    if de_ratio is not None and de_ratio > thresholds.DEBT_EQUITY_WATCH:
        bs_status = DimensionStatus.FAIL.value
        bs_findings.append(
            FinancialFinding(
                code="EXCESSIVE_DEBT_LEVERAGE",
                category="DEBT",
                severity=FindingSeverity.HIGH.value,
                confidence=ConfidenceLevel.HIGH.value,
                status=DimensionStatus.FAIL.value,
                start_period=years[-1],
                end_period=years[-1],
                metrics={"debt_equity_ratio": de_ratio, "latest_debt_equity": de_ratio},
                evidence_fact_ids=[f"BS.DEBT.TOTAL FY{years[-1]}", f"BS.EQUITY.TOTAL FY{years[-1]}"],
                explanation=f"Nợ vay trên vốn chủ sở hữu {de_ratio:.2f}x vượt ngưỡng cảnh báo ({thresholds.DEBT_EQUITY_WATCH:.2f}x).",
                archetype="NORMAL_ENTERPRISE",
            )
        )
    elif de_ratio is not None and de_ratio > thresholds.DEBT_EQUITY_PASS:
        bs_status = DimensionStatus.WATCH.value

    if de_ratio is not None:
        if de_ratio > thresholds.DEBT_EQUITY_WATCH:
            bs_exp = f"Nợ vay trên vốn chủ sở hữu ({de_ratio:.2f}x) vượt ngưỡng cảnh báo ({thresholds.DEBT_EQUITY_WATCH:.2f}x)."
        elif de_ratio > thresholds.DEBT_EQUITY_PASS:
            bs_exp = f"Nợ/VCSH hiện ở mức {de_ratio:.2f}x (ngưỡng an toàn khuyến nghị: <= {thresholds.DEBT_EQUITY_PASS:.2f}x, ngưỡng cảnh báo: > {thresholds.DEBT_EQUITY_WATCH:.2f}x); chỉ tiêu này được xếp diện theo dõi theo quy tắc quản trị vốn."
        else:
            bs_exp = f"Tỷ lệ Nợ/VCSH ở mức an toàn ({de_ratio:.2f}x <= {thresholds.DEBT_EQUITY_PASS:.2f}x); chưa phát hiện rủi ro đòn bẩy nghiêm trọng."
    else:
        bs_exp = "Không phát hiện rủi ro nợ vay đe dọa khả năng hoạt động."

    bs_res = FinancialDimensionResult(
        status=bs_status,
        confidence=ConfidenceLevel.HIGH.value,
        metrics={
            "latest_debt_equity": de_ratio,
            "debt_equity_ratio": de_ratio,
            "interest_coverage": interest_coverage,
            "cash_debt_ratio": cash_debt,
            "total_debt": tot_debt,
            "equity": tot_eq,
            "threshold_pass": thresholds.DEBT_EQUITY_PASS,
            "threshold_watch": thresholds.DEBT_EQUITY_WATCH,
        },
        findings=bs_findings,
        evidence=[f"BS.DEBT.TOTAL FY{years[-1]}", f"BS.EQUITY.TOTAL FY{years[-1]}"],
        missing_data=[],
        not_applicable=[],
        explanation=bs_exp,
    )

    # 5. Capital Efficiency
    roic_trend = "EXPANDING" if (roic_series and len(roic_series) >= 3 and roic_series[-1] > roic_series[0]) else "STABLE"
    cap_eff_res = FinancialDimensionResult(
        status=prof_status,
        confidence=ConfidenceLevel.HIGH.value if len(years) >= 5 else ConfidenceLevel.MEDIUM.value,
        metrics={
            "median_roic": med_roic,
            "median_roe": med_roe,
            "roic_trend": roic_trend,
        },
        findings=[],
        evidence=[f"IS.PROFIT.NET FY{years[-1]}"],
        missing_data=[],
        not_applicable=[],
        explanation=f"Hiệu quả sử dụng vốn ROIC trung vị {med_roic*100:.1f}% nếu có." if med_roic is not None else "Thiếu dữ liệu ROIC bóc tách.",
    )

    # 6. Capital Allocation
    retained_eff = "HIGH" if (pat_cagr and pat_cagr >= 0.15) else ("POSITIVE" if (pat_cagr and pat_cagr > 0) else "WATCH")
    cap_alloc_res = FinancialDimensionResult(
        status=DimensionStatus.PASS.value if pat_cagr is not None and pat_cagr > 0.05 else DimensionStatus.WATCH.value,
        confidence=ConfidenceLevel.MEDIUM.value,
        metrics={
            "retained_earnings_effectiveness": retained_eff,
            "retained_earnings_cagr": eq_cagr,
        },
        findings=[],
        evidence=[],
        missing_data=[],
        not_applicable=[],
        explanation="Phân bổ vốn duy trì tăng trưởng kinh doanh hợp lý.",
    )

    # 7. Dilution
    dilution_res = FinancialDimensionResult(
        status=growth_status,
        confidence=ConfidenceLevel.HIGH.value,
        metrics={
            "annual_share_growth": share_cagr,
            "share_cagr": share_cagr,
            "dilution_cagr": share_cagr,
            "pat_cagr": pat_cagr,
            "eps_cagr": eps_cagr,
        },
        findings=growth_findings,
        evidence=[],
        missing_data=[],
        not_applicable=[],
        explanation="Không bị pha loãng cổ phần nghiêm trọng." if growth_status == DimensionStatus.PASS.value else "Phát hiện hiện tượng pha loãng làm giảm hiệu quả tăng trưởng mỗi cổ phần.",
    )

    return {
        "growth": growth_res,
        "profitability": prof_res,
        "durability": durability_res,
        "balance_sheet": bs_res,
        "debt_liquidity": bs_res,
        "capital_efficiency": cap_eff_res,
        "capital_allocation": cap_alloc_res,
        "dilution": dilution_res,
    }


def analyze_bank(
    history_data: Dict[str, Any],
    thresholds: MungerThresholdPolicy = DEFAULT_MUNGER_THRESHOLD_POLICY,
) -> Dict[str, FinancialDimensionResult]:
    """Run specialized financial statement analysis for BANK (e.g. ACB)."""
    by_year = history_data.get("by_year", {})
    years = history_data.get("years", [])

    if not years:
        empty_res = FinancialDimensionResult(
            status=DimensionStatus.UNKNOWN.value,
            confidence=ConfidenceLevel.LOW.value,
            metrics={},
            findings=[],
            evidence=[],
            missing_data=["FINANCIAL_HISTORY"],
            not_applicable=[],
            explanation="Không có dữ liệu lịch sử ngân hàng.",
        )
        return {
            "growth": empty_res,
            "profitability": empty_res,
            "durability": empty_res,
            "balance_sheet": empty_res,
            "debt_liquidity": empty_res,
            "capital_efficiency": empty_res,
            "capital_allocation": empty_res,
            "dilution": empty_res,
        }

    pat_list = [by_year[y].get("net_profit") for y in years if by_year[y].get("net_profit") is not None]
    eq_list = [by_year[y].get("equity") for y in years if by_year[y].get("equity") is not None]
    sh_list = [by_year[y].get("outstanding_shares") for y in years if by_year[y].get("outstanding_shares") is not None]
    tot_assets_list = [by_year[y].get("total_assets") for y in years if by_year[y].get("total_assets") is not None]

    pat_cagr = (pat_list[-1] / pat_list[0]) ** (1.0 / (len(pat_list) - 1)) - 1.0 if len(pat_list) >= 2 and pat_list[0] > 0 and pat_list[-1] > 0 else None
    eq_cagr = (eq_list[-1] / eq_list[0]) ** (1.0 / (len(eq_list) - 1)) - 1.0 if len(eq_list) >= 2 and eq_list[0] > 0 and eq_list[-1] > 0 else None
    share_cagr = (sh_list[-1] / sh_list[0]) ** (1.0 / (len(sh_list) - 1)) - 1.0 if len(sh_list) >= 2 and sh_list[0] > 0 and sh_list[-1] > 0 else 0.0

    latest_shares = float(sh_list[-1]) if (sh_list and float(sh_list[-1]) > 0) else None
    eps_list = []
    for y in years:
        p = by_year[y].get("net_profit")
        if p is not None:
            if latest_shares:
                eps_list.append(float(p) / latest_shares)
            else:
                s = by_year[y].get("outstanding_shares")
                if s is not None and float(s) > 0:
                    eps_list.append(float(p) / float(s))
    eps_cagr = (eps_list[-1] / eps_list[0]) ** (1.0 / (len(eps_list) - 1)) - 1.0 if len(eps_list) >= 2 and eps_list[0] > 0 and eps_list[-1] > 0 else None

    roe_series = []
    roa_series = []
    for y in years:
        p = by_year[y].get("net_profit")
        e = by_year[y].get("equity")
        a = by_year[y].get("total_assets")
        if p is not None and e is not None and float(e) > 0:
            roe_series.append(float(p) / float(e))
        if p is not None and a is not None and float(a) > 0:
            roa_series.append(float(p) / float(a))

    med_roe = sorted(roe_series)[len(roe_series)//2] if roe_series else None
    med_roa = sorted(roa_series)[len(roa_series)//2] if roa_series else None

    # Bank Capital Strength: Equity / Assets
    last_ydict = by_year[years[-1]]
    last_eq = last_ydict.get("equity")
    last_assets = last_ydict.get("total_assets")
    equity_assets_ratio = float(last_eq) / float(last_assets) if last_eq and last_assets and float(last_assets) > 0 else None
    bank_leverage = float(last_assets) / float(last_eq) if last_eq and last_assets and float(last_eq) > 0 else None

    profitable_years = sum(1 for p in pat_list if p is not None and p > 0)
    negative_years = sum(1 for p in pat_list if p is not None and p <= 0)
    total_y = len(pat_list)

    pat_vol = None
    if len(pat_list) >= 3:
        mean_p = sum(pat_list) / len(pat_list)
        if mean_p != 0:
            var_p = sum((p - mean_p) ** 2 for p in pat_list) / len(pat_list)
            std_p = math.sqrt(var_p)
            pat_vol = std_p / abs(mean_p)

    prof_status = DimensionStatus.PASS.value
    prof_findings: List[FinancialFinding] = []
    if med_roe is not None and med_roe < thresholds.BANK_ROE_WATCH:
        prof_status = DimensionStatus.FAIL.value
        prof_findings.append(
            FinancialFinding(
                code="WEAK_BANK_ROE",
                category="PROFITABILITY",
                severity=FindingSeverity.HIGH.value,
                confidence=ConfidenceLevel.HIGH.value,
                status=DimensionStatus.FAIL.value,
                start_period=years[0],
                end_period=years[-1],
                metrics={"median_roe": med_roe},
                evidence_fact_ids=[f"IS.PROFIT.NET FY{years[-1]}", f"BS.EQUITY.TOTAL FY{years[-1]}"],
                explanation=f"ROE trung vị ngân hàng ({med_roe*100:.1f}%) dưới ngưỡng an toàn ({thresholds.BANK_ROE_WATCH*100:.1f}%).",
                archetype="BANK",
            )
        )
    elif med_roe is not None and med_roe < thresholds.BANK_ROE_PASS:
        prof_status = DimensionStatus.WATCH.value

    bs_status = DimensionStatus.PASS.value
    bs_findings: List[FinancialFinding] = []
    if equity_assets_ratio is not None and equity_assets_ratio < thresholds.BANK_EQUITY_ASSETS_MIN:
        bs_status = DimensionStatus.WATCH.value
        bs_findings.append(
            FinancialFinding(
                code="LOW_BANK_CAPITAL_ADEQUACY",
                category="BALANCE_SHEET",
                severity=FindingSeverity.MEDIUM.value,
                confidence=ConfidenceLevel.HIGH.value,
                status=DimensionStatus.WATCH.value,
                start_period=years[-1],
                end_period=years[-1],
                metrics={"equity_assets_ratio": equity_assets_ratio},
                evidence_fact_ids=[f"BS.EQUITY.TOTAL FY{years[-1]}", f"BS.ASSETS.TOTAL FY{years[-1]}"],
                explanation=f"Tỷ lệ Vốn chủ / Tổng tài sản ({equity_assets_ratio*100:.1f}%) ở mức thấp.",
                archetype="BANK",
            )
        )

    growth_res = FinancialDimensionResult(
        status=DimensionStatus.PASS.value if pat_cagr and pat_cagr > 0.08 else DimensionStatus.WATCH.value,
        confidence=ConfidenceLevel.HIGH.value,
        metrics={
            "net_profit_cagr": pat_cagr,
            "equity_cagr": eq_cagr,
            "eps_cagr": eps_cagr,
            "annual_share_growth": share_cagr,
            "share_cagr": share_cagr,
        },
        findings=[],
        evidence=[f"IS.PROFIT.NET FY{years[-1]}"],
        missing_data=[],
        not_applicable=[],
        explanation=f"Tăng trưởng LNST ngân hàng CAGR {(pat_cagr*100):.1f}%" if pat_cagr is not None else "LNST ngân hàng tăng trưởng ổn định.",
    )

    prof_res = FinancialDimensionResult(
        status=prof_status,
        confidence=ConfidenceLevel.HIGH.value,
        metrics={
            "median_roe": med_roe,
            "median_roa": med_roa,
            "margin_trend": "STABLE" if med_roe else "NOT_APPLICABLE",
        },
        findings=prof_findings,
        evidence=[f"IS.PROFIT.NET FY{years[-1]}", f"BS.EQUITY.TOTAL FY{years[-1]}"],
        missing_data=[],
        not_applicable=[],
        explanation=f"ROE trung vị ngân hàng đạt {med_roe*100:.1f}%." if med_roe is not None else "Không có đủ dữ liệu ROE ngân hàng.",
    )

    durability_res = FinancialDimensionResult(
        status=DimensionStatus.PASS.value if negative_years == 0 else DimensionStatus.WATCH.value,
        confidence=ConfidenceLevel.HIGH.value,
        metrics={
            "profitable_years": profitable_years,
            "negative_earnings_years": negative_years,
            "total_years": total_y,
            "pat_volatility": pat_vol,
            "profit_volatility": pat_vol,
        },
        findings=[],
        evidence=[f"IS.PROFIT.NET FY{y}" for y in years],
        missing_data=[],
        not_applicable=[],
        explanation=f"Ngân hàng duy trì lợi nhuận dương {profitable_years}/{total_y} năm quan sát.",
    )

    bs_res = FinancialDimensionResult(
        status=bs_status,
        confidence=ConfidenceLevel.HIGH.value,
        metrics={
            "latest_debt_equity": None,
            "debt_equity_ratio": None,
            "equity_assets_ratio": equity_assets_ratio,
            "bank_leverage": bank_leverage,
        },
        findings=bs_findings,
        evidence=[f"BS.EQUITY.TOTAL FY{years[-1]}", f"BS.ASSETS.TOTAL FY{years[-1]}"],
        missing_data=[],
        not_applicable=["INDUSTRIAL_DEBT_EQUITY"],
        explanation=f"Vốn chủ / Tổng tài sản: {equity_assets_ratio*100:.1f}%." if equity_assets_ratio is not None else "Bảng cân đối ngân hàng ổn định.",
    )

    cap_eff_res = FinancialDimensionResult(
        status=prof_status,
        confidence=ConfidenceLevel.HIGH.value,
        metrics={
            "median_roe": med_roe,
            "median_roa": med_roa,
            "median_roic": None,
        },
        findings=[],
        evidence=[],
        missing_data=[],
        not_applicable=["INDUSTRIAL_ROIC"],
        explanation=f"Hiệu quả sử dụng vốn ngân hàng (ROE trung vị {med_roe*100:.1f}%)." if med_roe is not None else "Chưa đủ dữ liệu.",
    )

    cap_alloc_res = FinancialDimensionResult(
        status=DimensionStatus.PASS.value if pat_cagr and pat_cagr > 0.05 else DimensionStatus.WATCH.value,
        confidence=ConfidenceLevel.HIGH.value,
        metrics={
            "retained_earnings_effectiveness": "HIGH" if (pat_cagr and pat_cagr >= 0.15) else "POSITIVE",
            "retained_earnings_cagr": eq_cagr,
        },
        findings=[],
        evidence=[],
        missing_data=[],
        not_applicable=[],
        explanation="Phân bổ vốn duy trì tăng trưởng ngân hàng bền vững.",
    )

    dilution_res = FinancialDimensionResult(
        status=DimensionStatus.PASS.value if (share_cagr is not None and share_cagr <= 0.08) else DimensionStatus.WATCH.value,
        confidence=ConfidenceLevel.HIGH.value,
        metrics={
            "annual_share_growth": share_cagr,
            "share_cagr": share_cagr,
            "dilution_cagr": share_cagr,
            "pat_cagr": pat_cagr,
            "eps_cagr": eps_cagr,
        },
        findings=[],
        evidence=[],
        missing_data=[],
        not_applicable=[],
        explanation=f"Pha loãng cổ phần ngân hàng trung bình {share_cagr*100:.1f}%/năm." if share_cagr is not None else "Không phát hiện pha loãng cổ phần đáng kể.",
    )

    return {
        "growth": growth_res,
        "profitability": prof_res,
        "durability": durability_res,
        "balance_sheet": bs_res,
        "debt_liquidity": bs_res,
        "capital_efficiency": cap_eff_res,
        "capital_allocation": cap_alloc_res,
        "dilution": dilution_res,
    }


def analyze_securities(
    history_data: Dict[str, Any],
    thresholds: MungerThresholdPolicy = DEFAULT_MUNGER_THRESHOLD_POLICY,
) -> Dict[str, FinancialDimensionResult]:
    """Run specialized financial statement analysis for SECURITIES (e.g. VIX)."""
    by_year = history_data.get("by_year", {})
    years = history_data.get("years", [])

    if not years:
        empty_res = FinancialDimensionResult(
            status=DimensionStatus.UNKNOWN.value,
            confidence=ConfidenceLevel.LOW.value,
            metrics={},
            findings=[],
            evidence=[],
            missing_data=["FINANCIAL_HISTORY"],
            not_applicable=[],
            explanation="Không có dữ liệu lịch sử công ty chứng khoán.",
        )
        return {
            "growth": empty_res,
            "profitability": empty_res,
            "durability": empty_res,
            "balance_sheet": empty_res,
            "debt_liquidity": empty_res,
            "capital_efficiency": empty_res,
            "capital_allocation": empty_res,
            "dilution": empty_res,
        }

    rev_list = [by_year[y].get("revenue") for y in years if by_year[y].get("revenue") is not None]
    pat_list = [by_year[y].get("net_profit") for y in years if by_year[y].get("net_profit") is not None]
    eq_list = [by_year[y].get("equity") for y in years if by_year[y].get("equity") is not None]
    sh_list = [by_year[y].get("outstanding_shares") for y in years if by_year[y].get("outstanding_shares") is not None]

    rev_cagr = (rev_list[-1] / rev_list[0]) ** (1.0 / (len(rev_list) - 1)) - 1.0 if len(rev_list) >= 2 and rev_list[0] > 0 and rev_list[-1] > 0 else None
    pat_cagr = (pat_list[-1] / pat_list[0]) ** (1.0 / (len(pat_list) - 1)) - 1.0 if len(pat_list) >= 2 and pat_list[0] > 0 and pat_list[-1] > 0 else None
    eq_cagr = (eq_list[-1] / eq_list[0]) ** (1.0 / (len(eq_list) - 1)) - 1.0 if len(eq_list) >= 2 and eq_list[0] > 0 and eq_list[-1] > 0 else None
    share_cagr = (sh_list[-1] / sh_list[0]) ** (1.0 / (len(sh_list) - 1)) - 1.0 if len(sh_list) >= 2 and sh_list[0] > 0 and sh_list[-1] > 0 else None

    latest_shares = float(sh_list[-1]) if (sh_list and float(sh_list[-1]) > 0) else None
    eps_list = []
    for y in years:
        p = by_year[y].get("net_profit")
        if p is not None:
            if latest_shares:
                eps_list.append(float(p) / latest_shares)
            else:
                s = by_year[y].get("outstanding_shares")
                if s is not None and float(s) > 0:
                    eps_list.append(float(p) / float(s))
    eps_cagr = (eps_list[-1] / eps_list[0]) ** (1.0 / (len(eps_list) - 1)) - 1.0 if len(eps_list) >= 2 and eps_list[0] > 0 and eps_list[-1] > 0 else None

    roe_series = []
    margin_series = []
    leverage_series = []
    for y in years:
        p = by_year[y].get("net_profit")
        e = by_year[y].get("equity")
        r = by_year[y].get("revenue")
        a = by_year[y].get("total_assets")
        if p is not None and e is not None and float(e) > 0:
            roe_series.append(float(p) / float(e))
        if p is not None and r is not None and float(r) > 0:
            margin_series.append(float(p) / float(r))
        if a is not None and e is not None and float(e) > 0:
            leverage_series.append(float(a) / float(e))

    med_roe = sorted(roe_series)[len(roe_series)//2] if roe_series else None
    med_margin = sorted(margin_series)[len(margin_series)//2] if margin_series else None
    med_leverage = sorted(leverage_series)[len(leverage_series)//2] if leverage_series else None

    margin_trend = "STABLE"
    if len(margin_series) >= 2:
        rec_3y_m = sum(margin_series[-3:]) / len(margin_series[-3:])
        hist_m = sum(margin_series) / len(margin_series)
        if rec_3y_m > hist_m + 0.005:
            margin_trend = "EXPANDING"
        elif rec_3y_m < hist_m - 0.005:
            margin_trend = "DECLINING"

    last_ydict = by_year[years[-1]]
    fvtpl_gain = last_ydict.get("IS.PROFIT.TRADING") or last_ydict.get("fvtpl_gain") or 0.0
    op_income = last_ydict.get("operating_profit") or last_ydict.get("net_profit") or 1.0
    fvtpl_ratio = float(fvtpl_gain) / float(op_income) if op_income > 0 else 0.0

    profitable_years = sum(1 for p in pat_list if p is not None and p > 0)
    negative_years = sum(1 for p in pat_list if p is not None and p <= 0)
    total_y = len(pat_list)

    pat_vol = None
    if len(pat_list) >= 3:
        mean_p = sum(pat_list) / len(pat_list)
        if mean_p != 0:
            var_p = sum((p - mean_p) ** 2 for p in pat_list) / len(pat_list)
            std_p = math.sqrt(var_p)
            pat_vol = std_p / abs(mean_p)

    raw_debt = last_ydict.get("total_debt")
    raw_eq = last_ydict.get("equity")
    tot_debt = float(raw_debt) if raw_debt is not None else None
    tot_eq = float(raw_eq) if raw_eq is not None else None
    de_ratio = (tot_debt / tot_eq) if (tot_debt is not None and tot_eq is not None and tot_eq > 0) else None

    prof_status = DimensionStatus.PASS.value
    prof_findings: List[FinancialFinding] = []
    if med_roe is not None and med_roe < thresholds.SECURITIES_ROE_WATCH:
        prof_status = DimensionStatus.FAIL.value
        prof_findings.append(
            FinancialFinding(
                code="WEAK_SECURITIES_ROE",
                category="PROFITABILITY",
                severity=FindingSeverity.HIGH.value,
                confidence=ConfidenceLevel.HIGH.value,
                status=DimensionStatus.FAIL.value,
                start_period=years[0],
                end_period=years[-1],
                metrics={"median_roe": med_roe, "margin_trend": margin_trend},
                evidence_fact_ids=[f"IS.PROFIT.NET FY{years[-1]}", f"BS.EQUITY.TOTAL FY{years[-1]}"],
                explanation=f"ROE trung vị công ty chứng khoán ({med_roe*100:.1f}%) dưới ngưỡng cảnh báo ({thresholds.SECURITIES_ROE_WATCH*100:.1f}%).",
                archetype="SECURITIES",
            )
        )
    elif fvtpl_ratio > thresholds.SECURITIES_FVTPL_DEPENDENCE_HIGH:
        prof_status = DimensionStatus.WATCH.value
        prof_findings.append(
            FinancialFinding(
                code="TRADING_INCOME_DEPENDENCE",
                category="PROFITABILITY",
                severity=FindingSeverity.MEDIUM.value,
                confidence=ConfidenceLevel.HIGH.value,
                status=DimensionStatus.WATCH.value,
                start_period=years[-1],
                end_period=years[-1],
                metrics={"fvtpl_ratio": fvtpl_ratio},
                evidence_fact_ids=[f"IS.PROFIT.NET FY{years[-1]}"],
                explanation=f"Lợi nhuận phụ thuộc đáng kể vào hoạt động tự doanh / FVTPL (chiếm {fvtpl_ratio*100:.1f}% lợi nhuận).",
                archetype="SECURITIES",
            )
        )

    bs_status = DimensionStatus.PASS.value
    bs_findings: List[FinancialFinding] = []
    if med_leverage is not None and med_leverage > thresholds.SECURITIES_LEVERAGE_WATCH:
        bs_status = DimensionStatus.WATCH.value
        bs_findings.append(
            FinancialFinding(
                code="SECURITIES_HIGH_LEVERAGE",
                category="BALANCE_SHEET",
                severity=FindingSeverity.MEDIUM.value,
                confidence=ConfidenceLevel.HIGH.value,
                status=DimensionStatus.WATCH.value,
                start_period=years[0],
                end_period=years[-1],
                metrics={"median_leverage": med_leverage},
                evidence_fact_ids=[f"BS.ASSETS.TOTAL FY{years[-1]}", f"BS.EQUITY.TOTAL FY{years[-1]}"],
                explanation=f"Đòn bẩy tài chính (Tổng tài sản / Vốn chủ) ở mức cao {med_leverage:.2f}x.",
                archetype="SECURITIES",
            )
        )

    growth_res = FinancialDimensionResult(
        status=DimensionStatus.PASS.value if pat_cagr and pat_cagr > 0.08 else DimensionStatus.WATCH.value,
        confidence=ConfidenceLevel.HIGH.value,
        metrics={
            "revenue_cagr": rev_cagr,
            "net_profit_cagr": pat_cagr,
            "equity_cagr": eq_cagr,
            "eps_cagr": eps_cagr,
            "annual_share_growth": share_cagr,
            "share_cagr": share_cagr,
        },
        findings=[],
        evidence=[f"IS.PROFIT.NET FY{years[-1]}"],
        missing_data=[],
        not_applicable=[],
        explanation=f"Tăng trưởng LNST chứng khoán CAGR {(pat_cagr*100):.1f}%" if pat_cagr is not None else "LNST chứng khoán tăng trưởng theo thị trường.",
    )

    prof_res = FinancialDimensionResult(
        status=prof_status,
        confidence=ConfidenceLevel.HIGH.value,
        metrics={
            "median_roe": med_roe,
            "median_net_margin": med_margin,
            "margin_trend": margin_trend,
            "fvtpl_dependence_ratio": fvtpl_ratio,
        },
        findings=prof_findings,
        evidence=[f"IS.PROFIT.NET FY{years[-1]}", f"BS.EQUITY.TOTAL FY{years[-1]}"],
        missing_data=[],
        not_applicable=[],
        explanation=f"ROE trung vị công ty chứng khoán: {med_roe*100:.1f}%." if med_roe is not None else "Không có đủ dữ liệu ROE công ty chứng khoán.",
    )

    durability_res = FinancialDimensionResult(
        status=DimensionStatus.PASS.value if negative_years == 0 else DimensionStatus.WATCH.value,
        confidence=ConfidenceLevel.HIGH.value,
        metrics={
            "profitable_years": profitable_years,
            "negative_earnings_years": negative_years,
            "total_years": total_y,
            "pat_volatility": pat_vol,
            "profit_volatility": pat_vol,
        },
        findings=[],
        evidence=[f"IS.PROFIT.NET FY{y}" for y in years],
        missing_data=[],
        not_applicable=[],
        explanation=f"Lợi nhuận dương {profitable_years}/{total_y} năm quan sát.",
    )

    bs_res = FinancialDimensionResult(
        status=bs_status,
        confidence=ConfidenceLevel.HIGH.value,
        metrics={
            "latest_debt_equity": de_ratio,
            "debt_equity_ratio": de_ratio,
            "median_leverage": med_leverage,
            "total_debt": tot_debt,
            "equity": tot_eq,
        },
        findings=bs_findings,
        evidence=[f"BS.ASSETS.TOTAL FY{years[-1]}", f"BS.EQUITY.TOTAL FY{years[-1]}"],
        missing_data=[],
        not_applicable=[],
        explanation=f"Đòn bẩy tài chính trung vị: {med_leverage:.2f}x." if med_leverage is not None else "Bảng cân đối chứng khoán hoạt động an toàn.",
    )

    cap_eff_res = FinancialDimensionResult(
        status=prof_status,
        confidence=ConfidenceLevel.HIGH.value,
        metrics={
            "median_roe": med_roe,
            "median_roic": med_roe,
        },
        findings=[],
        evidence=[],
        missing_data=[],
        not_applicable=[],
        explanation=f"Hiệu quả sử dụng vốn cổ phần (ROE trung vị {med_roe*100:.1f}%)." if med_roe is not None else "Chưa đủ dữ liệu.",
    )

    cap_alloc_res = FinancialDimensionResult(
        status=DimensionStatus.PASS.value if pat_cagr and pat_cagr > 0.05 else DimensionStatus.WATCH.value,
        confidence=ConfidenceLevel.HIGH.value,
        metrics={
            "retained_earnings_effectiveness": "HIGH" if (pat_cagr and pat_cagr >= 0.15) else "POSITIVE",
            "retained_earnings_cagr": eq_cagr,
        },
        findings=[],
        evidence=[],
        missing_data=[],
        not_applicable=[],
        explanation="Phân bổ vốn duy trì tăng trưởng công ty chứng khoán.",
    )

    dilution_res = FinancialDimensionResult(
        status=DimensionStatus.PASS.value if (share_cagr is not None and share_cagr <= 0.08) else DimensionStatus.WATCH.value,
        confidence=ConfidenceLevel.HIGH.value,
        metrics={
            "annual_share_growth": share_cagr,
            "share_cagr": share_cagr,
            "dilution_cagr": share_cagr,
            "pat_cagr": pat_cagr,
            "eps_cagr": eps_cagr,
        },
        findings=[],
        evidence=[],
        missing_data=[],
        not_applicable=[],
        explanation=f"Pha loãng cổ phần chứng khoán trung bình {share_cagr*100:.1f}%/năm." if share_cagr is not None else "Không phát hiện pha loãng cổ phần đáng kể.",
    )

    return {
        "growth": growth_res,
        "profitability": prof_res,
        "durability": durability_res,
        "balance_sheet": bs_res,
        "debt_liquidity": bs_res,
        "capital_efficiency": cap_eff_res,
        "capital_allocation": cap_alloc_res,
        "dilution": dilution_res,
    }
