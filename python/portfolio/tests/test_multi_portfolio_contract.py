from __future__ import annotations

from pathlib import Path

import pytest

from portfolio.postgres import (
    _validate_portfolio_schema,
    portfolio_schema,
    user_schema,
)

REPO_DIR = Path(__file__).resolve().parents[3]
APP_MAIN = REPO_DIR / "app" / "main.py"
FRONTEND_SRC = REPO_DIR / "frontend" / "src"


def test_default_portfolio_preserves_the_legacy_user_schema():
    assert user_schema(42) == "qport_user_42"
    assert _validate_portfolio_schema(42, user_schema(42)) == "qport_user_42"


def test_additional_portfolio_schema_is_owned_and_isolated():
    schema = portfolio_schema(42, "abcdef123456")
    assert schema == "qport_user_42_portfolio_abcdef123456"
    assert _validate_portfolio_schema(42, schema) == schema

    with pytest.raises(ValueError):
        _validate_portfolio_schema(7, schema)
    with pytest.raises(ValueError):
        _validate_portfolio_schema(42, "public")


def test_api_exposes_registry_selection_and_active_scope():
    source = APP_MAIN.read_text(encoding="utf-8")
    assert '@app.get("/api/portfolios")' in source
    assert '@app.post("/api/portfolios")' in source
    assert '@app.patch("/api/portfolios/{portfolio_id}")' in source
    assert '@app.post("/api/portfolios/{portfolio_id}/select")' in source
    assert '@app.delete("/api/portfolios/{portfolio_id}")' in source
    assert '"LEGACY_SCHEMA_IS_DEFAULT_PORTFOLIO"' in source
    assert '"POSTGRESQL_SCHEMA_PER_PORTFOLIO"' in source
    assert 'result["portfolio_context"]' in source
    assert "reset_portfolio_schema" in source
    assert 'request.headers.get("X-QPort-Portfolio-Id")' in source
    assert "portfolio_for_user(user_id, requested_id)" in source


def test_frontend_has_wealth_manager_and_global_switcher():
    nav = (FRONTEND_SRC / "components" / "AppNav.jsx").read_text(encoding="utf-8")
    page = (FRONTEND_SRC / "pages" / "PortfoliosPage.jsx").read_text(encoding="utf-8")
    entry = (FRONTEND_SRC / "entry-vercel.jsx").read_text(encoding="utf-8")
    api = (FRONTEND_SRC / "lib" / "api.js").read_text(encoding="utf-8")

    assert "Tài sản đang xem" in nav
    assert "Chuyển danh mục đầu tư" in nav
    assert 'href="/portfolios"' in nav
    assert "Danh mục của bạn" in page
    assert "holdings, cash, transactions, performance và analytics" in page
    assert "Portfolio mặc định giữ nguyên dữ liệu cũ" in page
    assert "case '/portfolios':" in entry
    assert "createPortfolio" in api
    assert "renamePortfolio" in api
    assert "activatePortfolio" in api
    assert "removePortfolio" in api
    assert "'X-QPort-Portfolio-Id': portfolioScopeId" in api
    assert "let portfolioScopeId" in api
