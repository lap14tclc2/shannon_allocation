"""Builder service for constructing InvestmentDecisionContext instances."""

from __future__ import annotations

from typing import Any
from portfolio.policy.models import InvestmentDecisionContext


def build_decision_context(
    symbol: str,
    holding: dict[str, Any] | None = None,
    valuation: dict[str, Any] | None = None,
    personal_finance: dict[str, Any] | None = None,
    business_review: dict[str, Any] | None = None,
    value_trap: dict[str, Any] | None = None,
    qualitative_evidence: list[dict[str, Any]] | None = None,
    munger_checklist: dict[str, Any] | None = None,
) -> InvestmentDecisionContext:
    """Build a unified InvestmentDecisionContext from component domain reports."""
    symbol_clean = symbol.strip().upper()
    ctx = InvestmentDecisionContext(symbol=symbol_clean)

    missing_fields: list[str] = []
    warnings: list[str] = []
    hard_rejects: list[str] = []

    # 1. Holding Details
    if holding:
        ctx.current_weight = float(holding.get("weight") or 0.0)
        ctx.current_market_value = float(holding.get("market_value") or 0.0)
        ctx.cost_basis = holding.get("cost_basis")
        ctx.shares_held = float(holding.get("quantity") or 0.0)
    else:
        ctx.current_weight = 0.0
        ctx.current_market_value = 0.0
        ctx.cost_basis = None
        ctx.shares_held = 0.0

    # 2. Valuation Report Integration
    if valuation:
        ctx.current_price = float(valuation.get("current_price") or valuation.get("price") or 0.0)
        ctx.bear_iv = valuation.get("bear_iv") or valuation.get("bear_case_iv")
        ctx.base_iv = valuation.get("base_iv") or valuation.get("intrinsic_value")
        ctx.bull_iv = valuation.get("bull_iv") or valuation.get("bull_case_iv")
        req_m = valuation.get("required_mos_pct") if valuation.get("required_mos_pct") is not None else valuation.get("required_mos")
        ctx.required_mos = float(req_m) if req_m is not None else None
        act_m = valuation.get("actual_mos_pct") if valuation.get("actual_mos_pct") is not None else valuation.get("actual_mos")
        ctx.actual_mos = float(act_m) if act_m is not None else None
        ctx.valuation_confidence = valuation.get("valuation_confidence") or "UNKNOWN"
        ctx.model_status = valuation.get("model_status") or valuation.get("status") or "INVALID"
        ctx.quality_score = valuation.get("quality_score")
        ctx.quality_tier = valuation.get("quality_tier")

        cf_qual = valuation.get("cash_flow_quality")
        if cf_qual in ("HIGH_QUALITY", "GOOD", "PASS"):
            ctx.accounting_numeric_quality = "PASS"
        elif cf_qual in ("LOW_QUALITY", "POOR", "FAIL"):
            ctx.accounting_numeric_quality = "FAIL"

        if valuation.get("hard_rejects"):
            hard_rejects.extend(valuation["hard_rejects"])
    else:
        missing_fields.append("VALUATION_REPORT")
        ctx.model_status = "INVALID"
        ctx.valuation_confidence = "UNKNOWN"

    # 3. Business Review & Qualitative Integration
    if business_review:
        ctx.circle_of_competence = (
            business_review.get("understandability")
            or business_review.get("circle_of_competence", "UNKNOWN")
        )
        ctx.financial_strength = business_review.get("financial_strength", "UNKNOWN")
        ctx.earnings_durability = business_review.get("earnings_durability", "UNKNOWN")

        # Accounting Reliability Split
        ctx.accounting_numeric_quality = business_review.get("accounting_numeric_quality") if business_review else ctx.accounting_numeric_quality
        ctx.accounting_qualitative_reliability = business_review.get("accounting_qualitative_reliability", "UNKNOWN") if business_review else ctx.accounting_qualitative_reliability

        if ctx.accounting_qualitative_reliability == "FAIL" or ctx.accounting_numeric_quality == "FAIL":
            ctx.accounting_reliability = "FAIL"
        elif ctx.accounting_numeric_quality == "PASS" and ctx.accounting_qualitative_reliability == "UNKNOWN":
            ctx.accounting_reliability = "WATCH"
        elif ctx.accounting_numeric_quality == "PASS" and ctx.accounting_qualitative_reliability == "PASS":
            ctx.accounting_reliability = "PASS"
        else:
            ctx.accounting_reliability = "UNKNOWN"

        # Management & Capital Allocation Split
        ctx.numeric_capital_allocation = (
            business_review.get("numeric_capital_allocation")
            or business_review.get("capital_allocation_quality")
            or business_review.get("management_capital_allocation")
            or "UNKNOWN"
        )
        ctx.management_integrity = business_review.get("management_integrity", "UNKNOWN")

        # Moat & Falsification
        ctx.moat_assessment = (
            business_review.get("moat")
            or business_review.get("moat_assessment", "UNKNOWN")
        )
        ctx.moat_types = business_review.get("moat_types", [])
        ctx.moat_supporting_evidence = business_review.get("moat_supporting_evidence", [])
        ctx.moat_counter_evidence = business_review.get("moat_counter_evidence", [])

        ctx.business_review_status = (
            business_review.get("overall_status")
            or business_review.get("status", "UNKNOWN")
        )
    else:
        missing_fields.append("BUSINESS_REVIEW")
        ctx.business_review_status = "UNKNOWN"

    if qualitative_evidence:
        ctx.qualitative_evidence_items = qualitative_evidence
        for item in qualitative_evidence:
            dim = item.get("dimension")
            st = item.get("status")
            if dim == "MOAT":
                ctx.moat_assessment = st
                if item.get("supporting_evidence"):
                    ctx.moat_supporting_evidence.extend(item["supporting_evidence"])
                if item.get("counter_evidence"):
                    ctx.moat_counter_evidence.extend(item["counter_evidence"])
            elif dim == "MANAGEMENT_CAPITAL_ALLOCATION":
                ctx.management_integrity = st
            elif dim == "ACCOUNTING_RELIABILITY_QUALITATIVE":
                ctx.accounting_qualitative_reliability = st
                if st == "FAIL":
                    ctx.accounting_reliability = "FAIL"
                    hard_rejects.append("ACCOUNTING_UNRELIABLE")
            elif dim == "CIRCLE_OF_COMPETENCE":
                ctx.circle_of_competence = st

    # Compute Accounting Reliability Aggregate
    if ctx.accounting_qualitative_reliability == "FAIL" or ctx.accounting_numeric_quality == "FAIL":
        ctx.accounting_reliability = "FAIL"
    elif (business_review and business_review.get("accounting_reliability") == "PASS") or (ctx.accounting_numeric_quality == "PASS" and ctx.accounting_qualitative_reliability == "PASS"):
        ctx.accounting_reliability = "PASS"
    elif ctx.accounting_numeric_quality == "PASS" and ctx.accounting_qualitative_reliability == "UNKNOWN":
        ctx.accounting_reliability = "WATCH"
    else:
        ctx.accounting_reliability = "UNKNOWN"

    # Compute Capital Allocation Quality Aggregate
    if ctx.management_integrity == "FAIL":
        ctx.capital_allocation_quality = "FAIL"
    elif ctx.numeric_capital_allocation == "PASS" or ctx.management_integrity == "PASS":
        ctx.capital_allocation_quality = "PASS"
    else:
        ctx.capital_allocation_quality = ctx.numeric_capital_allocation if ctx.management_integrity == "UNKNOWN" else ctx.management_integrity

    if munger_checklist:
        q_objs = munger_checklist.get("questions", [])
        concerns = [q.get("notes") for q in q_objs if q.get("status") == "CONCERN" and q.get("notes")]
        unanswered = [q for q in q_objs if q.get("status") == "UNANSWERED"]
        ctx.munger_checklist_concerns = concerns
        ctx.munger_checklist_status = "CONCERN" if concerns else ("ANSWERED" if not unanswered else "UNANSWERED")

    # 4. Value Trap Gate Integration
    if value_trap:
        ctx.value_trap_status = value_trap.get("status", "INSUFFICIENT_DATA")
        if value_trap.get("flags"):
            warnings.extend(value_trap["flags"])
    else:
        missing_fields.append("VALUE_TRAP_ASSESSMENT")
        ctx.value_trap_status = "INSUFFICIENT_DATA"

    # 5. Personal Balance Sheet Integration
    if personal_finance:
        ctx.survival_reserve_status = personal_finance.get("survival_reserve_status", "UNKNOWN")
        ctx.available_long_term_capital = float(personal_finance.get("available_long_term_capital") or 0.0)
        ctx.near_term_liability_status = personal_finance.get("near_term_liability_status", "UNKNOWN")
    else:
        missing_fields.append("PERSONAL_FINANCE")
        ctx.survival_reserve_status = "UNKNOWN"
        ctx.available_long_term_capital = 0.0
        ctx.near_term_liability_status = "UNKNOWN"

    # Deduplicate lists
    ctx.hard_rejects = list(dict.fromkeys(hard_rejects))
    ctx.missing_data = list(dict.fromkeys(missing_fields))
    ctx.warnings = list(dict.fromkeys(warnings))

    eq_status = value_trap.get("earnings_quality", "UNKNOWN") if value_trap else "UNKNOWN"
    arch_status = valuation.get("archetype_readiness", "NOT_APPLICABLE") if valuation else "NOT_APPLICABLE"

    val_data_status = (
        valuation.get("data_status")
        or valuation.get("model_status")
        or valuation.get("status")
        if valuation else None
    )

    if not valuation or val_data_status in ("CONFLICTED", "INSUFFICIENT", "BLOCKED", "INVALID"):
        fin_readiness = "BLOCKED"
        val_readiness = "BLOCKED"
    elif ctx.model_status in ("VALID", "VERIFIED", "MODEL_VERIFIED") and val_data_status in ("READY", "VALID", "VERIFIED", "MODEL_VERIFIED", None):
        fin_readiness = "READY"
        val_readiness = "READY"
    elif ctx.model_status in ("MODEL_PARTIAL", "FALLBACK", "PARTIAL"):
        fin_readiness = "PARTIAL"
        val_readiness = "PARTIAL"
    else:
        fin_readiness = "PARTIAL" if valuation else "BLOCKED"
        val_readiness = "PARTIAL" if valuation else "BLOCKED"

    pf_readiness = (
        "READY"
        if (personal_finance and ctx.survival_reserve_status in ("SAFE", "ATTENTION", "UNSAFE"))
        else "BLOCKED"
    )

    ctx.data_readiness = {
        "financial_core": fin_readiness,
        "valuation": val_readiness,
        "business_review": "READY" if (business_review and ctx.business_review_status in ("BUSINESS_PASS", "PASS", "BUSINESS_FAIL", "FAIL")) else "PARTIAL" if business_review else "BLOCKED",
        "earnings_quality": "READY" if eq_status in ("CONFIRMED", "PASS", "GOOD") else "PARTIAL" if eq_status == "PARTIAL" else "BLOCKED",
        "value_trap": "READY" if value_trap and ctx.value_trap_status in ("CLEAR", "WATCH", "HIGH_RISK") else "PARTIAL" if value_trap else "BLOCKED",
        "personal_finance": pf_readiness,
        "archetype_specific": arch_status,
    }

    return ctx
