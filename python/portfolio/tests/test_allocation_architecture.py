"""Allocation architecture boundaries (T00/T08 audit).

Guards the core invariants:
- no duplicate risk engine (reuse canonical portfolio_risk);
- no duplicate valuation engine;
- no Kelly sizing / expected alpha in V1;
- no auto-execution / ledger writes;
- no direct provider-crawl imports in the allocation domain;
- existing /valuation, /risk, /screener responsibilities preserved.
"""
from __future__ import annotations

import ast
from pathlib import Path

PORTFOLIO_DIR = Path(__file__).resolve().parents[1]
ALLOCATION_DIR = PORTFOLIO_DIR / "allocation"
API = Path(__file__).resolve().parents[3] / "app" / "main.py"
FRONTEND_SRC = Path(__file__).resolve().parents[3] / "frontend" / "src"


def _imports(path: Path) -> list[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    out: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            out.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            out.append(node.module)
    return out


def _source(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def test_allocation_reuses_canonical_risk_engine_only():
    service = ALLOCATION_DIR / "service.py"
    imports = _imports(service)
    assert any("risk" in name for name in imports)
    source = _source(service)
    # No copied covariance/correlation/ERC/VaR math.
    for forbidden in ("np.cov(", "pd.DataFrame.corr", "def _solve_erc", "def _pairwise_covariance", "np.quantile"):
        assert forbidden not in source


def test_allocation_domain_has_no_second_valuation_engine():
    for path in ALLOCATION_DIR.glob("*.py"):
        source = _source(path)
        assert "ValuationEngine.evaluate" not in source
        assert "class ValuationEngine" not in source


def test_no_kelly_or_expected_alpha_in_allocation_v1():
    for path in ALLOCATION_DIR.glob("*.py"):
        lower = _source(path).lower()
        # Guard against actual Kelly/alpha implementation identifiers. The word
        # "kelly" is allowed in a negative documentation note (e.g. "NOT Kelly").
        for forbidden in ("kelly_fraction", "fractional_kelly", "calculate_kelly", "kelly_weight", "expected_alpha", "alpha_estimate"):
            assert forbidden not in lower


def test_no_composite_opportunity_weights_in_decision_code():
    # The unvalidated weighted factor model must not exist anywhere in the
    # allocation package (opportunity.py, service.py, candidate_service.py).
    for path in ALLOCATION_DIR.glob("*.py"):
        source = _source(path)
        for forbidden in ("QUALITY_WEIGHT", "VALUATION_WEIGHT", "FIT_WEIGHT", "TECHNICAL_WEIGHT",
                          "full_opportunity_score", "WEAK_HOLDING_SCORE", "ROTATION_ADVANTAGE_THRESHOLD"):
            assert forbidden not in source, f"{path.name} still contains {forbidden}"


def test_no_composite_score_in_decision_models_or_bands():
    # ``opportunity_score`` must not be a decision input; the renamed discovery
    # rank is explicitly a research-ordering field.
    models = _source(ALLOCATION_DIR / "models.py")
    assert "opportunity_score" not in models
    assert "discovery_score" in models
    opportunity = _source(ALLOCATION_DIR / "opportunity.py")
    assert "opportunity_score" not in opportunity
    # Decision evidence must expose separate dimensions, never a composite.
    assert '"opportunity_score"' not in opportunity
    for dimension in ('"business_quality_tier"', '"valuation_safety_pp"', '"portfolio_fit"', '"technical_confirmation"'):
        assert dimension in opportunity


def test_decision_logic_is_explicit_gates_not_scores():
    source = _source(ALLOCATION_DIR / "opportunity.py")
    for gate in ("def decide_holding", "def decide_candidate", "def rotation_gates",
                 "def holding_is_rotation_eligible", "quality_tier_rank", "fit_rank"):
        assert gate in source
    # Rotation must require a material valuation-safety delta (governance buffer).
    assert "VALUATION_SAFETY_REPLACEMENT_DELTA" in source


def test_rotation_delta_is_a_documented_governance_default_not_alpha():
    source = _source(ALLOCATION_DIR / "opportunity.py")
    assert "VALUATION_SAFETY_REPLACEMENT_DELTA = 10.0" in source
    assert "never described as" in source or "NOT alpha" in source


def test_explainable_reason_codes_present():
    source = _source(ALLOCATION_DIR / "reason_codes.py")
    for code in ("VALUATION_SAFETY_INSUFFICIENT", "VALUATION_SAFETY_IMPROVES",
                 "PORTFOLIO_FIT_IMPROVES", "PORTFOLIO_FIT_WEAK"):
        assert code in source


def test_allocation_never_auto_executes_or_writes_ledger():
    for path in ALLOCATION_DIR.glob("*.py"):
        source = _source(path)
        assert "append_event" not in source
        assert "apply_event(" not in source
        assert "store.append" not in source
        assert "auto_execute" not in source
        assert "execute_trade" not in source


def test_allocation_domain_has_no_provider_crawl_imports():
    for path in ALLOCATION_DIR.glob("*.py"):
        for name in _imports(path):
            assert "vndirect" not in name.lower()
            assert "tcbs" not in name.lower()
            assert "cafef" not in name.lower()
            assert "market_data" not in name.lower()


def test_allocation_reuses_value_engine_models_not_a_copy():
    # The allocation domain consumes normalized signals; it must not import the
    # valuation engine's model internals (dcf/epv/owner_earnings) nor re-derive
    # required MOS math.
    imports = set()
    for path in ALLOCATION_DIR.glob("*.py"):
        imports.update(_imports(path))
    for forbidden in ("value_engine.dcf", "value_engine.epv", "value_engine.owner_earnings", "value_engine.engine", "value_engine.margin_of_safety"):
        assert forbidden not in imports
    # valuation_safety = actual_mos - required_mos is the derived field.
    source = _source(ALLOCATION_DIR / "eligibility.py")
    assert "actual_mos" in source and "required_mos" in source
    assert "actual_mos - required_mos" in source


def test_risk_endpoint_unchanged_and_still_canonical():
    source = _source(API)
    assert '"/api/portfolio/risk"' in source
    assert "portfolio(require_portfolio_user(qport_session)).risk()" in source
    assert '"/api/portfolio/valuation/{symbol}"' in source
    assert '"/api/portfolio/screener"' in source


def test_allocation_endpoints_are_read_only():
    source = _source(API)
    assert '"/api/portfolio/allocation"' in source
    assert '"/api/portfolio/allocation/simulate"' in source
    simulate_block = source[source.index('"/api/portfolio/allocation/simulate"'):]
    simulate_block = simulate_block[:simulate_block.index("\n@app.")]
    assert "append_event" not in simulate_block
    assert "apply_event" not in simulate_block


def test_frontend_allocation_page_does_not_look_like_a_trading_terminal():
    page = FRONTEND_SRC / "pages" / "AllocationPage.jsx"
    assert page.exists()
    source = _source(page)
    lower = source.lower()
    for trading_term in ("buy_now", "place_order", "limit_order", "market_order", "slippage"):
        assert trading_term not in lower
    assert "Không cần hành động" in source or "NO ACTION REQUIRED" in source


def test_allocation_nav_uses_vietnamese_phan_bo_von():
    nav = FRONTEND_SRC / "components" / "AppNav.jsx"
    assert "Phân bổ vốn" in _source(nav)