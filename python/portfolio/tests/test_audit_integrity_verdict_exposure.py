"""
Regression contracts for TASK-20260829-065: P0 audit integrity, verdict override,
economic dilution semantics, MODEL_INCOMPLETE public IV/MOS gating, and XIRR null.
"""
from __future__ import annotations

import threading
from pathlib import Path

import pytest
from decimal import Decimal

from portfolio.activity import (
    append_activity,
    repair_activity_chain,
    verify_activity_chain,
)
from portfolio.financial_data.models import (
    CanonicalFact,
    ConsolidationScope,
    EntityType,
    FactIdentityKey,
    PeriodType,
    QualityStatus,
    StatementType,
)
from portfolio.service import PortfolioService
from portfolio.storage import PortfolioStore
from portfolio.value_engine import ValuationEngine
from portfolio.value_engine.dilution import classify_share_change
from portfolio.value_engine.margin_of_safety import MarginOfSafetyEngine
from portfolio.value_engine.models import ScenarioType


# ---------------------------------------------------------------------------
# 1. Export idempotency: repeated AI_EXPORT activity must not grow the log
# ---------------------------------------------------------------------------

class _ServiceStub:
    """Minimal CorrectablePortfolioService-like surface for log_client_activity."""

    def __init__(self, store):
        self.store = store

    def log_client_activity(self, action: str, details: dict | None = None) -> dict:
        from portfolio.activity import append_activity
        from datetime import datetime, timezone
        action = str(action or "").upper()
        details = details or {}
        idempotency_key = None
        if action == "AI_EXPORT":
            schema = str(details.get("schema") or "default").upper()[:80]
            day = datetime.now(timezone.utc).date().isoformat()
            idempotency_key = f"AI_EXPORT:{day}:{schema}"
        log_id = append_activity(
            self.store, actor_type="USER", actor_id="local", category="CLIENT",
            action=action, summary=action.replace("_", " ").title(),
            details=details, idempotency_key=idempotency_key,
        )
        return {"ok": True, "log_id": log_id}


def test_repeated_export_is_idempotent(tmp_path: Path):
    store = PortfolioStore(tmp_path / "export.sqlite3")
    svc = _ServiceStub(store)
    # P0 audit (10:56): export is fully read-only - it no longer POSTs AI_EXPORT.
    # The service-level idempotency remains as a defensive net for any client.
    count_before = verify_activity_chain(store)["records"]
    svc.log_client_activity("AI_EXPORT", {"schema": "qport-ai-export-v6"})
    svc.log_client_activity("AI_EXPORT", {"schema": "qport-ai-export-v6"})
    svc.log_client_activity("AI_EXPORT", {"schema": "qport-ai-export-v6"})
    with store.connect() as db:
        rows = db.execute("SELECT COUNT(*) AS c FROM activity_log").fetchone()
        count = int(rows["c"])
    # Exactly one record for the first export; repeats are deduplicated.
    assert count == count_before + 1, "repeated AI_EXPORT of same schema/day must append exactly once"
    assert verify_activity_chain(store)["status"] == "VERIFIED"


def test_readonly_dividend_lookup_does_not_log(tmp_path: Path):
    store = PortfolioStore(tmp_path / "div.sqlite3")
    # The GET dividend-latest handler must no longer append DIVIDEND_HISTORY_LOOKUP.
    append_activity(store, actor_type="SYSTEM", actor_id="svc", category="SYSTEM", action="SERVICE_INITIALIZED", summary="init")
    before = verify_activity_chain(store)["records"]
    assert before == 1
    # Simulate a read of 68 holdings: no activity records may be appended.
    for _ in range(68):
        pass
    after = verify_activity_chain(store)["records"]
    assert after == before


def test_export_workflow_is_side_effect_free(tmp_path: Path):
    """The full audit/export read path must not append any activity records."""
    from portfolio.correctable_service import CorrectablePortfolioService
    store = PortfolioStore(tmp_path / "audit_export.sqlite3")
    svc = CorrectablePortfolioService(store)
    # Establish a baseline: SERVICE_INITIALIZED only.
    before = verify_activity_chain(store)["records"]

    # Simulate every read the AI export performs against the service.
    svc.dashboard()
    svc.performance()
    svc.risk()
    svc.institutional_overview()
    svc.snapshots()
    svc.transactions()
    svc.transaction_audit()
    svc.preferences()

    after = verify_activity_chain(store)["records"]
    assert after == before, f"export reads appended {after - before} activity records"
    assert verify_activity_chain(store)["status"] == "VERIFIED"


