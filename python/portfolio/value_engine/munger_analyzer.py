"""High-Level Munger Financial Statement Analysis Orchestrator (Task 136).

Orchestrates full evidence-driven long-term financial analysis across 12 dimensions
and returns a canonical FinancialBusinessAnalysis payload.
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
                    "valuation_confidence": val_res.get("valuation_confidence", "MEDIUM"),
                    "quality_tier": val_res.get("quality_tier"),
                }
        except Exception:
            valuation_data = None

    # 1. Build Multi-Year History
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

    # Data Readiness
    data_readiness = "READY" if history_years >= 5 else ("PARTIAL" if history_years >= 3 else "INSUFFICIENT")

    # 3. Forensics & Accounting Consistency
    acct_res = run_accounting_consistency_checks(history_data, thresholds)
    eq_res = run_earnings_quality_forensics(history_data, archetype_str, thresholds)
    rec_res = run_receivables_forensics(history_data, archetype_str, thresholds)
    inv_res = run_inventory_forensics(history_data, archetype_str, thresholds)

    # Combined Forensics Result
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

    # 4. Archetype Specific Analyzers
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

    # 5. Normalized Earning Power
    by_year = history_data.get("by_year", {})
    pat_series = [by_year[y].get("net_profit") for y in years if by_year[y].get("net_profit") is not None]
    reported_latest = pat_series[-1] if pat_series else None
    
    norm_5y = sum(pat_series[-5:]) / min(5, len(pat_series)) if pat_series else None
    norm_10y = sum(pat_series[-10:]) / min(10, len(pat_series)) if len(pat_series) >= 5 else norm_5y

    normalized_earning_power = {
        "reported_latest": reported_latest,
        "normalized_5y": norm_5y,
        "normalized_10y": norm_10y,
        "earning_power_divergence": (reported_latest - norm_5y) if reported_latest is not None and norm_5y is not None else None,
        "explanation": f"Lợi nhuận chuẩn hóa 5 năm đạt {norm_5y:,.0f} VND so với gần nhất {reported_latest:,.0f} VND." if norm_5y and reported_latest else "Chưa đủ dữ liệu lợi nhuận chuẩn hóa.",
    }

    # 6. Structural vs Cyclical Deterioration
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

    hard_failures = [f.code for f in all_findings if f.severity in (FindingSeverity.CRITICAL.value, FindingSeverity.HIGH.value)]
    warnings = [f.code for f in all_findings if f.severity in (FindingSeverity.MEDIUM.value, FindingSeverity.LOW.value)]

    # 8. Compounder Classification
    med_roe = prof_metrics.get("median_roe")
    pat_cagr = growth_metrics.get("net_profit_cagr")
    eps_cagr = growth_metrics.get("eps_cagr")
    structural_class = structural_dict.get("classification")

    if data_readiness == "INSUFFICIENT":
        compounder_class = CompounderClassification.INSUFFICIENT_DATA.value
    elif structural_class in (DeteriorationClassification.STRUCTURAL.value, DeteriorationClassification.POSSIBLY_STRUCTURAL.value):
        compounder_class = CompounderClassification.DETERIORATING_BUSINESS.value
    elif med_roe is not None and med_roe >= thresholds.ROE_PASS and pat_cagr is not None and pat_cagr >= 0.12 and not hard_failures:
        if eps_cagr is not None and eps_cagr >= 0.10:
            compounder_class = CompounderClassification.COMPOUNDER.value
        else:
            compounder_class = CompounderClassification.POTENTIAL_COMPOUNDER.value
    elif med_roe is not None and med_roe >= thresholds.ROE_WATCH:
        compounder_class = CompounderClassification.AVERAGE_BUSINESS.value
    else:
        compounder_class = CompounderClassification.WEAK_BUSINESS.value

    # 9. Value Trap Assessment (Refactored to consume Munger analysis)
    vt_status = "CLEAR"
    if hard_failures or structural_class == DeteriorationClassification.STRUCTURAL.value:
        vt_status = "HIGH_RISK"
    elif warnings or structural_class in (DeteriorationClassification.POSSIBLY_STRUCTURAL.value, DeteriorationClassification.POSSIBLY_CYCLICAL.value):
        vt_status = "WATCH"

    value_trap_assessment = {
        "status": vt_status,
        "deterioration_classification": structural_class,
        "hard_failures": hard_failures,
        "warnings": warnings,
        "explanation": f"Đánh giá Bẫy giá trị: {vt_status}. Trạng thái cấu trúc: {structural_class}.",
    }

    # 10. Canonical Valuation & Deterministic Required MOS Integration
    val_payload = valuation_data or {}
    val_status = val_payload.get("status", "INCOMPLETE")
    curr_price = val_payload.get("current_price")
    bear_iv = val_payload.get("bear_iv")
    base_iv = val_payload.get("base_iv")
    bull_iv = val_payload.get("bull_iv")
    actual_mos = val_payload.get("actual_mos_pct")
    val_confidence = val_payload.get("valuation_confidence", "MEDIUM")

    # Consume canonical required MOS authority from valuation engine payload
    canonical_req_mos = val_payload.get("required_mos_pct")
    if canonical_req_mos is not None:
        required_mos = float(canonical_req_mos)
    else:
        # Dynamic fallback if valuation engine payload was not provided
        base_req_mos = thresholds.BASE_REQUIRED_MOS_AVERAGE
        if compounder_class == CompounderClassification.COMPOUNDER.value:
            base_req_mos = thresholds.BASE_REQUIRED_MOS_COMPOUNDER
        elif compounder_class == CompounderClassification.POTENTIAL_COMPOUNDER.value:
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

    # 11. Core Deterministic BCTC-Only Decision (NO DEFAULT BUY!)
    decision_state = "WAIT_FOR_MOS"
    decision_reason = ""

    if hard_failures or vt_status == "HIGH_RISK" or compounder_class == CompounderClassification.DETERIORATING_BUSINESS.value or structural_class in (DeteriorationClassification.STRUCTURAL.value, DeteriorationClassification.POSSIBLY_STRUCTURAL.value):
        decision_state = "AVOID"
        fail_reasons = hard_failures if hard_failures else ([f"Bẫy giá trị rủi ro cao ({vt_status})"] if vt_status == "HIGH_RISK" else [f"Doanh nghiệp suy giảm cấu trúc ({structural_class})"])
        decision_reason = f"Phát hiện rủi ro tài chính nghiêm trọng ({', '.join(fail_reasons)})."
    elif data_readiness == "INSUFFICIENT":
        decision_state = "REVIEW_BUSINESS"
        decision_reason = "Chưa đủ dữ liệu tài chính lịch sử (dưới 3-5 năm) để hoàn thành đánh giá BCTC."
    elif (
        data_readiness in ("READY", "PARTIAL")
        and not hard_failures
        and vt_status != "HIGH_RISK"
        and compounder_class not in (CompounderClassification.DETERIORATING_BUSINESS.value, CompounderClassification.INSUFFICIENT_DATA.value, CompounderClassification.WEAK_BUSINESS.value)
        and val_status == "READY"
        and actual_mos is not None
        and mos_gate == "PASS"
    ):
        decision_state = "BUY"
        decision_reason = f"Doanh nghiệp đạt chuẩn chất lượng BCTC và mức giá hiện tại (MOS {actual_mos:.1f}%) đạt/vượt Biên an toàn yêu cầu ({required_mos:.1f}%)."
    else:
        decision_state = "WAIT_FOR_MOS"
        if compounder_class == CompounderClassification.WEAK_BUSINESS.value:
            decision_reason = "Doanh nghiệp có chất lượng tài chính yếu, không đạt tiêu chí mua dài hạn."
        elif val_status != "READY" or actual_mos is None:
            decision_reason = "Doanh nghiệp chất lượng ổn định nhưng chưa có định giá chuẩn để xác định Biên an toàn."
        elif mos_gate == "FAIL":
            decision_reason = f"Doanh nghiệp có chất lượng tốt ({compounder_class}) nhưng mức giá hiện tại (MOS {actual_mos:.1f}%) chưa đạt Biên an toàn yêu cầu ({required_mos:.1f}%)."
        else:
            decision_reason = "Doanh nghiệp ở trạng thái theo dõi, chờ mức giá có Biên an toàn phù hợp."

    from .vietnamese_presenter import get_vietnamese_decision, get_vietnamese_status

    long_term_decision = {
        "state": decision_state,
        "state_vietnamese": get_vietnamese_decision(decision_state),
        "primary_reason": decision_reason,
        "actual_mos_pct": actual_mos,
        "required_mos_pct": required_mos,
        "mos_gate": mos_gate,
        "mos_gate_vietnamese": get_vietnamese_status(mos_gate),
        "bctc_only_pipeline": True,
        "qualitative_unknown_blocks_decision": False,
        "compounder_classification": compounder_class,
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
        compounder_classification=compounder_class,
        overall_financial_quality=overall_quality,
        hard_financial_failures=hard_failures,
        financial_warnings=warnings,
        all_findings=all_findings,
    )

