"""High-Level Munger Financial Statement Analysis Orchestrator (Task 136, Task 154).

Orchestrates full evidence-driven long-term financial analysis across 16 deterministic gates:
GATE 1: Data completeness
GATE 2: Accounting consistency
GATE 3: Balance sheet / Solvency
GATE 4: Earnings quality
GATE 5: Cash conversion
GATE 6: Earnings durability
GATE 7: Capital efficiency
GATE 8: Capital allocation
GATE 9: Dilution
GATE 10: Financial forensics (10 pairings)
GATE 11: Structural deterioration / Value trap
GATE 12: Normalized earnings (3Y/5Y/10Y/Median/Volatility/Peak-Trough)
GATE 13: Bear case resilience
GATE 14: Valuation readiness
GATE 15: Margin of Safety (MOS)
GATE 16: Portfolio / Personal capital constraints
-> Final Action

Sole evidence source: Canonical SSI Annual Financial Statements in PostgreSQL.
"""

from __future__ import annotations

import math
from typing import Any, Dict, List, Optional
from .archetypes import ArchetypeClassifier, EconomicArchetype
from .munger_archetype_analyzers import (
    analyze_bank,
    analyze_normal_enterprise,
    analyze_securities,
)
from .munger_forensics import (
    classify_structural_vs_cyclical_deterioration,
    run_accounting_consistency_checks,
    run_earnings_quality_forensics,
    run_inventory_forensics,
    run_receivables_forensics,
)
from .munger_history_builder import build_financial_history_from_facts
from .munger_models import (
    CompounderClassification,
    ConfidenceLevel,
    DeteriorationClassification,
    DimensionStatus,
    FindingSeverity,
    FinancialBusinessAnalysis,
    FinancialDimensionResult,
    FinancialFinding,
)
from .munger_thresholds import DEFAULT_MUNGER_THRESHOLD_POLICY, MungerThresholdPolicy
from .vietnamese_presenter import (
    get_vietnamese_deterioration,
    get_vietnamese_finding_title,
    get_vietnamese_valuetrap,
)