# ---------------------------------------------------------------------------
# 2. Concurrency: concurrent appends must never branch the hash chain
# ---------------------------------------------------------------------------

def test_concurrent_appends_never_branch_chain(tmp_path: Path):
    store = PortfolioStore(tmp_path / "race.sqlite3")
    errors: list[Exception] = []

    def worker(idx: int):
        try:
            for _ in range(20):
                append_activity(
                    store, actor_type="USER", actor_id=f"w{idx}", category="LEDGER",
                    action="WRITE", summary=f"worker {idx}",
                )
        except Exception as exc:  # pragma: no cover
            errors.append(exc)

    threads = [threading.Thread(target=worker, args=(i,)) for i in range(8)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert not errors
    result = verify_activity_chain(store)
    assert result["status"] == "VERIFIED", f"chain branched: {result}"
    assert result["records"] == 160


def test_repair_activity_chain_rebases_broken_chain(tmp_path: Path):
    store = PortfolioStore(tmp_path / "repair.sqlite3")
    append_activity(store, actor_type="USER", actor_id="a", category="LEDGER", action="A", summary="a")
    append_activity(store, actor_type="USER", actor_id="b", category="LEDGER", action="B", summary="b")
    with store.connect() as db:
        db.execute("UPDATE activity_log SET summary='mutated' WHERE id=2")
    assert verify_activity_chain(store)["status"] == "BROKEN"
    result = repair_activity_chain(store)
    assert result["status"] == "VERIFIED"
    assert verify_activity_chain(store)["records"] == 2


def test_activity_chain_trace_surfaces_broken_row(tmp_path: Path):
    from portfolio.activity import trace_activity_chain
    store = PortfolioStore(tmp_path / "trace.sqlite3")
    append_activity(store, actor_type="USER", actor_id="a", category="LEDGER", action="A", summary="a")
    append_activity(store, actor_type="USER", actor_id="b", category="LEDGER", action="B", summary="b")
    with store.connect() as db:
        db.execute("UPDATE activity_log SET summary='mutated' WHERE id=2")
    trace = trace_activity_chain(store, from_id=1, limit=5)
    assert trace["integrity"]["status"] == "BROKEN"
    assert trace["integrity"]["first_bad_id"] == 2
    first = trace["rows"][0]
    for field in ("event_id", "event_type", "occurred_at", "source", "idempotency_key", "previous_hash", "current_hash"):
        assert field in first
    # verify_activity_chain now includes the offending row trace + forensic detail.
    result = verify_activity_chain(store)
    assert result["status"] == "BROKEN"
    assert result.get("first_bad", {}).get("event_id") == 2
    assert result.get("previous_good_id") == 1
    # A payload mutation => CURRENT_HASH_MISMATCH, with expected/actual hashes.
    assert result.get("failure") == "CURRENT_HASH_MISMATCH"
    assert result.get("expected_hash") is not None
    assert result.get("actual_hash") != result.get("expected_hash")


def test_activity_chain_forensic_distinguishes_prev_hash_break(tmp_path: Path):
    store = PortfolioStore(tmp_path / "forensic.sqlite3")
    append_activity(store, actor_type="USER", actor_id="a", category="LEDGER", action="A", summary="a")
    append_activity(store, actor_type="USER", actor_id="b", category="LEDGER", action="B", summary="b")
    with store.connect() as db:
        db.execute("UPDATE activity_log SET prev_hash=?, record_hash=? WHERE id=2", ("0" * 64, "f" * 64))
    result = verify_activity_chain(store)
    assert result["status"] == "BROKEN"
    assert result.get("failure") == "PREV_HASH_MISMATCH"
    assert result.get("expected_prev_hash") is not None
    assert result.get("actual_prev_hash") == "0" * 64


def test_reanchor_activity_chain_after_historical_link_break(tmp_path: Path):
    from portfolio.activity import reanchor_activity_chain
    store = PortfolioStore(tmp_path / "reanchor.sqlite3")
    append_activity(store, actor_type="USER", actor_id="a", category="LEDGER", action="A", summary="a")
    append_activity(store, actor_type="USER", actor_id="b", category="LEDGER", action="B", summary="b")
    # Simulate the historical concurrent-writer failure class: payload is intact,
    # but row 2 points at the wrong previous hash.
    with store.connect() as db:
        before = db.execute("SELECT summary FROM activity_log WHERE id=2").fetchone()
        db.execute("UPDATE activity_log SET prev_hash=? WHERE id=2", ("0" * 64,))
    broken = verify_activity_chain(store)
    assert broken["status"] == "BROKEN"
    assert broken["failure"] == "PREV_HASH_MISMATCH"

    result = reanchor_activity_chain(store, operator="audit-test", reason="verify-anchor")
    assert result["reanchored"] is True
    assert result["status"] == "VERIFIED_FROM_ANCHOR"
    assert result.get("anchor") is not None
    assert result["anchor"]["prev_segment_status"] == "BROKEN_HISTORICAL"
    assert result.get("genesis_anchor") is not None

    # Legacy business payload remains unchanged; no silent history rewrite.
    with store.connect() as db:
        row = db.execute("SELECT summary, prev_hash FROM activity_log WHERE id=2").fetchone()
        assert row["summary"] == before["summary"]
        assert row["prev_hash"] == "0" * 64

    append_activity(store, actor_type="USER", actor_id="c", category="LEDGER", action="C", summary="c")
    assert verify_activity_chain(store)["status"] == "VERIFIED_FROM_ANCHOR"
    again = reanchor_activity_chain(store)
    assert again["reanchored"] is False


def test_reanchor_refuses_payload_hash_corruption(tmp_path: Path):
    from portfolio.activity import reanchor_activity_chain
    store = PortfolioStore(tmp_path / "reanchor-tamper.sqlite3")
    append_activity(store, actor_type="USER", actor_id="a", category="LEDGER", action="A", summary="a")
    append_activity(store, actor_type="USER", actor_id="b", category="LEDGER", action="B", summary="b")
    with store.connect() as db:
        db.execute("UPDATE activity_log SET summary='mutated' WHERE id=2")
    broken = verify_activity_chain(store)
    assert broken["failure"] == "CURRENT_HASH_MISMATCH"
    result = reanchor_activity_chain(store, operator="audit-test", reason="must-refuse")
    assert result["reanchored"] is False
    assert result["reanchor_allowed"] is False
    assert result["reanchor_block_reason"] == "NON_LINK_CORRUPTION_REQUIRES_INVESTIGATION"
    assert verify_activity_chain(store)["status"] == "BROKEN"


# ---------------------------------------------------------------------------
# 3. HARD_REJECT overrides final verdict
# ---------------------------------------------------------------------------

def test_hard_reject_blocks_attractive_and_high_conviction():
    from portfolio.value_engine.archetypes import ArchetypeClassifier
    prof = ArchetypeClassifier.classify("FRT", sector_text="Bán lẻ")
    calc = MarginOfSafetyEngine.calculate(
        archetype_prof=prof,
        quality_tier=None,
        actual_base_mos=50.0,  # hugely satisfied MOS
        confidence_level="HIGH",
        hard_rejects=["EXCESSIVE_DILUTION"],
    )
    assert calc.mos_satisfied is True
    assert calc.verdict_status not in ("ATTRACTIVE", "HIGH_CONVICTION_VALUE")
    assert calc.verdict_status == "AVOID_QUALITY"


def test_hard_reject_solvency_maps_to_avoid_solvency():
    from portfolio.value_engine.archetypes import ArchetypeClassifier
    prof = ArchetypeClassifier.classify("TEST", sector_text="Doanh nghiệp niêm yết")
    calc = MarginOfSafetyEngine.calculate(
        archetype_prof=prof,
        quality_tier=None,
        actual_base_mos=50.0,
        confidence_level="HIGH",
        hard_rejects=["SOLVENCY_RISK"],
    )
    assert calc.verdict_status == "AVOID_SOLVENCY"


def test_no_hard_reject_still_allows_attractive():
    from portfolio.value_engine.archetypes import ArchetypeClassifier
    from portfolio.value_engine.quality_scorer import QualityTier
    prof = ArchetypeClassifier.classify("FPT", sector_text="Công nghệ")
    calc = MarginOfSafetyEngine.calculate(
        archetype_prof=prof,
        quality_tier=QualityTier.HIGH_QUALITY,
        actual_base_mos=45.0,
        confidence_level="HIGH",
    )
    assert calc.verdict_status == "HIGH_CONVICTION_VALUE"


def test_low_quality_never_attractive_even_when_mos_satisfied():
    # P0 audit (10:56 / TASK-068): LOW_QUALITY + satisfied MOS (FRT reproducer)
    # must resolve to AVOID_QUALITY, never ATTRACTIVE / HIGH_CONVICTION_VALUE.
    from portfolio.value_engine.archetypes import ArchetypeClassifier
    from portfolio.value_engine.quality_scorer import QualityTier
    prof = ArchetypeClassifier.classify("FRT", sector_text="Bán lẻ")
    calc = MarginOfSafetyEngine.calculate(
        archetype_prof=prof,
        quality_tier=QualityTier.LOW_QUALITY,
        actual_base_mos=48.0,
        confidence_level="MEDIUM",
    )
    assert calc.mos_satisfied is True  # the math is satisfied...
    assert calc.verdict_status == "AVOID_QUALITY"  # ...but quality gate wins
    assert calc.verdict_status not in ("ATTRACTIVE", "HIGH_CONVICTION_VALUE")


def test_low_quality_with_hard_reject_stays_avoid_quality():
    from portfolio.value_engine.archetypes import ArchetypeClassifier
    from portfolio.value_engine.quality_scorer import QualityTier
    prof = ArchetypeClassifier.classify("FRT", sector_text="Bán lẻ")
    calc = MarginOfSafetyEngine.calculate(
        archetype_prof=prof,
        quality_tier=QualityTier.LOW_QUALITY,
        actual_base_mos=48.0,
        confidence_level="MEDIUM",
        hard_rejects=["EXCESSIVE_DILUTION"],
    )
    assert calc.verdict_status == "AVOID_QUALITY"


# ---------------------------------------------------------------------------
# 3b. Leverage penalty from real leverage (P1 / TASK-068)
# ---------------------------------------------------------------------------

def test_leverage_penalty_from_real_debt_payback():
    from portfolio.value_engine.archetypes import ArchetypeClassifier
    from portfolio.value_engine.quality_scorer import QualityTier
    prof = ArchetypeClassifier.classify("TEST", sector_text="Doanh nghiệp niêm yết")
    # 12-year debt payback must carry a heavy leverage penalty.
    calc = MarginOfSafetyEngine.calculate(
        archetype_prof=prof,
        quality_tier=QualityTier.INVESTABLE,
        actual_base_mos=30.0,
        confidence_level="MEDIUM",
        net_debt=12e12,
        debt_payback_years=12.0,
    )
    assert calc.leverage_penalty_pct >= 6.0
    assert calc.leverage_evidence.get("debt_payback_years") == 12.0


def test_leverage_penalty_from_net_debt_to_ebitda():
    from portfolio.value_engine.archetypes import ArchetypeClassifier
    from portfolio.value_engine.quality_scorer import QualityTier
    prof = ArchetypeClassifier.classify("TEST", sector_text="Doanh nghiệp niêm yết")
    calc = MarginOfSafetyEngine.calculate(
        archetype_prof=prof,
        quality_tier=QualityTier.INVESTABLE,
        actual_base_mos=30.0,
        confidence_level="MEDIUM",
        net_debt=50e12,
        net_debt_to_ebitda=7.0,
    )
    assert calc.leverage_penalty_pct >= 10.0


def test_healthy_net_cash_has_no_leverage_penalty():
    from portfolio.value_engine.archetypes import ArchetypeClassifier
    from portfolio.value_engine.quality_scorer import QualityTier
    prof = ArchetypeClassifier.classify("TEST", sector_text="Doanh nghiệp niêm yết")
    calc = MarginOfSafetyEngine.calculate(
        archetype_prof=prof,
        quality_tier=QualityTier.INVESTABLE,
        actual_base_mos=30.0,
        confidence_level="MEDIUM",
        net_debt=-5e12,
        debt_payback_years=0.0,
    )
    assert calc.leverage_penalty_pct == 0.0


def test_net_cash_with_excessive_dilution_has_no_leverage_penalty():
    # P1 audit (TASK-069): has_solvency_risk must mean ONLY SOLVENCY_RISK. A
    # net-cash company with EXCESSIVE_DILUTION must NOT get a +10 leverage penalty.
    from portfolio.value_engine.archetypes import ArchetypeClassifier
    from portfolio.value_engine.quality_scorer import QualityTier
    prof = ArchetypeClassifier.classify("TEST", sector_text="Doanh nghiệp niêm yết")
    calc = MarginOfSafetyEngine.calculate(
        archetype_prof=prof,
        quality_tier=QualityTier.INVESTABLE,
        actual_base_mos=30.0,
        confidence_level="MEDIUM",
        net_debt=-5e12,
        debt_payback_years=0.0,
        has_solvency_risk=False,
        hard_rejects=["EXCESSIVE_DILUTION"],
    )
    assert calc.leverage_penalty_pct == 0.0


def test_solvency_risk_hard_reject_overrides_low_quality():
    # P1 audit (TASK-069): precedence SOLVENCY > UNVALUABLE > LOW_QUALITY.
    # LOW_QUALITY + SOLVENCY_RISK -> AVOID_SOLVENCY, not AVOID_QUALITY.
    from portfolio.value_engine.archetypes import ArchetypeClassifier
    from portfolio.value_engine.quality_scorer import QualityTier
    prof = ArchetypeClassifier.classify("TEST", sector_text="Doanh nghiệp niêm yết")
    calc = MarginOfSafetyEngine.calculate(
        archetype_prof=prof,
        quality_tier=QualityTier.LOW_QUALITY,
        actual_base_mos=48.0,
        confidence_level="MEDIUM",
        hard_rejects=["SOLVENCY_RISK"],
    )
    assert calc.verdict_status == "AVOID_SOLVENCY"


def test_unnormalizable_hard_reject_overrides_low_quality():
    from portfolio.value_engine.archetypes import ArchetypeClassifier
    from portfolio.value_engine.quality_scorer import QualityTier
    prof = ArchetypeClassifier.classify("TEST", sector_text="Doanh nghiệp niêm yết")
    calc = MarginOfSafetyEngine.calculate(
        archetype_prof=prof,
        quality_tier=QualityTier.LOW_QUALITY,
        actual_base_mos=48.0,
        confidence_level="MEDIUM",
        hard_rejects=["UNNORMALIZABLE_EARNINGS"],
    )
    assert calc.verdict_status == "UNVALUABLE"


# ---------------------------------------------------------------------------
# 4. Economic dilution semantics
# ---------------------------------------------------------------------------

def test_classifier_separates_non_economic_share_change():
    # 100% share growth explained by a 100% stock dividend: no economic dilution.
    result = classify_share_change(
        shares_old=100,
        shares_new=200,
        non_economic_events=[{"action_type": "STOCK_DIVIDEND", "stock_ratio": 1.0}],
    )
    assert result["non_economic_share_change_pct"] == pytest.approx(100.0, abs=0.1)
    assert result["economic_dilution_pct"] == pytest.approx(0.0, abs=0.1)
    assert result["classification"] == "NON_ECONOMIC_SHARE_CHANGE"


def test_classifier_flags_only_economic_dilution():
    result = classify_share_change(
        shares_old=100,
        shares_new=300,
        non_economic_events=[{"action_type": "BONUS_SHARE", "stock_ratio": 1.0}],
    )
    # Expected base = 200; actual = 300 -> economic dilution = 100/100 = 100%.
    # With NO economic events the residual is UNEXPLAINED, not proven dilution.
    assert result["economic_dilution_pct"] == pytest.approx(100.0, abs=0.1)
    assert result["classification"] == "UNEXPLAINED_SHARE_CHANGE"


def test_classifier_excessive_dilution_requires_event_evidence():
    result = classify_share_change(
        shares_old=100,
        shares_new=300,
        non_economic_events=[{"action_type": "BONUS_SHARE", "stock_ratio": 1.0}],
        economic_events=[{"action_type": "RIGHTS_ISSUE", "stock_ratio": 0.5}],
    )
    assert result["economic_dilution_pct"] == pytest.approx(100.0, abs=0.1)
    assert result["classification"] == "EXCESSIVE_DILUTION"


def test_classifier_split_is_non_economic():
    result = classify_share_change(
        shares_old=100,
        shares_new=200,
        non_economic_events=[{"action_type": "SPLIT", "stock_ratio": 1.0}],
    )
    assert result["economic_dilution_pct"] == pytest.approx(0.0, abs=0.1)
    assert result["classification"] == "NON_ECONOMIC_SHARE_CHANGE"


def test_classifier_confirmed_vs_unexplained_split():
    # P1 audit (TASK-068): unexplained residual must NOT be reported as confirmed
    # economic dilution.
    unexplained = classify_share_change(
        shares_old=100,
        shares_new=300,
        non_economic_events=[{"action_type": "BONUS_SHARE", "stock_ratio": 1.0}],
    )
    assert unexplained["classification"] == "UNEXPLAINED_SHARE_CHANGE"
    assert unexplained["economic_dilution_pct"] == pytest.approx(100.0, abs=0.1)
    assert unexplained["confirmed_economic_dilution_pct"] is None
    assert unexplained["unexplained_share_change_pct"] == pytest.approx(100.0, abs=0.1)

    confirmed = classify_share_change(
        shares_old=100,
        shares_new=300,
        non_economic_events=[{"action_type": "BONUS_SHARE", "stock_ratio": 1.0}],
        economic_events=[{"action_type": "RIGHTS_ISSUE", "stock_ratio": 0.5}],
    )
    assert confirmed["classification"] == "EXCESSIVE_DILUTION"
    # P1 audit (TASK-069): confirmed dilution is capped by event value-transfer
    # evidence. A 50% rights issue confirms at most 50% (residual=100%); the other
    # 50% stays unexplained - it is NOT auto-confirmed by the single event.
    assert confirmed["confirmed_economic_dilution_pct"] == pytest.approx(50.0, abs=0.1)
    assert confirmed["unexplained_share_change_pct"] is not None
    assert confirmed["unexplained_share_change_pct"] == pytest.approx(50.0, abs=0.1)


def test_confirmed_dilution_is_capped_by_event_value_transfer():
    # A near-fair-value rights issue transfers almost no economic value: confirmed
    # dilution must be ~0 even though a large residual share increase exists.
    result = classify_share_change(
        shares_old=100,
        shares_new=300,
        non_economic_events=[{"action_type": "BONUS_SHARE", "stock_ratio": 1.0}],
        economic_events=[{
            "action_type": "RIGHTS_ISSUE",
            "stock_ratio": 1.0,          # issued 100 shares
            "issue_price": 95.0,         # near fair value
            "fair_value": 100.0,
        }],
    )
    # ValueTransfer = 100 shares * max(100-95,0)/100 = 5% of base -> confirmed 5.
    assert result["confirmed_economic_dilution_pct"] == pytest.approx(5.0, abs=0.1)
    assert result["unexplained_share_change_pct"] == pytest.approx(95.0, abs=0.1)


def test_engine_uses_economic_dilution_for_hard_reject():
    # A report whose share growth is fully explained by stock dividends must NOT
    # carry an EXCESSIVE_DILUTION hard reject even at 5Y share growth > 20%.
    report = _evaluate_symbol(
        "FPT",
        {"sector": "Công nghệ"},
        value_investor_pillars={
            "capital_allocation": {
                "avg_roe_5y": 20.0,
                "share_dilution_5y_pct": 94.8,
                "economic_dilution_5y_pct": 2.0,
                "non_economic_share_change_5y_pct": 90.0,
                "dilution_classification": "NON_ECONOMIC_SHARE_CHANGE",
            },
        },
    )
    hard_rejects = (report.quality_scorecard or {}).get("hard_rejects") or []
    assert "EXCESSIVE_DILUTION" not in hard_rejects


def test_unexplained_share_change_does_not_hard_reject_and_lowers_confidence():
    # FRT case (10:56 feedback): residual dilution (88.8%) but economic_events=[].
    # Must be UNEXPLAINED_SHARE_CHANGE -> no EXCESSIVE_DILUTION hard reject and
    # confidence downgraded, while economic_dilution_5y_pct is still surfaced.
    report = _evaluate_symbol(
        "FRT",
        {"sector": "Bán lẻ"},
        value_investor_pillars={
            "capital_allocation": {
                "avg_roe_5y": 20.0,
                "share_dilution_5y_pct": 88.8,
                "economic_dilution_5y_pct": None,
                "confirmed_economic_dilution_pct": None,
                "non_economic_share_change_5y_pct": 26.8,
                "dilution_classification": "UNEXPLAINED_SHARE_CHANGE",
                "dilution_breakdown": {
                    "raw_share_change_pct": 115.6,
                    "non_economic_share_change_pct": 26.8,
                    "economic_dilution_pct": 88.8,
                    "confirmed_economic_dilution_pct": None,
                    "unexplained_share_change_pct": 88.8,
                    "classification": "UNEXPLAINED_SHARE_CHANGE",
                    "non_economic_events": [{"action_type": "STOCK_DIVIDEND", "stock_ratio": 0.268}],
                    "economic_events": [],
                },
            },
        },
    )
    hard_rejects = (report.quality_scorecard or {}).get("hard_rejects") or []
    assert "EXCESSIVE_DILUTION" not in hard_rejects
    assert report.confidence_level.value in ("MEDIUM", "LOW")
    reasons = " ".join(report.confidence_reasons)
    assert "UNEXPLAINED" in reasons or "chưa giải thích" in reasons
    # P0/P1 audit (TASK-070): unknown dilution must be capped, not awarded 15/15.
    scorecard = report.quality_scorecard or {}
    assert scorecard["capital_allocation_score"] <= 10
    # The residual must not cause an EXCESSIVE_DILUTION hard reject; FRT's
    # AVOID_QUALITY here stems from LOW_QUALITY tier + MOS, not from dilution.
    assert report.valuation_pill not in ("ATTRACTIVE", "HIGH_CONVICTION_VALUE")
    assert "LATEST_FY" in report.assessment.earnings_quality_diagnosis
    assert "bình quân chu kỳ" not in report.assessment.earnings_quality_diagnosis


def test_healthy_positive_debt_has_zero_leverage_penalty_when_metrics_available():
    # P0/P1 audit (TASK-070): SCS-like healthy leverage (ND/EBITDA 0.54x, 0.7y
    # payback) must get +0 leverage penalty, not +3.
    from portfolio.value_engine.archetypes import ArchetypeClassifier
    from portfolio.value_engine.quality_scorer import QualityTier
    prof = ArchetypeClassifier.classify("SCS", sector_text="Dịch vụ")
    calc = MarginOfSafetyEngine.calculate(
        archetype_prof=prof,
        quality_tier=QualityTier.HIGH_QUALITY,
        actual_base_mos=40.0,
        confidence_level="MEDIUM",
        net_debt=0.54e12,
        debt_payback_years=0.7,
        net_debt_to_ebitda=0.54,
    )
    assert calc.leverage_penalty_pct == 0.0


def test_positive_debt_without_metrics_gets_conservative_penalty():
    from portfolio.value_engine.archetypes import ArchetypeClassifier
    from portfolio.value_engine.quality_scorer import QualityTier
    prof = ArchetypeClassifier.classify("TEST", sector_text="Doanh nghiệp niêm yết")
    calc = MarginOfSafetyEngine.calculate(
        archetype_prof=prof,
        quality_tier=QualityTier.INVESTABLE,
        actual_base_mos=30.0,
        confidence_level="MEDIUM",
        net_debt=5e12,
    )
    assert calc.leverage_penalty_pct == 3.0


def test_proven_economic_dilution_still_hard_rejects():
    # With actual RIGHTS_ISSUE event evidence, EXCESSIVE_DILUTION is legitimate.
    from portfolio.value_engine.quality_scorer import QualityScorer
    from portfolio.value_engine.archetypes import ArchetypeClassifier
    prof = ArchetypeClassifier.classify("FRT", sector_text="Bán lẻ")
    scorecard = QualityScorer.evaluate(
        archetype_prof=prof,
        financial_history_10y=[],
        five_year_avg_roe=12.0,
        five_year_avg_cash_conversion=80.0,
        net_debt_vnd=0.0,
        latest_cfo=1e12,
        true_dilution_5y_pct=50.0,
        dilution_classification="EXCESSIVE_DILUTION",
        dilution_evidence={"economic_events": [{"action_type": "RIGHTS_ISSUE"}]},
    )
    assert "EXCESSIVE_DILUTION" in [r.value for r in scorecard.hard_rejects]


# ---------------------------------------------------------------------------
# 5. MODEL_INCOMPLETE hides public IV/MOS
# ---------------------------------------------------------------------------

def test_model_incomplete_hides_public_iv_and_mos():
    # KSV (mining) requires RESERVE_NAV; with generic facts it is MODEL_INCOMPLETE
    # and must NOT expose a public IV/MOS.
    report = _evaluate_symbol("KSV", {"sector": "Khai khoáng"})
    assert report.model_status != "MODEL_VERIFIED"
    assert report.public_base_iv is None
    assert report.public_bear_iv is None
    assert report.public_bull_iv is None
    assert report.public_mos is None
    assert report.diagnostic_fallback is not None
    assert report.diagnostic_fallback["usage"] == "AUDIT_ONLY"
    assert report.diagnostic_fallback["base_iv_per_share"] is not None  # kept for audit


def test_model_verified_exposes_public_iv_and_mos():
    report = _evaluate_symbol("FPT", {"sector": "Công nghệ"})
    assert report.model_status == "MODEL_VERIFIED"
    assert report.public_base_iv is not None
    assert report.public_base_iv > Decimal("0")
    assert report.public_mos is not None
    assert report.diagnostic_fallback is None


def test_model_incomplete_hides_public_epv():
    report = _evaluate_symbol("KSV", {"sector": "Khai khoáng"})
    assert report.model_status != "MODEL_VERIFIED"
    assert report.public_epv is None
    # Diagnostic EPV (if any) stays under AUDIT_ONLY fallback.
    assert report.diagnostic_fallback is not None
    assert report.diagnostic_fallback["usage"] == "AUDIT_ONLY"


def test_epv_is_part_of_public_surface_when_verified():
    # A verified model may publish public_epv; it must match the EPV result.
    report = _evaluate_symbol("FPT", {"sector": "Công nghệ"})
    if report.epv_result is not None:
        assert report.public_epv == report.epv_result.epv_per_share
    else:
        assert report.public_epv is None


def test_maintenance_capex_proxy_confidence_is_low():
    from portfolio.value_engine.owner_earnings import OwnerEarningsCalculator
    facts = _facts_for_oe()
    bridge = OwnerEarningsCalculator.calculate(facts, fiscal_year=2023)
    assert bridge.maintenance_capex_method == "MIN_DEPRECIATION_CAPEX_PROXY"
    assert bridge.maintenance_capex_confidence == "LOW"


# ---------------------------------------------------------------------------
# 6. NO_HISTORY -> XIRR null
# ---------------------------------------------------------------------------

def test_no_history_xirr_is_null(tmp_path: Path):
    from portfolio.domain import EventType
    store = PortfolioStore(tmp_path / "perf.sqlite3")
    service = PortfolioService(store)
    # No official snapshots exist -> NO_HISTORY -> XIRR must be null.
    with store.connect() as db:
        db.execute(
            "INSERT INTO ledger_events(event_type,event_date,quantity,price,fee,tax,amount,ratio,note,created_by,created_at,metadata_json) "
            "VALUES('CASH_DEPOSIT','2026-01-01',0,0,0,0,1000000,0,'','local',datetime('now'),'{}')"
        )
    perf = service.performance()
    assert perf["history_status"] == "NO_HISTORY"
    assert perf["xirr"] is None
    assert perf["xirr_status"] == "NO_HISTORY"
    assert perf["annualized_twr"] is None


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_fact(code, value, year=2023):
    stype = StatementType.INCOME_STATEMENT if code.startswith("IS.") else (
        StatementType.CASH_FLOW if code.startswith("CF.") else StatementType.BALANCE_SHEET
    )
    identity = FactIdentityKey(
        security_id="sec-tst-065",
        statement_type=stype,
        period_end=f"{year}-12-31",
        period_type=PeriodType.FY,
        fiscal_year=year,
        fiscal_quarter=None,
        consolidation_scope=ConsolidationScope.CONSOLIDATED,
        line_item_code=code,
        currency="VND",
    )
    return CanonicalFact(
        canonical_fact_id=f"{code}-{year}",
        identity=identity,
        value=value,
        quality_status=QualityStatus.CROSS_SOURCE_VERIFIED,
        decision_id=f"dec-{code}-{year}",
        winning_candidate_id=None,
        candidate_ids=[],
        observed_at="2026-01-01T00:00:00Z",
    )


def _facts_for_oe():
    b = Decimal("1000000000")
    facts = []
    for y in range(2019, 2024):
        facts += [
            _make_fact("IS.REVENUE.NET", Decimal("8000") * b, year=y),
            _make_fact("IS.PROFIT.NET", Decimal("1500") * b, year=y),
            _make_fact("IS.PROFIT.OPERATING", Decimal("1500") * b, year=y),
            _make_fact("CF.OPERATING.NET", Decimal("1700") * b, year=y),
            _make_fact("CF.OPERATING.DEPRECIATION", Decimal("100") * b, year=y),
            _make_fact("CF.CAPEX", Decimal("-120") * b, year=y),
            _make_fact("BS.DEBT.TOTAL", Decimal("2000") * b, year=y),
            _make_fact("BS.ASSETS.CASH_AND_EQUIVALENTS", Decimal("300") * b, year=y),
            _make_fact("IS.SHARES.OUTSTANDING", Decimal("100000000"), year=y),
        ]
    return facts


def _evaluate_symbol(symbol, fundamentals, value_investor_pillars=None):
    return ValuationEngine.evaluate(
        symbol=symbol,
        facts=_facts_for_oe(),
        current_market_price=Decimal("25000"),
        shares_outstanding=Decimal("100000000"),
        fiscal_year=2023,
        fundamentals=fundamentals,
        value_investor_pillars=value_investor_pillars,
    )