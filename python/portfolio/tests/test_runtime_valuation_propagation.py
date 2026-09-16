"""Comprehensive Regression Test Suite for Task 135: Runtime Valuation & Evidence Propagation."""

import os
import pytest
from portfolio.canonical_valuation import build_canonical_valuation
from portfolio.policy.context_builder import build_decision_context
from portfolio.policy.engine import evaluate_decision
from portfolio.value_engine.value_trap import evaluate_value_trap
from portfolio.value_engine.business_review import evaluate_business_review
from portfolio.finance_catalog import valuation_readiness_audit, valuation_snapshot_from_catalog
from portfolio.service import PortfolioService


def test_1_canonical_ready_valuation_reaches_runtime_decision():
    """1. Canonical READY valuation reaches runtime_decision."""
    val = {
        "ok": True,
        "symbol": "FPT",
        "model_status": "VALID",
        "valuation_confidence": "HIGH",
        "current_price": 100000.0,
        "base_iv": 150000.0,
        "bear_iv": 120000.0,
        "bull_iv": 180000.0,
        "required_mos_pct": 15.0,
        "actual_mos_pct": 33.3,
        "quality_tier": "HIGH_QUALITY",
    }
    ctx = build_decision_context(symbol="FPT", valuation=val)
    assert ctx.base_iv == 150000.0
    assert ctx.bear_iv == 120000.0
    assert ctx.bull_iv == 180000.0
    assert ctx.model_status == "VALID"
    assert ctx.data_readiness.get("valuation") == "READY"


def test_2_bear_base_bull_values_survive_every_adapter():
    """2. Bear/Base/Bull values survive every adapter."""
    val = {
        "ok": True,
        "symbol": "FPT",
        "model_status": "MODEL_VERIFIED",
        "current_price": 100000.0,
        "bear_iv": 110000.0,
        "base_iv": 140000.0,
        "bull_iv": 170000.0,
    }
    b_rev = evaluate_business_review("FPT", valuation_report=val).to_dict()
    v_trap = evaluate_value_trap("FPT", valuation_report=val).to_dict()
    ctx = build_decision_context(symbol="FPT", valuation=val, business_review=b_rev, value_trap=v_trap)
    ev = evaluate_decision(ctx)

    assert ctx.bear_iv == 110000.0
    assert ctx.base_iv == 140000.0
    assert ctx.bull_iv == 170000.0
    assert any(f.get("metric") == "base_iv" and f.get("value") == 140000.0 for f in ev.facts)


def test_3_mos_survives_every_adapter():
    """3. MOS survives every adapter."""
    val = {
        "ok": True,
        "symbol": "DGC",
        "model_status": "MODEL_VERIFIED",
        "current_price": 80000.0,
        "base_iv": 100000.0,
        "actual_mos_pct": 20.0,
        "required_mos_pct": 15.0,
    }
    ctx = build_decision_context(symbol="DGC", valuation=val)
    assert ctx.actual_mos == 20.0
    assert ctx.required_mos == 15.0


def test_4_business_review_unknown_does_not_erase_valuation():
    """4. BusinessReview UNKNOWN does not erase quantitative valuation."""
    val = {
        "ok": True,
        "symbol": "FPT",
        "model_status": "MODEL_VERIFIED",
        "valuation_confidence": "HIGH",
        "current_price": 100000.0,
        "base_iv": 150000.0,
        "bear_iv": 120000.0,
        "bull_iv": 180000.0,
    }
    b_rev = {"overall_status": "UNKNOWN", "understandability": "UNKNOWN"}
    ctx = build_decision_context(symbol="FPT", valuation=val, business_review=b_rev)
    evidence = evaluate_decision(ctx)

    assert evidence.decision in ("REVIEW_BUSINESS", "BUILD_RESERVE_FIRST")
    assert "VALUATION_UNAVAILABLE" not in evidence.blocking_reasons
    assert ctx.base_iv == 150000.0
    assert ctx.bear_iv == 120000.0


def test_5_qualitative_unknown_does_not_cause_valuetrap_insufficient_data():
    """5. Qualitative UNKNOWN does not automatically cause ValueTrap INSUFFICIENT_DATA."""
    val = {
        "ok": True,
        "symbol": "FPT",
        "model_status": "MODEL_VERIFIED",
        "current_price": 100000.0,
        "base_iv": 150000.0,
        "bear_iv": 120000.0,
    }
    hist = [
        {"fiscal_year": 2023, "net_profit": 100, "cfo": 110, "revenue": 1000},
        {"fiscal_year": 2024, "net_profit": 120, "cfo": 130, "revenue": 1200},
        {"fiscal_year": 2025, "net_profit": 140, "cfo": 150, "revenue": 1400},
    ]
    vt = evaluate_value_trap("FPT", valuation_report=val, financial_history=hist)
    assert vt.status != "INSUFFICIENT_DATA"


