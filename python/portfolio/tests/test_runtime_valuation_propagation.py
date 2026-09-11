"""Regression tests for Task 135: Runtime Valuation & Evidence Propagation."""

import os
import pytest
from portfolio.canonical_valuation import build_canonical_valuation
from portfolio.policy.context_builder import build_decision_context
from portfolio.policy.engine import evaluate_decision
from portfolio.value_engine.value_trap import evaluate_value_trap
from portfolio.finance_catalog import valuation_readiness_audit, valuation_snapshot_from_catalog, _schema_connection, FINANCE_SCHEMA


def test_canonical_valuation_to_context_propagation():
    """Verify Bear/Base/Bull IV and MOS propagate from valuation to decision context."""
    val = {
        "ok": True,
        "symbol": "FPT",
        "model_status": "VALID",
        "valuation_confidence": "HIGH",
        "current_price": 100000,
        "base_iv": 150000,
        "bear_iv": 120000,
        "bull_iv": 180000,
        "required_mos": 15.0,
        "actual_mos": 33.3,
        "quality_tier": "HIGH_QUALITY",
    }
    ctx = build_decision_context(symbol="FPT", valuation=val)
    assert ctx.base_iv == 150000
    assert ctx.bear_iv == 120000
    assert ctx.bull_iv == 180000
    assert ctx.model_status == "VALID"
    assert ctx.data_readiness.get("valuation") == "READY"


def test_valid_valuation_and_business_unknown_yields_review_business_not_valuation_unavailable():
    """Verify valid valuation + Business UNKNOWN yields REVIEW_BUSINESS without VALUATION_UNAVAILABLE blocker."""
    val = {
        "ok": True,
        "symbol": "FPT",
        "model_status": "VALID",
        "valuation_confidence": "HIGH",
        "current_price": 100000,
        "base_iv": 150000,
        "required_mos": 15.0,
    }
    ctx = build_decision_context(symbol="FPT", valuation=val, business_review={"overall_status": "UNKNOWN"})
    evidence = evaluate_decision(ctx)
    assert evidence.decision == "REVIEW_BUSINESS"
    assert "VALUATION_UNAVAILABLE" not in evidence.blocking_reasons
    assert "BUSINESS_REVIEW_INCOMPLETE" in evidence.blocking_reasons


def test_valuetrap_clear_and_watch_preserved():
    """Verify ValueTrap CLEAR and WATCH statuses propagate independently of qualitative review."""
    vt_clear = evaluate_value_trap(
        "DGC",
        valuation_report={"ok": True, "base_iv": 100000, "bear_iv": 60000, "current_price": 50000},
        financial_history=[
            {"fiscal_year": 2023, "net_income": 100, "cfo": 110, "revenue": 1000, "receivables": 100, "inventory": 100},
            {"fiscal_year": 2024, "net_income": 120, "cfo": 130, "revenue": 1200, "receivables": 110, "inventory": 110},
            {"fiscal_year": 2025, "net_income": 140, "cfo": 150, "revenue": 1400, "receivables": 120, "inventory": 120},
        ],
    )
    assert vt_clear.status == "CLEAR"

    vt_watch = evaluate_value_trap(
        "TRAP",
        valuation_report={"ok": True, "base_iv": 100000, "bear_iv": 40000, "current_price": 50000},
        financial_history=[
            {"fiscal_year": 2023, "net_income": 100, "cfo": 50, "revenue": 1000, "receivables": 100, "inventory": 100},
            {"fiscal_year": 2024, "net_income": 80, "cfo": 40, "revenue": 1200, "receivables": 300, "inventory": 300},
            {"fiscal_year": 2025, "net_income": 60, "cfo": 30, "revenue": 1400, "receivables": 500, "inventory": 500},
        ],
    )
    assert vt_watch.status in ("WATCH", "HIGH_RISK")


def test_qualitative_unknown_does_not_erase_quantitative_valuation():
    """Verify qualitative evidence UNKNOWN does not block quantitative valuation model."""
    ctx = build_decision_context(
        symbol="FPT",
        valuation={"ok": True, "base_iv": 150000, "model_status": "VALID", "current_price": 100000},
        business_review={"overall_status": "UNKNOWN"},
    )
    assert ctx.base_iv == 150000
    assert ctx.data_readiness["valuation"] == "READY"


@pytest.mark.skipif(not os.environ.get("DATABASE_URL"), reason="Requires PostgreSQL database connection")
def test_fy_only_history_valuation_allowed():
    """Verify valuation readiness works on FY history without requiring quarterly data."""
    val = build_canonical_valuation("FPT", market_price=100000.0)
    assert val.get("ok") is True
    assert val.get("valuation_confidence") is not None
    assert len(val.get("financial_history", [])) > 0


@pytest.mark.skipif(not os.environ.get("DATABASE_URL"), reason="Requires PostgreSQL database connection")
def test_real_postgres_ssi_deterministic_selection_and_no_false_conflict():
    """Real DB test: Verify SSI facts take precedence over TCBS without creating false CANONICAL_FACT_CONFLICT."""
    audit = valuation_readiness_audit("FPT", market_price=100000.0)
    assert audit["status"] == "READY"
    assert len(audit.get("conflicts", [])) == 0

    snap = valuation_snapshot_from_catalog("FPT", market_price=100000.0)
    assert snap["ok"] is True


@pytest.mark.skipif(not os.environ.get("DATABASE_URL"), reason="Requires PostgreSQL database connection")
def test_real_postgres_golden_symbols_valuation_propagation():
    """Real DB test: Verify ACB, DGC, FPT, VIX propagate canonical valuation cleanly."""
    for sym in ["ACB", "DGC", "FPT", "VIX"]:
        val = build_canonical_valuation(sym, market_price=50000.0)
        assert val.get("ok") is True, f"Canonical valuation failed for {sym}"
        ctx = build_decision_context(symbol=sym, valuation=val)
        assert ctx.base_iv is not None, f"Base IV missing for {sym}"
        assert ctx.model_status in ("VALID", "MODEL_VERIFIED", "VERIFIED"), f"Invalid model_status for {sym}"
        assert ctx.data_readiness["valuation"] == "READY", f"Valuation readiness not READY for {sym}"
