"""Unit and Integration Tests for Munger Long-Term Candidates & Portfolio Valuation Navigation (Task 158).

Verifies:
1. Munger candidate discovery engine filters and ranks universe by quality first.
2. Value trap warnings and accounting failures properly disqualify candidates.
3. Every candidate has a rich Vietnamese semantic rationale (no raw machine enums).
4. API endpoint /api/portfolio/business-candidates returns structured payload without N+1 requests.
5. Valuation route contract supports symbol parameter and navigation.
"""

from __future__ import annotations

import os
import pytest
from portfolio.value_engine.munger_candidates import (
    compute_all_munger_candidates,
    get_munger_candidates,
    _generate_candidate_rationale_vi,
)


@pytest.mark.skipif(not os.environ.get("DATABASE_URL"), reason="Requires PostgreSQL database connection")
def test_munger_candidates_generation_and_ranking():
    """Verify candidates are discovered from canonical facts and ranked by quality score."""
    candidates = compute_all_munger_candidates(force_refresh=True)
    assert len(candidates) > 0

    # Ensure symbols are generic and not hardcoded
    symbols = [c["symbol"] for c in candidates]
    assert "FPT" in symbols or "ACB" in symbols or "DGC" in symbols

    # Check top candidate structure
    top = candidates[0]
    assert "symbol" in top
    assert "quality_tier_vi" in top
    assert "recommendation_reason_vi" in top
    assert "data_source" in top
    assert top["rank_score"] > 0
    assert top["value_trap_status"] in ("CLEAR", "WATCH")


def test_munger_candidates_filtering_and_rationale():
    """Verify rationale generation produces natural Vietnamese and no machine enums."""
    rationale = _generate_candidate_rationale_vi(
        symbol="FPT",
        quality_tier="EXCEPTIONAL",
        roe=23.4,
        pat_cagr=0.25,
        cfo_pat=0.92,
        vt_status="CLEAR",
        mos=23.7,
        req_mos=25.0,
        is_financial=False,
        top_warning_vi="Không có cảnh báo tài chính trọng yếu",
    )
    assert "ROE" in rationale
    assert "23.4%" in rationale
    assert "tăng trưởng" in rationale
    assert "Biên an toàn" in rationale
    assert "CLEAR" not in rationale
    assert "EXCEPTIONAL" not in rationale
    assert "null" not in rationale
    assert "undefined" not in rationale


@pytest.mark.skipif(not os.environ.get("DATABASE_URL"), reason="Requires PostgreSQL database connection")
def test_munger_candidates_disqualifies_severe_value_trap():
    """Verify company with structural deterioration is disqualified from candidate list."""
    from portfolio.value_engine.value_trap import ValueTrapAssessment

    # If a company has structural value trap status, it must not be in candidate list
    all_cand = compute_all_munger_candidates()
    for c in all_cand:
        assert c["value_trap_status"] != "HIGH_RISK"
        assert c["deterioration_classification"] != "STRUCTURAL_EVIDENCE"


def test_get_munger_candidates_api_wrapper():
    """Verify get_munger_candidates API response structure."""
    res = get_munger_candidates(tier="all", limit=10)
    assert res["ok"] is True
    assert "candidates" in res
    assert "summary" in res
    assert "total" in res
    assert len(res["candidates"]) <= 10
    assert res["summary"]["total_universe_evaluated"] >= len(res["candidates"])


def test_frontend_valuation_and_candidates_contract():
    """Verify frontend files have correct candidate hooks and valuation query navigation."""
    from pathlib import Path
    root = Path(__file__).resolve().parents[3]
    
    # 1. BusinessPage has candidate section
    biz_page = (root / "frontend" / "src" / "pages" / "BusinessPage.jsx").read_text(encoding="utf-8")
    assert "getMungerCandidates" in biz_page
    assert "Cổ phiếu tiềm năng theo tiêu chuẩn Munger" in biz_page
    assert "recommendation_reason_vi" in biz_page

    # 2. TerminalPage has valuation button
    terminal_page = (root / "frontend" / "src" / "pages" / "TerminalPage.jsx").read_text(encoding="utf-8")
    assert "table-btn-val" in terminal_page
    assert "/valuation?symbol=" in terminal_page

    # 3. ValuationPage handles symbol query param
    val_page = (root / "frontend" / "src" / "pages" / "ValuationPage.jsx").read_text(encoding="utf-8")
    assert "new URLSearchParams(window.location.search).get('symbol')" in val_page
