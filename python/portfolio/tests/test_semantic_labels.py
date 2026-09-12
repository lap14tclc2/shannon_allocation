"""Automated unit and regression tests for QPort Vietnamese Semantic Presentation Layer (Task 145)."""

import pytest
from portfolio.value_engine.vietnamese_presenter import (
    get_vietnamese_status,
    get_vietnamese_decision,
    get_vietnamese_classification,
    get_vietnamese_valuetrap,
    get_vietnamese_deterioration,
    get_vietnamese_archetype,
    get_vietnamese_finding_title,
    get_vietnamese_comparison,
    enrich_finding_dict,
    FINDING_TITLES,
    STATUS_VIETNAMESE,
    DECISION_VIETNAMESE,
    VALUETRAP_VIETNAMESE,
    DETERIORATION_VIETNAMESE,
)


def test_receivables_grow_faster_than_revenue_semantic_mapping():
    """Regression test: RECEIVABLES_GROW_FASTER_THAN_REVENUE must NEVER render raw machine string."""
    code = "RECEIVABLES_GROW_FASTER_THAN_REVENUE"
    title = get_vietnamese_finding_title(code)
    assert title == "Khoản phải thu tăng nhanh hơn doanh thu"
    assert title != code

    enriched = enrich_finding_dict({"code": code, "status": "FAIL", "metrics": {}})
    narrative = enriched.get("vietnamese_explanation", {})
    assert narrative.get("tieu_de") == "Khoản phải thu tăng nhanh hơn doanh thu"
    assert "RECEIVABLES_GROW_FASTER_THAN_REVENUE" not in narrative.get("tieu_de")


def test_profit_cash_divergence_semantic_mapping():
    """Regression test: PROFIT_CASH_DIVERGENCE must render Vietnamese semantic title."""
    code = "PROFIT_CASH_DIVERGENCE"
    title = get_vietnamese_finding_title(code)
    assert title == "Lợi nhuận tăng nhưng dòng tiền không theo kịp"
    assert title != code


def test_all_known_forensic_codes_mapped():
    """Ensure all forensic finding codes produced by engine have explicit Vietnamese titles."""
    known_codes = [
        "RECEIVABLES_GROW_FASTER_THAN_REVENUE",
        "PROFIT_CASH_DIVERGENCE",
        "WEAK_CASH_CONVERSION",
        "INVENTORY_BUILDUP",
        "INVENTORY_GROWTH_EXCEEDS_SALES",
        "INVENTORY_GROW_FASTER_THAN_REVENUE",
        "DEBT_FUNDED_LOW_QUALITY_GROWTH",
        "EXCESSIVE_DEBT_LEVERAGE",
        "UNSTABLE_EARNINGS_HISTORY",
        "WEAK_PROFITABILITY_ROE",
        "PER_SHARE_VALUE_DILUTION",
        "ACCOUNTING_IDENTITY_DISCREPANCY",
        "WEAK_BANK_ROE",
        "LOW_BANK_CAPITAL_ADEQUACY",
        "WEAK_SECURITIES_ROE",
        "TRADING_INCOME_DEPENDENCE",
        "SECURITIES_HIGH_LEVERAGE",
    ]
    for code in known_codes:
        assert code in FINDING_TITLES, f"Forensic code {code} missing from FINDING_TITLES dictionary!"
        title = get_vietnamese_finding_title(code)
        assert title != code, f"Forensic code {code} rendered raw string!"
        assert "_" not in title, f"Forensic code {code} rendered raw underscores!"


def test_unknown_enum_safe_fallback():
    """Unmapped enums must format safely without returning raw ALL_CAPS_SNAKE_CASE."""
    unknown_code = "FUTURE_NEW_FORENSIC_FLAG"
    formatted = get_vietnamese_finding_title(unknown_code)
    assert formatted != unknown_code
    assert "_" not in formatted
    assert formatted == "Future New Forensic Flag"

    unknown_status = "MYSTERY_STATUS"
    formatted_status = get_vietnamese_status(unknown_status)
    assert formatted_status == "mystery status"


def test_decision_codes_mapped():
    decisions = ["BUY", "BUY_MORE", "HOLD", "WAIT_FOR_MOS", "REVIEW_BUSINESS", "AVOID", "SELL"]
    for d in decisions:
        res = get_vietnamese_decision(d)
        assert res != d
        assert "_" not in res


def test_value_trap_codes_mapped():
    traps = ["CLEAR", "WATCH", "HIGH_RISK", "INSUFFICIENT_DATA", "UNPROTECTED"]
    for vt in traps:
        res = get_vietnamese_valuetrap(vt)
        assert res != vt
        assert "_" not in res