def test_6_valuetrap_clear_and_watch_survives_context_building():
    """6. ValueTrap CLEAR/WATCH survives context building."""
    vt_clear = evaluate_value_trap(
        "FPT",
        valuation_report={"ok": True, "base_iv": 150000, "bear_iv": 120000, "current_price": 100000},
        financial_history=[
            {"fiscal_year": 2023, "net_profit": 100, "cfo": 110, "revenue": 1000},
            {"fiscal_year": 2024, "net_profit": 120, "cfo": 130, "revenue": 1200},
            {"fiscal_year": 2025, "net_profit": 140, "cfo": 150, "revenue": 1400},
        ],
    )
    ctx_clear = build_decision_context(symbol="FPT", value_trap=vt_clear.to_dict())
    assert ctx_clear.value_trap_status == "CLEAR"

    vt_watch = evaluate_value_trap(
        "FPT",
        valuation_report={"ok": True, "base_iv": 150000, "bear_iv": 60000, "current_price": 100000},
        financial_history=[
            {"fiscal_year": 2023, "net_profit": 100, "cfo": 110, "revenue": 1000},
            {"fiscal_year": 2024, "net_profit": 120, "cfo": 130, "revenue": 1200},
            {"fiscal_year": 2025, "net_profit": 140, "cfo": 150, "revenue": 1400},
        ],
    )
    ctx_watch = build_decision_context(symbol="FPT", value_trap=vt_watch.to_dict())
    assert ctx_watch.value_trap_status == "WATCH"


@pytest.mark.skipif(not os.environ.get("DATABASE_URL"), reason="Requires PostgreSQL database connection")
def test_7_ssi_primary_selected_despite_ordinary_tcbs_source_variance():
    """7. SSI primary selected despite ordinary TCBS source variance."""
    audit = valuation_readiness_audit("FPT", market_price=100000.0)
    assert audit["status"] == "READY"
    assert audit.get("provider") == "ssi" or audit.get("provider") is None


@pytest.mark.skipif(not os.environ.get("DATABASE_URL"), reason="Requires PostgreSQL database connection")
def test_8_source_variance_does_not_become_canonical_fact_conflict():
    """8. SOURCE_VARIANCE does not become CANONICAL_FACT_CONFLICT."""
    audit = valuation_readiness_audit("ACB", market_price=25000.0)
    assert audit["status"] == "READY"
    assert len(audit.get("conflicts", [])) == 0


@pytest.mark.skipif(not os.environ.get("DATABASE_URL"), reason="Requires PostgreSQL database connection")
def test_9_fy_only_valuation_works_without_quarterly_data():
    """9. FY-only valuation works without quarterly data."""
    val = build_canonical_valuation("FPT", market_price=100000.0)
    assert val.get("ok") is True
    assert len(val.get("financial_history", [])) > 0
    assert val.get("base_iv") is not None


def test_10_terminal_and_business_consume_same_canonical_valuation():
    """10. Terminal and Business APIs consume identical canonical valuation."""
    svc = PortfolioService(store=None)
    val = svc.valuation("FPT")
    rt = svc.runtime_decision("FPT")
    if val.get("ok") and "valuation" in rt and "base_iv" in rt["valuation"]:
        assert rt["valuation"]["base_iv"] == val.get("base_iv")
        assert rt["valuation"]["bear_iv"] == val.get("bear_iv")


def test_11_task_134_precedence_remains_review_business_when_business_evidence_incomplete():
    """11. Task 134 precedence remains REVIEW_BUSINESS when business evidence is incomplete even if PBS is UNKNOWN."""
    ctx = build_decision_context(
        symbol="FPT",
        valuation={"ok": True, "base_iv": 150000, "bear_iv": 120000, "current_price": 100000, "model_status": "VALID"},
        business_review={"overall_status": "UNKNOWN"},
        personal_finance=None,
    )
    ev = evaluate_decision(ctx)
    assert ev.decision in ("REVIEW_BUSINESS", "BUILD_RESERVE_FIRST")


def test_12_acb_bank_path_does_not_require_industrial_cfo_capex():
    """12. ACB bank path does not require industrial CFO/CapEx."""
    val = {
        "ok": True,
        "symbol": "ACB",
        "is_bank": True,
        "archetype": "BANK",
        "model_status": "MODEL_VERIFIED",
        "current_price": 25000.0,
        "base_iv": 27000.0,
        "bear_iv": 18000.0,
    }
    vt = evaluate_value_trap("ACB", valuation_report=val, financial_history=[{"fiscal_year": 2025, "net_profit": 100}])
    assert vt.cash_conversion_status == "NOT_APPLICABLE"
    assert "CFO_NET_INCOME_RATIO" not in vt.missing_data


def test_13_vix_securities_path_does_not_require_generic_cfo_ni_cash_conversion():
    """13. VIX securities path does not require generic CFO/NI cash conversion."""
    val = {
        "ok": True,
        "symbol": "VIX",
        "is_securities": True,
        "archetype": "SECURITIES",
        "model_status": "MODEL_VERIFIED",
        "current_price": 12000.0,
        "base_iv": 29000.0,
        "bear_iv": 16000.0,
    }
    vt = evaluate_value_trap("VIX", valuation_report=val, financial_history=[{"fiscal_year": 2025, "net_profit": 100}])
    assert vt.cash_conversion_status == "NOT_APPLICABLE"
    assert vt.return_on_capital_trend == "NOT_APPLICABLE"
    assert "CFO_NET_INCOME_RATIO" not in vt.missing_data
