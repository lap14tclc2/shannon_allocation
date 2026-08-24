from pathlib import Path

PORTFOLIO_DIR = Path(__file__).resolve().parents[1]
PYTHON_DIR = PORTFOLIO_DIR.parent
REPO_DIR = PYTHON_DIR.parent
FRONTEND = REPO_DIR / "frontend" / "src"


def test_runtime_service_backfills_long_d1_history_before_incremental_sync():
    source = (PORTFOLIO_DIR / "service.py").read_text(encoding="utf-8")
    assert "risk_lookback_start = today - timedelta(days=550)" in source
    assert "start_date = min(risk_lookback_start, event_start)" in source
    assert '"required_bars": 260' in source
    assert '"risk_ready": count_after >= 260' in source
    assert '"history_status": history_status' in source
    assert '"history": self._market_history_status(symbols)' in source


def test_portfolio_auto_backfill_is_visible_and_non_blocking_to_the_page():
    page = (FRONTEND / "pages" / "PortfolioPage.jsx").read_text(encoding="utf-8")
    indicator = (FRONTEND / "components" / "MarketHistoryIndicator.jsx").read_text(encoding="utf-8")
    assert "MarketHistoryIndicator" in page
    assert "syncPortfolio" in indicator
    assert "D1 HISTORY · SYNCING" in indicator
    assert "D1 HISTORY · READY" in indicator
    assert "localStorage" in indicator
    assert "LEASE_MS" in indicator
    assert "createPortal" in indicator


def test_risk_building_state_hides_low_value_dash_grid():
    source = (FRONTEND / "components" / "PortfolioAssessmentEnhancer.jsx").read_text(encoding="utf-8")
    assert "Market history is building" in source
    assert "Portfolio structure" in source
    assert "Performance history maturity" in source
    assert "evidence-progress" in source
    assert "building ?" in source


def test_readability_layer_sets_accessible_minimums_and_semantic_colors():
    source = (FRONTEND / "accessibility-polish.css").read_text(encoding="utf-8")
    client = (FRONTEND / "entry-vercel.jsx").read_text(encoding="utf-8")
    assert "font-size: 14px" in source
    assert "font-size: 13px" in source
    assert "font-size: 12.5px" in source
    assert "--text-secondary: #b3bcb3" in source
    assert ".market-history-indicator" in source
    assert ".page:has(> .holdings-card) > .holdings-card { order: 30; }" in source
    assert ".page:has(> .holdings-card) > .portfolio-assessment-card { order: 50; }" in source
    assert "accessibility-polish.css" in client
