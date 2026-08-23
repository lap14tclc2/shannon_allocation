from pathlib import Path

REPO_DIR = Path(__file__).resolve().parents[3]
PORTFOLIO_DIR = Path(__file__).resolve().parents[1]
FRONTEND_SRC = REPO_DIR / "frontend" / "src"
PYTHON_DIR = REPO_DIR / "python"


def test_portfolio_dashboard_restores_information_only_risk_assessment():
    source = (FRONTEND_SRC / "pages" / "PortfolioDashboardPage.jsx").read_text(encoding="utf-8")
    assert "Portfolio assessment" in source
    assert "252D volatility" in source
    assert "Current drawdown" in source
    assert "Largest risk contributor" in source
    assert "Daily CVaR 95%" in source
    assert "no BUY/SELL action" in source


def test_holding_rows_expand_to_broker_account_breakdown_from_open_tax_lots():
    source = (FRONTEND_SRC / "pages" / "PortfolioDashboardPage.jsx").read_text(encoding="utf-8")
    styles = (FRONTEND_SRC / "portfolio-insights.css").read_text(encoding="utf-8")
    api = (FRONTEND_SRC / "lib" / "api.js").read_text(encoding="utf-8")

    assert "getPortfolioOperations" in source
    assert "operations?.tax_lots" in source
    assert "groupBrokerSources" in source
    assert "remaining_quantity" in source
    assert "broker_code" in source
    assert "account_id" in source
    assert 'className="holding-expand-button"' in source
    assert "aria-expanded={expanded}" in source
    assert 'className="ranking holding-source-table"' in source
    assert "Cost value" in source
    assert "Market value" in source
    assert "% of symbol" in source
    assert "getPortfolioOperations" in api
    assert ".holding-source-scroll" in styles
    assert "overflow-x: auto" in styles


def test_dividend_ui_shows_latest_and_expands_full_history():
    source = (FRONTEND_SRC / "pages" / "PortfolioDashboardPage.jsx").read_text(encoding="utf-8")
    assert 'className="dividend-symbol-node"' in source
    assert "result.events" in source
    assert "Latest" in source
    assert "Refresh from providers" in source
    assert "loadPositionDividends(false)" in source
    assert "loadPositionDividends(true)" in source


def test_dividend_backend_is_sqlite_first_with_explicit_provider_refresh():
    source = (PORTFOLIO_DIR / "dividend_store.py").read_text(encoding="utf-8")
    server = (PYTHON_DIR / "buyhold_server.py").read_text(encoding="utf-8")
    assert "CREATE TABLE IF NOT EXISTS dividend_events" in source
    assert "CREATE TABLE IF NOT EXISTS dividend_fetch_state" in source
    assert 'origin="SQLITE_CACHE"' in source
    assert "force_refresh" in source
    assert "SqliteDividendService(_portfolio(user).store, stop_on_first_data=False)" in server
    assert 'parse_qs(query).get("refresh")' in server


def test_portfolio_insight_styles_are_loaded_after_mobile_first_layer():
    entry = (FRONTEND_SRC / "entry-client.jsx").read_text(encoding="utf-8")
    assert "import './responsive.css';" in entry
    assert "import './portfolio-insights.css';" in entry
    assert entry.index("import './portfolio-insights.css';") > entry.index("import './responsive.css';")
