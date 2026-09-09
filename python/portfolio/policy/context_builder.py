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
        ctx.required_mos = valuation.get("required_mos") or valuation.get("required_mos_pct")
        ctx.actual_mos = valuation.get("actual_mos") or valuation.get("actual_mos_pct")
        ctx.valuation_confidence = valuation.get("valuation_confidence") or "UNKNOWN"
        ctx.model_status = valuation.get("model_status") or valuation.get("status") or "INVALID"
        ctx.quality_score = valuation.get("quality_score")
        ctx.quality_tier = valuation.get("quality_tier")

        if valuation.get("hard_rejects"):
            hard_rejects.extend(valuation["hard_rejects"])
    else:
        missing_fields.append("VALUATION_REPORT")
        ctx.model_status = "INVALID"
        ctx.valuation_confidence = "UNKNOWN"

    # 3. Business Review Integration
    if business_review:
        ctx.circle_of_competence = business_review.get("circle_of_competence", "UNKNOWN")
        ctx.accounting_reliability = business_review.get("accounting_reliability", "UNKNOWN")
        ctx.financial_strength = business_review.get("financial_strength", "UNKNOWN")
        ctx.earnings_durability = business_review.get("earnings_durability", "UNKNOWN")
        ctx.capital_allocation_quality = business_review.get("capital_allocation_quality", "UNKNOWN")
        ctx.moat_assessment = business_review.get("moat_assessment", "UNKNOWN")
        ctx.business_review_status = business_review.get("status", "UNKNOWN")
    else:
        missing_fields.append("BUSINESS_REVIEW")
        ctx.business_review_status = "UNKNOWN"

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

    ctx.data_readiness = {
        "financial_core": "READY" if valuation else "BLOCKED",
        "valuation": "READY" if ctx.model_status in ("VALID", "VERIFIED", "MODEL_VERIFIED") else "PARTIAL" if valuation else "BLOCKED",
        "business_review": "READY" if (business_review and ctx.business_review_status in ("BUSINESS_PASS", "PASS", "BUSINESS_FAIL", "FAIL")) else "PARTIAL" if business_review else "BLOCKED",
        "earnings_quality": "READY" if eq_status in ("CONFIRMED", "PASS", "GOOD") else "PARTIAL" if eq_status == "PARTIAL" else "BLOCKED",
        "value_trap": "READY" if value_trap and ctx.value_trap_status in ("CLEAR", "WATCH", "HIGH_RISK") else "PARTIAL" if value_trap else "BLOCKED",
        "personal_finance": "READY" if (personal_finance and ctx.survival_reserve_status in ("SAFE", "ATTENTION", "UNSAFE")) else "BLOCKED",
        "archetype_specific": arch_status,
    }

    return ctx
