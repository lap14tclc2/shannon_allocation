from __future__ import annotations

import ast
from pathlib import Path

PORTFOLIO_DIR = Path(__file__).resolve().parents[1]
PYTHON_DIR = PORTFOLIO_DIR.parent
REPO_DIR = PYTHON_DIR.parent
FRONTEND_SRC = REPO_DIR / "frontend" / "src"
API = REPO_DIR / "app" / "main.py"


def _imports(path: Path) -> list[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path)); out=[]
    for node in ast.walk(tree):
        if isinstance(node, ast.Import): out.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module: out.append(node.module)
    return out


def test_portfolio_package_is_self_contained():
    offenders={}
    for path in sorted(PORTFOLIO_DIR.glob("*.py")):
        bad=[name for name in _imports(path) if any(x in name for x in ("backtest","optimizer","research"))]
        if bad: offenders[path.name]=bad
    assert offenders == {}


def test_optimizer_research_stack_is_removed_from_repository():
    # The optimizer/research source is gone; only a stale __pycache__ (compiled
    # .pyc artifacts) may remain under python/backtest, never any source .py.
    for name in ("optimize_main.py", "research_main.py", "research_legacy_server.py"):
        assert not (PYTHON_DIR / name).exists()
    backtest = PYTHON_DIR / "backtest"
    if backtest.exists():
        assert list(backtest.rglob("*.py")) == [], "stale optimizer source .py files remain"
    for name in ("OptimizerListPage.jsx","OptimizerDetailPage.jsx","ResearchPage.jsx","RunPage.jsx","ComboPage.jsx"):
        assert not (FRONTEND_SRC/"pages"/name).exists()


def test_operational_service_has_no_optimizer_or_auto_rebalance_api():
    source=(PORTFOLIO_DIR/"service.py").read_text(encoding="utf-8").lower()
    for forbidden in ("apply_optimizer","auto_rebalance","annual_allocation","run_optimizer"):
        assert forbidden not in source


def test_institutional_book_is_operational_but_not_an_auto_trader():
    institutional=(PORTFOLIO_DIR/"institutional.py").read_text(encoding="utf-8").lower()
    correction=(PORTFOLIO_DIR/"correctable_service.py").read_text(encoding="utf-8").lower()
    assert "institutional_lite_ibor" in institutional
    assert "fifo_tax_lots" in institutional
    assert "reconciliation_runs" in institutional
    assert "corporate_actions" in institutional
    assert "nav_restatements" in institutional
    ca_source=(PORTFOLIO_DIR/"corporate_actions.py").read_text(encoding="utf-8").lower()
    assert "append_event" not in ca_source
    assert "post_corporate_action_receipt" in correction
    assert "user_confirmed_only" in correction


def test_activity_log_is_append_only_and_hash_chained():
    source=(PORTFOLIO_DIR/"activity.py").read_text(encoding="utf-8").lower()
    assert "prev_hash" in source and "record_hash" in source and "sha256" in source
    assert "def append_activity" in source
    assert "def verify_activity_chain" in source
    assert "def update_activity" not in source
    assert "def delete_activity" not in source


def test_isin_is_resolved_not_generated_from_ticker():
    source=(PORTFOLIO_DIR/"security_reference.py").read_text(encoding="utf-8").lower()
    assert "isin" in source
    assert "unresolved" in source
    assert "not mathematically" in source
    assert "vn000000" not in source


def test_vercel_fastapi_exposes_operational_routes_without_research_routes():
    source=API.read_text(encoding="utf-8").lower()
    assert "fastapi" in source
    assert '"/api/portfolio"' in source
    assert '"/api/portfolio/operations"' in source
    assert '"/api/portfolio/logs"' in source
    assert "securities/{symbol}/resolve" in source
    assert "corporate-actions" in source
    assert "reconciliation" in source
    assert "/research" not in source
    assert "/optimizer" not in source
    assert "backtest" not in source


def test_frontend_keeps_advanced_routes_but_hides_them_from_primary_navigation():
    client=(FRONTEND_SRC/"entry-vercel.jsx").read_text(encoding="utf-8").lower()
    nav=(FRONTEND_SRC/"components"/"AppNav.jsx").read_text(encoding="utf-8").lower()
    for route in ("operations", "logs", "risk", "snapshots", "settings"):
        assert f"'/{route}'" in client
    for primary in ("portfolio", "transactions", "performance", "risk"):
        assert primary in nav
    for advanced in ("operations", "logs", "snapshots"):
        assert advanced not in nav
    assert "optimizer" not in client
    assert "research" not in client


def test_transactions_use_simple_history_and_advanced_optional_fields():
    source=(FRONTEND_SRC/"pages"/"TransactionsPage.jsx").read_text(encoding="utf-8")
    assert "window.prompt" not in source
    assert "Thông tin CTCK & chi phí" in source
    assert "transaction-advanced" in source
    assert "CTCK" in source
    assert "broker_code" in source
    assert "discardPortfolioTransaction" in source
    assert "Xác nhận loại bỏ" in source
    assert "Save broker" not in source
    assert "Institutional ledger rules" not in source
    assert "Correction audit log" not in source


def test_runtime_cron_never_generates_model_driven_trades():
    source=API.read_text(encoding="utf-8")
    cron=source[source.index('def cron_daily_sync'):]
    assert "sync_daily" in cron
    assert "append_event" not in cron
    assert "post_corporate_action" not in cron
