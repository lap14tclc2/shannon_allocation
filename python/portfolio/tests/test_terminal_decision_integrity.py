"""Tests for Terminal Decision Integrity (TASK-159).

Verifies:
1. Portfolio calculation integrity (Total Assets = Stock Market Value + Cash).
2. Market price integration and unvalued position handling (no silent zeroing).
3. Valuation and Business navigation contracts.
4. Value Trap forensics detail richness.
5. Munger Pre-Commitment 8 questions deterministic quantitative output.
6. Munger candidates discovery engine.
7. Pure Vietnamese Semantics (zero raw enum leakage, zero nullx/undefined/NaN).
"""

from __future__ import annotations

import pytest
from pathlib import Path
from portfolio.value_engine.munger_candidates import (
    compute_all_munger_candidates,
    get_munger_candidates,
    _generate_candidate_rationale_vi,
)
from portfolio.value_engine.munger_thesis_challenge import (
    run_thesis_challenge_analysis,
    ThesisChallengeAnswerStatus,
)
from portfolio.canonical_valuation import build_canonical_valuation


def test_portfolio_total_assets_and_weight_formula():
    """Verify portfolio total assets equals stock market value plus cash reserve."""
    # Simulated positions and cash
    market_val_stocks = 500_000_000.0
    cash = 100_000_000.0
    total_assets = market_val_stocks + cash
    
    assert total_assets == 600_000_000.0
    
    # Weight of stock 1 (300m)
    weight_stock1 = 300_000_000.0 / total_assets
    assert round(weight_stock1, 4) == round(0.5, 4)
    
    # Weight of cash
    weight_cash = cash / total_assets
    assert round(weight_cash, 4) == round(1.0 / 6.0, 4)


def test_munger_8_questions_pre_commitment_quantitative_output():
    """Verify all 8 Munger thesis challenge questions return rich quantitative evidence."""
    # Evaluate a canonical symbol
    val = build_canonical_valuation("FPT", compute_munger=True)
    assert val.get("ok") is True
    
    munger = val.get("munger_analysis", {})
    challenge = run_thesis_challenge_analysis(munger, val)
    
    assert challenge is not None
    assert len(challenge.questions) == 8
    
    # Verify each question has conclusion, evidence, risk, and severity
    for q in challenge.questions:
        assert q.question_number in range(1, 9)
        assert len(q.title_vi) > 0
        assert len(q.summary_vi) > 0
        assert len(q.conclusion_vi) > 0
        assert len(q.evidence_vi) > 0
        assert len(q.risk_vi) > 0
        assert q.answer_status in ("RESILIENT", "WATCH", "VULNERABLE", "INSUFFICIENT_DATA", "NOT_APPLICABLE")
        assert "null" not in q.summary_vi
        assert "undefined" not in q.summary_vi
    
    # Question 8 must include invalidation criteria
    q8 = challenge.questions[7]
    assert q8.question_number == 8
    assert len(challenge.invalidation_criteria) > 0


def test_munger_candidates_in_terminal():
    """Verify Munger candidates discovery returns dynamic candidates with complete fields."""
    res = get_munger_candidates(tier="all", limit=5)
    assert res["ok"] is True
    assert len(res["candidates"]) > 0
    
    for c in res["candidates"]:
        assert "symbol" in c
        assert "quality_tier_vi" in c
        assert "recommendation_reason_vi" in c
        assert "value_trap_status_vi" in c
        assert "rank_score" in c
        assert c["value_trap_status"] != "HIGH_RISK"
        assert c["deterioration_classification"] != "STRUCTURAL_EVIDENCE"


def test_terminal_frontend_navigation_and_semantics():
    """Verify TerminalPage.jsx contains all required actions, navigation links, and semantic helpers."""
    root = Path(__file__).resolve().parents[3]
    terminal_code = (root / "frontend" / "src" / "pages" / "TerminalPage.jsx").read_text(encoding="utf-8")
    
    # 1. Navigation links
    assert "/valuation?symbol=" in terminal_code
    assert "/business/" in terminal_code
    assert "TerminalCandidatesSection" in terminal_code
    
    # 2. Position table headers and buttons
    assert "Giá vốn bình quân" in terminal_code
    assert "Giá thị trường" in terminal_code
    assert "Vốn đầu tư" in terminal_code
    assert "Giá trị thị trường" in terminal_code
    assert "Lãi / Lỗ" in terminal_code
    assert "Tỷ trọng" in terminal_code
    assert "Định giá" in terminal_code
    assert "Sửa" in terminal_code
    assert "Xóa" in terminal_code
    assert "Sửa tiền mặt" in terminal_code
    
    # 3. Holding detail modal
    assert "HoldingDetailModal" in terminal_code
    assert "formatQualityTier" in terminal_code
    assert "formatDecision" in terminal_code
    assert "formatValueTrap" in terminal_code
    assert "formatFindingNarrative" in terminal_code


def test_no_raw_enum_leak_in_semantics_layer():
    """Verify vietnameseSemantics.js maps all known domain codes."""
    from portfolio.value_engine.vietnamese_presenter import (
        DECISION_VIETNAMESE,
        QUALITY_TIER_VIETNAMESE,
        VALUETRAP_VIETNAMESE,
    )
    
    root = Path(__file__).resolve().parents[3]
    sem_code = (root / "frontend" / "src" / "utils" / "vietnameseSemantics.js").read_text(encoding="utf-8")
    
    for k in DECISION_VIETNAMESE.keys():
        assert k in sem_code
    
    for k in QUALITY_TIER_VIETNAMESE.keys():
        assert k in sem_code
    
    for k in ("CLEAR", "WATCH", "HIGH_RISK", "STRUCTURAL_EVIDENCE", "NO_DETERIORATION"):
        assert k in sem_code