def build_munger_financial_analysis(
    symbol: str,
    provider: str = "ssi",
    raw_facts: Optional[List[Dict[str, Any]]] = None,
    existing_history: Optional[List[Dict[str, Any]]] = None,
    thresholds: MungerThresholdPolicy = DEFAULT_MUNGER_THRESHOLD_POLICY,
    valuation_data: Optional[Dict[str, Any]] = None,
) -> FinancialBusinessAnalysis:
    """Build canonical FinancialBusinessAnalysis for a symbol."""
    ticker = symbol.strip().upper()

    # Auto-retrieve canonical valuation if not explicitly passed
    if valuation_data is None:
        try:
            from portfolio.canonical_valuation import build_canonical_valuation
            val_res = build_canonical_valuation(ticker, compute_munger=False)
            if val_res.get("ok"):
                valuation_data = {
                    "status": "READY" if val_res.get("base_iv") is not None else "INCOMPLETE",
                    "current_price": val_res.get("current_price"),
                    "bear_iv": val_res.get("bear_iv"),
                    "base_iv": val_res.get("base_iv"),
                    "bull_iv": val_res.get("bull_iv"),
                    "actual_mos_pct": val_res.get("actual_mos_pct"),
                    "required_mos_pct": val_res.get("required_mos_pct"),
                    "valuation_confidence": val_res.get("valuation_confidence", "MEDIUM"),
                    "quality_tier": val_res.get("quality_tier"),
                }
        except Exception:
            valuation_data = None

    # 1. GATE 1: Build Multi-Year History & Check Data Completeness
    history_data = build_financial_history_from_facts(ticker, raw_facts=raw_facts, existing_history=existing_history)
    years = history_data.get("years", [])
    history_start = history_data.get("history_start", 0)
    history_end = history_data.get("history_end", 0)
    history_years = history_data.get("history_years", 0)
    history_depth = history_data.get("history_depth", "INSUFFICIENT_HISTORY")
    effective_provider = history_data.get("provider", provider)

    # 2. Archetype Router
    classifier = ArchetypeClassifier()
    archetype_profile = classifier.classify(ticker)
    archetype_enum = archetype_profile.archetype
    archetype_str = (
        "BANK" if (archetype_enum == EconomicArchetype.COMMERCIAL_BANK or ticker in {"ACB", "VCB", "BID", "CTG", "MBB", "TCB", "VPB", "STB", "HDB", "TPB", "VIB", "MSB", "LPB", "EIB", "OCB", "SSB", "BAB", "NAB", "BVB", "ABB", "PGB", "SGB"})
        else ("SECURITIES" if (archetype_enum == EconomicArchetype.SECURITIES_BROKER or ticker in {"VIX", "SSI", "VND", "HCM", "VCI", "MBS", "SHS", "CTS", "FTS", "BSI", "ORS", "AGR", "VDS", "TCBS"})
        else "NORMAL_ENTERPRISE")
    )

    data_readiness = "READY" if history_years >= 5 else ("PARTIAL" if history_years >= 3 else "INSUFFICIENT")

    # 3. GATE 2 & 4 & 5 & 10: Forensics, Accounting Consistency, Earnings Quality, Receivables, Inventory
    acct_res = run_accounting_consistency_checks(history_data, thresholds)
    eq_res = run_earnings_quality_forensics(history_data, archetype_str, thresholds)
    rec_res = run_receivables_forensics(history_data, archetype_str, thresholds)
    inv_res = run_inventory_forensics(history_data, archetype_str, thresholds)

    all_findings: List[FinancialFinding] = []
    for r in (acct_res, eq_res, rec_res, inv_res):
        all_findings.extend(r.findings)

    forensics_status = DimensionStatus.PASS.value
    if any(f.status == DimensionStatus.FAIL.value for f in all_findings):
        forensics_status = DimensionStatus.FAIL.value
    elif any(f.status == DimensionStatus.WATCH.value for f in all_findings):
        forensics_status = DimensionStatus.WATCH.value

    forensics_res = FinancialDimensionResult(
        status=forensics_status,
        confidence=ConfidenceLevel.HIGH.value if history_years >= 5 else ConfidenceLevel.MEDIUM.value,
        metrics={"total_findings": len(all_findings)},
        findings=all_findings,
        evidence=[f.code for f in all_findings],
        missing_data=[],
        not_applicable=[],
        explanation=f"Phát hiện {len(all_findings)} vấn đề cần lưu ý trong BCTC." if all_findings else "Không phát hiện dấu hiệu bất thường BCTC nghiêm trọng.",
    )

    # 4. GATES 6, 7, 8, 9: Archetype-Specific Analyzers (Durability, Profitability, Capital Efficiency, Allocation, Dilution)
    if archetype_str == "BANK":
        arch_dict = analyze_bank(history_data, thresholds)
    elif archetype_str == "SECURITIES":
        arch_dict = analyze_securities(history_data, thresholds)
    else:
        arch_dict = analyze_normal_enterprise(history_data, thresholds)

    growth_res = arch_dict["growth"]
    prof_res = arch_dict["profitability"]
    dur_res = arch_dict["durability"]
    bs_res = arch_dict["balance_sheet"]
    debt_res = arch_dict["debt_liquidity"]
    cap_eff_res = arch_dict["capital_efficiency"]
    cap_alloc_res = arch_dict["capital_allocation"]
    dilution_res = arch_dict["dilution"]

    # Add findings from archetype analyzers
    for r in (growth_res, prof_res, dur_res, bs_res, debt_res, cap_eff_res, cap_alloc_res, dilution_res):
        for f in r.findings:
            if f not in all_findings:
                all_findings.append(f)

    # 5. GATE 12: Normalized Earning Power & Earnings Volatility Deep Dive
    by_year = history_data.get("by_year", {})
    pat_series = [float(by_year[y]["net_profit"]) for y in years if by_year.get(y, {}).get("net_profit") is not None]
    reported_latest = pat_series[-1] if pat_series else None

    norm_3y = sum(pat_series[-3:]) / min(3, len(pat_series)) if pat_series else None
    norm_5y = sum(pat_series[-5:]) / min(5, len(pat_series)) if pat_series else None
    norm_10y = sum(pat_series[-10:]) / min(10, len(pat_series)) if len(pat_series) >= 5 else norm_5y

    clean_pats = sorted(pat_series) if pat_series else []
    n_p = len(clean_pats)
    median_pat = (clean_pats[n_p // 2] if n_p % 2 != 0 else (clean_pats[n_p // 2 - 1] + clean_pats[n_p // 2]) / 2.0) if clean_pats else None
    mean_pat = (sum(pat_series) / len(pat_series)) if pat_series else None

    earnings_volatility = 0.0
    if pat_series and mean_pat and abs(mean_pat) > 0:
        variance = sum((p - mean_pat) ** 2 for p in pat_series) / len(pat_series)
        std_dev = math.sqrt(variance)
        earnings_volatility = round(std_dev / abs(mean_pat), 4)

    is_peak_earnings = bool(reported_latest and norm_5y and norm_5y > 0 and reported_latest >= 1.50 * norm_5y)
    is_trough_earnings = bool(reported_latest and norm_5y and norm_5y > 0 and reported_latest <= 0.60 * norm_5y)

    norm_exp = "Chưa đủ dữ liệu lợi nhuận chuẩn hóa."
    if norm_5y and reported_latest:
        if is_peak_earnings:
            norm_exp = (
                f"LNST hiện tại ({reported_latest:,.0f} đ) cao hơn đáng kể mức bình thường hóa lịch sử (5 năm: {norm_5y:,.0f} đ, biến động CV: {earnings_volatility*100:.1f}%); "
                f"cần kiểm tra khả năng đây là lợi nhuận ở vùng cao của chu kỳ (Cảnh báo định giá / biên an toàn, không phải lỗi chất lượng kinh doanh cốt lõi)."
            )
        elif is_trough_earnings:
            norm_exp = (
                f"Lợi nhuận gần nhất ({reported_latest:,.0f} đ) đang ở vùng đáy chu kỳ hoặc chịu chi phí bất thường so với mức bình thường hóa 5 năm ({norm_5y:,.0f} đ)."
            )
        else:
            norm_exp = f"Lợi nhuận chuẩn hóa 5 năm đạt {norm_5y:,.0f} đ so với gần nhất {reported_latest:,.0f} đ (Biến động CV: {earnings_volatility*100:.1f}%)."

    normalized_earning_power = {
        "reported_latest": reported_latest,
        "normalized_3y": norm_3y,
        "normalized_5y": norm_5y,
        "normalized_10y": norm_10y,
        "median_pat": median_pat,
        "mean_pat": mean_pat,
        "earnings_volatility": earnings_volatility,
        "is_peak_earnings": is_peak_earnings,
        "is_trough_earnings": is_trough_earnings,
        "earning_power_divergence": (reported_latest - norm_5y) if reported_latest is not None and norm_5y is not None else None,
        "explanation": norm_exp,
    }

    # 6. GATE 11: Structural vs Cyclical Deterioration & Value Trap
    growth_metrics = growth_res.metrics
    prof_metrics = prof_res.metrics
    dur_metrics = dur_res.metrics
    structural_dict = classify_structural_vs_cyclical_deterioration(all_findings, growth_metrics, prof_metrics, dur_metrics)

    # 7. Overall Financial Quality Summary & Hard Failures
    overall_quality = {
        "growth": growth_res.status,
        "profitability": prof_res.status,
        "durability": dur_res.status,
        "earnings_quality": eq_res.status if archetype_str == "NORMAL_ENTERPRISE" else DimensionStatus.NOT_APPLICABLE.value,
        "cash_flow_quality": eq_res.status,
        "balance_sheet": bs_res.status,
        "debt_liquidity": debt_res.status,
        "capital_efficiency": cap_eff_res.status,
        "capital_allocation": cap_alloc_res.status,
        "dilution": dilution_res.status,
        "accounting_consistency": acct_res.status,
        "forensics": forensics_status,
    }

    hard_failures = [
        f.code for f in all_findings
        if f.severity == FindingSeverity.CRITICAL.value
        or (f.severity == FindingSeverity.HIGH.value and f.category not in ("WORKING_CAPITAL",))
    ]
    warnings = [f.code for f in all_findings if f.code not in hard_failures]
    med_roe = prof_metrics.get("median_roe")
    pat_cagr = growth_metrics.get("net_profit_cagr")
    eps_cagr = growth_metrics.get("eps_cagr")
    rev_cagr = growth_metrics.get("revenue_cagr")
    structural_class = structural_dict.get("classification")
    negative_earnings_years = dur_metrics.get("negative_earnings_years", 0)
    cyclical_rebound = dur_metrics.get("cyclical_rebound_observed", False)
    eq_status = eq_res.status
    cfo_pat_median = eq_res.metrics.get("median_cfo_pat") or eq_res.metrics.get("avg_cfo_pat")

    if data_readiness == "INSUFFICIENT" or history_years < 3:
        compounder_class = CompounderClassification.INSUFFICIENT_DATA.value
    elif structural_class in (DeteriorationClassification.STRUCTURAL.value, DeteriorationClassification.POSSIBLY_STRUCTURAL.value) or hard_failures:
        compounder_class = CompounderClassification.DETERIORATING_BUSINESS.value
    elif med_roe is not None and med_roe >= thresholds.ROE_PASS:
        # Strict Durable Compounder standard:
        # (1) Proven track record >= 5 years
        # (2) Stable non-cyclical earnings: volatility < 0.35, no loss years
        # (3) Solid growth: PAT CAGR >= 8% (and EPS CAGR >= 6% if available)
        # (4) Healthy cash conversion: CFO/PAT median >= 0.70x (and earnings quality not FAIL)
        # (5) Fortress capital: no debt failure, no capital allocation failure, no destructive dilution
        is_durable_history = history_years >= 5
        is_low_volatility = earnings_volatility < 0.35 and negative_earnings_years == 0 and not cyclical_rebound
        is_solid_growth = (pat_cagr is not None and pat_cagr >= 0.08) and (eps_cagr is None or eps_cagr >= 0.06)
        is_cash_healthy = (cfo_pat_median is None or cfo_pat_median >= 0.70) and eq_status != DimensionStatus.FAIL.value
        is_balance_sheet_safe = debt_res.status != DimensionStatus.FAIL.value and cap_alloc_res.status != DimensionStatus.FAIL.value and dilution_res.status != DimensionStatus.FAIL.value

        if is_durable_history and is_low_volatility and is_solid_growth and is_cash_healthy and is_balance_sheet_safe:
            compounder_class = CompounderClassification.COMPOUNDER.value
        elif (earnings_volatility >= 0.35 or cyclical_rebound) and (pat_cagr is not None and pat_cagr >= 0.08 or med_roe >= thresholds.ROE_PASS):
            # High return but exposed to macroeconomic / commodity / sector cycle fluctuations
            compounder_class = CompounderClassification.CYCLICAL_QUALITY.value
        elif is_solid_growth or (history_years < 5 and med_roe >= thresholds.ROE_PASS):
            # Good business with potential, or track record still maturing
            compounder_class = CompounderClassification.POTENTIAL_COMPOUNDER.value
        else:
            compounder_class = CompounderClassification.AVERAGE_BUSINESS.value
    elif med_roe is not None and med_roe >= thresholds.ROE_WATCH:
        if earnings_volatility >= 0.35 or cyclical_rebound or (pat_cagr is not None and pat_cagr >= 0.08 and earnings_volatility >= 0.30):
            compounder_class = CompounderClassification.CYCLICAL_QUALITY.value
        elif pat_cagr is not None and pat_cagr >= 0.10 and earnings_volatility < 0.35:
            compounder_class = CompounderClassification.POTENTIAL_COMPOUNDER.value
        else:
            compounder_class = CompounderClassification.AVERAGE_BUSINESS.value
    else:
        compounder_class = CompounderClassification.WEAK_BUSINESS.value

    # 9. Value Trap Assessment (Multi-signal integration)
    vt_status = "CLEAR"
    if hard_failures or structural_class == DeteriorationClassification.STRUCTURAL.value:
        vt_status = "HIGH_RISK"
    elif warnings or structural_class in (DeteriorationClassification.POSSIBLY_STRUCTURAL.value, DeteriorationClassification.POSSIBLY_CYCLICAL.value):
        vt_status = "WATCH"

    from .vietnamese_presenter import (
        get_vietnamese_classification,
        get_vietnamese_decision,
        get_vietnamese_deterioration,
        get_vietnamese_status,
        get_vietnamese_valuetrap,
    )

    value_trap_assessment = {
        "status": vt_status,
        "deterioration_classification": structural_class,
        "hard_failures": hard_failures,
        "warnings": warnings,
        "explanation": f"Đánh giá Bẫy giá trị: {get_vietnamese_valuetrap(vt_status)}. Trạng thái cấu trúc: {get_vietnamese_deterioration(structural_class)}.",
    }

    # 10. GATES 13, 14, 15: Canonical Valuation & Required MOS Integration
    val_payload = valuation_data or {}
    val_status = val_payload.get("status", "INCOMPLETE")
    curr_price = val_payload.get("current_price")
    bear_iv = val_payload.get("bear_iv")
    base_iv = val_payload.get("base_iv")
    bull_iv = val_payload.get("bull_iv")
    actual_mos = val_payload.get("actual_mos_pct")
    val_confidence = val_payload.get("valuation_confidence", "MEDIUM")

    canonical_req_mos = val_payload.get("required_mos_pct")
    if canonical_req_mos is not None:
        required_mos = float(canonical_req_mos)
    else:
        base_req_mos = thresholds.BASE_REQUIRED_MOS_AVERAGE
        if compounder_class == CompounderClassification.COMPOUNDER.value:
            base_req_mos = thresholds.BASE_REQUIRED_MOS_COMPOUNDER
        elif compounder_class in (CompounderClassification.POTENTIAL_COMPOUNDER.value, CompounderClassification.CYCLICAL_QUALITY.value):
            base_req_mos = thresholds.BASE_REQUIRED_MOS_POTENTIAL_COMPOUNDER
        elif compounder_class == CompounderClassification.AVERAGE_BUSINESS.value:
            base_req_mos = thresholds.BASE_REQUIRED_MOS_AVERAGE
        elif compounder_class in (CompounderClassification.WEAK_BUSINESS.value, CompounderClassification.DETERIORATING_BUSINESS.value):
            base_req_mos = thresholds.BASE_REQUIRED_MOS_WEAK

        addons = 0.0
        if vt_status == "WATCH":
            addons += thresholds.MOS_ADDON_VALUE_TRAP_WATCH
        if history_depth == "LIMITED":
            addons += thresholds.MOS_ADDON_LIMITED_HISTORY
        if bs_res.status == DimensionStatus.WATCH.value:
            addons += thresholds.MOS_ADDON_BALANCE_SHEET_WATCH
        if val_confidence in ("LOW", "MEDIUM"):
            addons += thresholds.MOS_ADDON_LOW_CONFIDENCE

        required_mos = round(base_req_mos + addons, 1)

    if val_status != "READY" or actual_mos is None or required_mos is None:
        mos_gate = "UNKNOWN"
    elif actual_mos >= required_mos:
        mos_gate = "PASS"
    else:
        mos_gate = "FAIL"

    valuation_analysis = {
        "status": val_status,
        "current_price": curr_price,
        "bear_iv": bear_iv,
        "base_iv": base_iv,
        "bull_iv": bull_iv,
        "actual_mos_pct": actual_mos,
        "required_mos_pct": required_mos,
        "mos_gate": mos_gate,
        "valuation_confidence": val_confidence,
    }

    # 11. Core Deterministic Munger Decision (Anti False-BUY Gate & Separation of Quality vs MOS)
    decision_state = "WAIT_FOR_MOS"
    decision_reason = ""
    primary_blocker_gate = ""

    has_forensic_red_flags = bool(hard_failures or vt_status == "HIGH_RISK" or structural_class in (DeteriorationClassification.STRUCTURAL.value, DeteriorationClassification.POSSIBLY_STRUCTURAL.value))
    has_forensic_warnings = bool(
        "WEAK_CASH_CONVERSION" in warnings
        or "RECEIVABLES_GROW_FASTER_THAN_REVENUE" in warnings
        or "RECEIVABLES_DIVERGENCE" in warnings
        or "INVENTORY_GROWTH_EXCEEDS_SALES" in warnings
        or "INVENTORY_DIVERGENCE" in warnings
        or "INVENTORY_BUILDUP" in warnings
        or "ACCOUNTING_IDENTITY_DISCREPANCY" in warnings
        or earnings_volatility >= 0.40
    )

    monitoring_reasons: List[str] = []
    if warnings:
        for w in warnings:
            monitoring_reasons.append(get_vietnamese_finding_title(w))
    if earnings_volatility >= 0.35:
        monitoring_reasons.append(f"Độ biến động LNST lịch sử tương đối cao (CV {earnings_volatility*100:.1f}%)")
    if is_peak_earnings:
        monitoring_reasons.append("LNST gần nhất cao hơn mức chuẩn hóa lịch sử; cần thận trọng khi sử dụng lợi nhuận hiện tại làm đại diện cho earning power dài hạn")

    if has_forensic_red_flags:
        decision_state = "AVOID"
        primary_blocker_gate = "FORENSIC_GATE" if hard_failures else "VALUE_TRAP_GATE"
        fail_reasons = hard_failures if hard_failures else ([f"Bẫy giá trị rủi ro cao ({get_vietnamese_valuetrap(vt_status)})"] if vt_status == "HIGH_RISK" else [f"Doanh nghiệp suy giảm cấu trúc ({get_vietnamese_deterioration(structural_class)})"])
        decision_reason = f"Phát hiện rủi ro tài chính nghiêm trọng ({', '.join(fail_reasons)})."
    elif data_readiness == "INSUFFICIENT":
        decision_state = "REVIEW_BUSINESS"
        primary_blocker_gate = "DATA_READINESS_GATE"
        decision_reason = "Chưa đủ dữ liệu tài chính lịch sử (dưới 3-5 năm) để hoàn thành đánh giá BCTC."
    elif compounder_class in (CompounderClassification.WEAK_BUSINESS.value, CompounderClassification.DETERIORATING_BUSINESS.value):
        decision_state = "AVOID"
        primary_blocker_gate = "BUSINESS_QUALITY_GATE"
        decision_reason = "Doanh nghiệp có chất lượng tài chính yếu, không đạt tiêu chí tích sản dài hạn."
    elif val_status != "READY" or actual_mos is None:
        decision_state = "REVIEW_BUSINESS"
        primary_blocker_gate = "VALUATION_GATE"
        decision_reason = "Doanh nghiệp chất lượng ổn định nhưng chưa có định giá chuẩn để xác định Biên an toàn."
    elif mos_gate == "PASS":
        # Munger Invariant: When MOS passes (actual_mos >= required_mos), MOS gate is PASS.
        # Hard blockers are PASS. If monitoring signals exist, classify as CONDITIONAL_BUY with explicit distinction.
        if has_forensic_warnings or vt_status == "WATCH" or compounder_class == CompounderClassification.AVERAGE_BUSINESS.value or is_peak_earnings:
            decision_state = "CONDITIONAL_BUY"
            warn_list = [get_vietnamese_finding_title(w) for w in warnings if w in ("WEAK_CASH_CONVERSION", "RECEIVABLES_GROW_FASTER_THAN_REVENUE", "RECEIVABLES_DIVERGENCE", "INVENTORY_GROWTH_EXCEEDS_SALES", "INVENTORY_DIVERGENCE", "INVENTORY_BUILDUP", "ACCOUNTING_IDENTITY_DISCREPANCY")]
            warn_desc = f", các điểm cần theo dõi: {', '.join(warn_list)}" if warn_list else ""
            peak_note = " (LNST gần nhất cao hơn mức chuẩn hóa lịch sử)" if is_peak_earnings else ""
            decision_reason = (
                f"Điều kiện mua đã đạt theo các cổng chính (MOS {actual_mos:.1f}% >= {required_mos:.1f}%), "
                f"nhưng lợi nhuận có độ biến động tương đối cao (CV: {earnings_volatility*100:.1f}%){peak_note} và một số chỉ tiêu cần tiếp tục theo dõi{warn_desc}. "
                f"Khuyến nghị mua có điều kiện / giải ngân thận trọng từng phần."
            )
        elif bear_iv is not None and curr_price is not None and curr_price > bear_iv:
            decision_state = "CONDITIONAL_BUY"
            decision_reason = (
                f"Mức giá hiện tại đạt Biên an toàn cơ sở (MOS {actual_mos:.1f}%), nhưng thị giá ({curr_price:,.0f} đ) "
                f"vẫn cao hơn kịch bản Thận trọng Bear IV ({bear_iv:,.0f} đ). Có thể mua có điều kiện và theo dõi sát kịch bản thận trọng."
            )
        else:
            decision_state = "BUY"
            decision_reason = f"Doanh nghiệp đạt chuẩn chất lượng BCTC và mức giá hiện tại (MOS {actual_mos:.1f}%) đạt/vượt Biên an toàn yêu cầu ({required_mos:.1f}%). Đạt chuẩn mua tích sản."
    else:  # mos_gate == "FAIL"
        decision_state = "WAIT_FOR_MOS"
        primary_blocker_gate = "MOS_GATE"
        decision_reason = f"Doanh nghiệp có chất lượng ({get_vietnamese_classification(compounder_class)}) nhưng mức giá hiện tại (MOS {actual_mos:.1f}%) chưa đạt Biên an toàn yêu cầu ({required_mos:.1f}%). Kiên nhẫn chờ đạt biên an toàn."

    # Machine-readable Decision Trace
    blocking_reasons: List[str] = []
    supporting_evidence: List[str] = []
    critical_risks: List[str] = []

    if mos_gate == "FAIL":
        blocking_reasons.append(f"Biên an toàn thực tế ({actual_mos:.1f}%) chưa đạt yêu cầu ({required_mos:.1f}%)")
    elif mos_gate == "PASS":
        supporting_evidence.append(f"Biên an toàn thực tế ({actual_mos:.1f}%) đạt yêu cầu ({required_mos:.1f}%)")

    if hard_failures:
        for h in hard_failures:
            critical_risks.append(get_vietnamese_finding_title(h))
            blocking_reasons.append(f"Thất bại tài chính: {get_vietnamese_finding_title(h)}")

    if warnings:
        for w in warnings:
            critical_risks.append(get_vietnamese_finding_title(w))

    if med_roe is not None and med_roe >= 0.15:
        supporting_evidence.append(f"ROE trung vị đạt {(med_roe*100):.1f}%")
    if pat_cagr is not None and pat_cagr >= 0.10:
        supporting_evidence.append(f"Tăng trưởng LNST CAGR đạt {(pat_cagr*100):.1f}%/năm")

    quality_gate_status = (
        "PASS"
        if not hard_failures
        and compounder_class
        in (
            CompounderClassification.COMPOUNDER.value,
            CompounderClassification.POTENTIAL_COMPOUNDER.value,
            CompounderClassification.CYCLICAL_QUALITY.value,
        )
        else ("WATCH" if warnings else "FAIL")
    )

    # Explicit rationale explaining why WATCH findings can coexist with BUY / CONDITIONAL_BUY
    watch_coexistence_rationale: Optional[str] = None
    if warnings:
        warn_titles = [get_vietnamese_finding_title(w) for w in warnings]
        if decision_state in ("BUY", "CONDITIONAL_BUY"):
            watch_coexistence_rationale = (
                f"Các phát hiện ở mức Theo dõi ({', '.join(warn_titles)}) là các tín hiệu phi cấu trúc / áp lực vốn lưu động hoặc biến động chu kỳ, không phải lỗi chặn mua (Hard Blocker). "
                f"Các yếu tố này đã được lượng hóa và bù đắp thông qua phụ phí Biên an toàn yêu cầu (Required MOS: {required_mos:.1f}%). "
                f"Do doanh nghiệp không có suy giảm cấu trúc, không có vi phạm kế toán nghiêm trọng và mức giá hiện tại (MOS {actual_mos:.1f}%) "
                f"đạt yêu cầu an toàn, khuyến nghị {get_vietnamese_decision(decision_state)} cùng tồn tại hợp lệ với các chỉ tiêu giám sát này."
            )
        elif decision_state == "WAIT_FOR_MOS":
            watch_coexistence_rationale = (
                f"Các cảnh báo Theo dõi ({', '.join(warn_titles)}) làm tăng phụ phí Biên an toàn yêu cầu lên {required_mos:.1f}%. "
                f"Mức giá hiện tại (MOS {actual_mos:.1f}%) chưa đủ bù đắp các rủi ro này."
            )

    decision_trace = {
        "decision": decision_state,
        "decision_vietnamese": get_vietnamese_decision(decision_state),
        "decision_authority": "MUNGER_BCTC_PIPELINE",
        "bctc_readiness": data_readiness,
        "quality_gate": quality_gate_status,
        "quality_gate_source": "BUSINESS_QUALITY_GATE",
        "quality_gate_vietnamese": get_vietnamese_status(quality_gate_status),
        "forensic_gate": forensics_status,
        "forensic_gate_source": "FORENSIC_GATE",
        "forensic_gate_vietnamese": get_vietnamese_status(forensics_status),
        "value_trap_gate": vt_status,
        "value_trap_gate_source": "VALUE_TRAP_GATE",
        "value_trap_gate_vietnamese": get_vietnamese_valuetrap(vt_status),
        "valuation_gate": val_status,
        "valuation_gate_source": "VALUATION_GATE",
        "mos_gate": mos_gate,
        "mos_gate_source": "MOS_GATE",
        "mos_gate_vietnamese": get_vietnamese_status(mos_gate),
        "primary_blocker_gate": primary_blocker_gate,
        "valuation_confidence": val_confidence,
        "blocking_reasons": blocking_reasons,
        "monitoring_reasons": monitoring_reasons,
        "supporting_evidence": supporting_evidence,
        "critical_risks": critical_risks,
        "watch_coexistence_rationale": watch_coexistence_rationale,
        "primary_reason": decision_reason,
    }

    long_term_decision = {
        "state": decision_state,
        "state_vietnamese": get_vietnamese_decision(decision_state),
        "decision_authority": "MUNGER_BCTC_PIPELINE",
        "primary_reason": decision_reason,
        "primary_blocker_gate": primary_blocker_gate,
        "actual_mos_pct": actual_mos,
        "required_mos_pct": required_mos,
        "mos_gate": mos_gate,
        "mos_gate_vietnamese": get_vietnamese_status(mos_gate),
        "bctc_only_pipeline": True,
        "qualitative_unknown_blocks_decision": False,
        "compounder_classification": compounder_class,
        "has_forensic_warnings": has_forensic_warnings,
        "valuation_confidence": val_confidence,
        "blocking_reasons": blocking_reasons,
        "monitoring_reasons": monitoring_reasons,
        "supporting_evidence": supporting_evidence,
        "watch_coexistence_rationale": watch_coexistence_rationale,
        "decision_trace": decision_trace,
    }

    # 12. Automated Investment Thesis Challenge Engine (Task 141)
    from .munger_thesis_challenge import run_thesis_challenge_analysis
    temp_payload = {
        "symbol": ticker,
        "archetype": archetype_str,
        "data_readiness": data_readiness,
        "all_findings": [f.to_dict() if hasattr(f, "to_dict") else f for f in all_findings],
        "hard_financial_failures": hard_failures,
        "financial_warnings": warnings,
        "value_trap_assessment": value_trap_assessment,
        "normalized_earning_power": normalized_earning_power,
        "overall_financial_quality": overall_quality,
        "long_term_decision": long_term_decision,
        "valuation": valuation_analysis,
        "profitability_analysis": prof_res.to_dict() if hasattr(prof_res, "to_dict") else prof_res,
        "debt_liquidity": debt_res.to_dict() if hasattr(debt_res, "to_dict") else debt_res,
        "compounder_classification": compounder_class,
    }
    thesis_challenge_obj = run_thesis_challenge_analysis(
        munger_analysis=temp_payload,
        valuation_data=valuation_analysis,
    )
    thesis_challenge_dict = thesis_challenge_obj.to_dict()

    # 13. Liquidity Gate Evaluation (Task 162, Task 173, Task 174)
    from .liquidity_evaluator import evaluate_symbol_liquidity, synthesize_munger_screening_conclusion_vi
    canonical_price_val = valuation_analysis.get("current_price")
    liquidity_info = evaluate_symbol_liquidity(ticker, canonical_price=canonical_price_val)

    # 14. Evidence-Based Final Conclusion
    evidence_conclusion = _build_evidence_based_conclusion(
        symbol=ticker,
        archetype=archetype_str,
        compounder_class=compounder_class,
        all_findings=all_findings,
        hard_failures=hard_failures,
        warnings=warnings,
        value_trap_assessment=value_trap_assessment,
        valuation=valuation_analysis,
        long_term_decision=long_term_decision,
        prof_res=prof_res,
        growth_res=growth_res,
        eq_res=eq_res,
        liquidity=liquidity_info,
    )

    return FinancialBusinessAnalysis(
        symbol=ticker,
        archetype=archetype_str,
        history_start=history_start,
        history_end=history_end,
        history_years=history_years,
        history_depth=history_depth,
        data_readiness=data_readiness,
        provider=effective_provider,
        growth_analysis=growth_res,
        profitability_analysis=prof_res,
        earnings_durability=dur_res,
        earnings_quality=eq_res,
        cash_flow_quality=eq_res,
        balance_sheet_strength=bs_res,
        debt_liquidity=debt_res,
        capital_efficiency=cap_eff_res,
        capital_allocation=cap_alloc_res,
        dilution_analysis=dilution_res,
        accounting_consistency=acct_res,
        financial_forensics=forensics_res,
        normalized_earning_power=normalized_earning_power,
        structural_deterioration=structural_dict,
        cyclical_analysis={"cyclical_rebound": False},
        value_trap_assessment=value_trap_assessment,
        valuation=valuation_analysis,
        long_term_decision=long_term_decision,
        thesis_challenge=thesis_challenge_dict,
        evidence_based_conclusion=evidence_conclusion,
        liquidity=liquidity_info,
        compounder_classification=compounder_class,
        overall_financial_quality=overall_quality,
        hard_financial_failures=hard_failures,
        financial_warnings=warnings,
        all_findings=all_findings,
    )


def _build_evidence_based_conclusion(
    symbol: str,
    archetype: str,
    compounder_class: str,
    all_findings: List[FinancialFinding],
    hard_failures: List[str],
    warnings: List[str],
    value_trap_assessment: Dict[str, Any],
    valuation: Dict[str, Any],
    long_term_decision: Dict[str, Any],
    prof_res: FinancialDimensionResult,
    growth_res: FinancialDimensionResult,
    eq_res: FinancialDimensionResult,
    liquidity: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Build structured evidence-based final conclusion payload."""
    from .vietnamese_presenter import (
        get_vietnamese_classification,
        get_vietnamese_decision,
        get_vietnamese_finding_title,
        get_vietnamese_status,
        get_vietnamese_valuetrap,
    )
    from .liquidity_evaluator import synthesize_munger_screening_conclusion_vi

    strengths: List[str] = []
    weaknesses: List[str] = []

    med_roe = prof_res.metrics.get("median_roe")
    if med_roe is not None and med_roe >= 0.15:
        strengths.append(f"Tỷ suất sinh lời ROE trung vị đạt mức cao ({(med_roe*100):.1f}%)")

    pat_cagr = growth_res.metrics.get("net_profit_cagr")
    if pat_cagr is not None and pat_cagr >= 0.12:
        strengths.append(f"Tăng trưởng lợi nhuận ròng mạnh mẽ ({(pat_cagr*100):.1f}%/năm)")

    avg_cfo_pat = eq_res.metrics.get("avg_cfo_pat") or eq_res.metrics.get("median_cfo_pat")
    if avg_cfo_pat is not None and avg_cfo_pat >= 0.8:
        strengths.append(f"Khả năng chuyển hóa lợi nhuận thành tiền mặt tương đối tốt (CFO/PAT trung vị {avg_cfo_pat:.2f}x)")

    if not hard_failures:
        strengths.append("Không phát hiện vi phạm hằng đẳng thức kế toán hay thất bại nghiêm trọng")

    if hard_failures:
        for f in hard_failures:
            weaknesses.append(f"Thất bại nghiêm trọng: {get_vietnamese_finding_title(f)}")

    if warnings:
        for w in warnings[:3]:
            weaknesses.append(f"Cảnh báo: {get_vietnamese_finding_title(w)}")

    conclusion_text = (
        f"Đánh giá tổng thể cho {symbol}: {get_vietnamese_classification(compounder_class)}. "
        f"Trạng thái bẫy giá trị: {get_vietnamese_valuetrap(value_trap_assessment.get('status', 'CLEAR'))}. "
        f"Quyết định khuyến nghị: {long_term_decision.get('state_vietnamese', 'Chờ biên an toàn')} — {long_term_decision.get('primary_reason', '')}"
    )

    str_list = strengths if strengths else ["Nền tảng tài chính duy trì ổn định"]
    weak_list = weaknesses if weaknesses else ["Chưa phát hiện điểm yếu BCTC nghiêm trọng"]
    primary_warn = weaknesses[0] if weaknesses else "Chưa phát hiện cảnh báo trọng yếu"
    act_mos = valuation.get("actual_mos_pct") if valuation else None
    req_mos = valuation.get("required_mos_pct") if valuation else None
    if act_mos is not None and req_mos is not None:
        val_mos_str = f"MOS: {float(act_mos):.1f}% vs Yêu cầu: {float(req_mos):.1f}%"
    else:
        val_mos_str = "Chưa có định giá chuẩn"

    liq_code = (liquidity or {}).get("classification", "LIQUIDITY_INSUFFICIENT_DATA")
    synthesis_conclusion = synthesize_munger_screening_conclusion_vi(
        quality_tier=valuation.get("quality_tier", "INVESTABLE"),
        compounder_class=compounder_class,
        mos=act_mos,
        req_mos=req_mos,
        vt_status=value_trap_assessment.get("status", "CLEAR"),
        liquidity_code=liq_code,
        hard_failures_count=len(hard_failures),
    )

    # Evidence-backed thesis break and thesis consolidation conditions
    break_conditions = []
    if archetype == "BANK":
        break_conditions.append("ROE ngân hàng suy giảm dưới 12.0% liên tiếp 2 năm hoặc nợ xấu vượt 3.0%")
    elif archetype == "SECURITIES":
        break_conditions.append("ROE công ty chứng khoán dưới 8.0% liên tiếp 2 năm hoặc đòn bẩy tài chính vượt 2.5x")
    else:
        if med_roe is not None and med_roe >= 0.15:
            break_conditions.append(f"ROE suy giảm dưới 12.0% (hiện tại trung vị {med_roe*100:.1f}%)")
        else:
            break_conditions.append("ROE suy giảm dưới 10.0% hoặc ROIC suy giảm dưới 8.0% kéo dài 2 năm")
        if avg_cfo_pat is not None and avg_cfo_pat >= 0.8:
            break_conditions.append("Tỷ lệ chuyển hóa CFO/PAT suy giảm dưới 0.6x kéo dài trên 2 năm")
        if warnings:
            break_conditions.append("Áp lực vốn lưu động/tồn kho chuyển hóa thành thất bại tài chính nghiêm trọng")
        break_conditions.append("Pha loãng cổ phiếu không đi kèm với tăng trưởng lợi nhuận ròng tương xứng")

    dieu_co_the_pha_vo = "; ".join(break_conditions[:3]) if break_conditions else "Biên an toàn suy giảm hoặc phát hiện bất thường dòng tiền BCTC"

    return {
        "symbol": symbol,
        "compounder_classification": compounder_class,
        "compounder_classification_vietnamese": get_vietnamese_classification(compounder_class),
        "decision_state": long_term_decision.get("state"),
        "decision_state_vietnamese": long_term_decision.get("state_vietnamese"),
        "primary_reason": long_term_decision.get("primary_reason"),
        "strengths": strengths,
        "weaknesses": weaknesses,
        "diem_manh_tai_chinh": str_list,
        "diem_yeu": weak_list,
        "diem_yeu_tai_chinh": weak_list,
        "warning_quan_trong_nhat": primary_warn,
        "xu_huong_dai_han": f"Phân loại: {get_vietnamese_classification(compounder_class)}",
        "value_trap_risk": get_vietnamese_valuetrap(value_trap_assessment.get("status", "CLEAR")),
        "liquidity_classification": (liquidity or {}).get("classification"),
        "liquidity_classification_vietnamese": (liquidity or {}).get("classification_vi"),
        "synthesis_conclusion_vietnamese": synthesis_conclusion,
        "dieu_co_the_pha_vo_thesis": dieu_co_the_pha_vo,
        "dieu_kien_cung_co_thesis": "Duy trì ROE và tăng trưởng lợi nhuận có dòng tiền bảo chứng",
        "valuation_mos": val_mos_str,
        "final_decision": long_term_decision.get("state_vietnamese", "Chờ biên an toàn"),
        "ket_luan_tong_the": conclusion_text,
        "khuyen_nghi": long_term_decision.get("state_vietnamese"),
        "summary_text": conclusion_text,
        "full_narrative": conclusion_text,
    }
