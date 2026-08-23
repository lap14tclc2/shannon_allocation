from __future__ import annotations

import ast
from pathlib import Path

PORTFOLIO_DIR = Path(__file__).resolve().parents[1]
PYTHON_DIR = PORTFOLIO_DIR.parent
REPO_DIR = PYTHON_DIR.parent
FRONTEND_SRC = REPO_DIR / "frontend" / "src"


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
    for path in (PYTHON_DIR/"backtest", PYTHON_DIR/"optimize_main.py", PYTHON_DIR/"research_main.py", PYTHON_DIR/"research_legacy_server.py"):
        assert not path.exists()
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
    assert "vn000000" not in source  # no ticker-to-ISIN hard-coded fabrication table


def test_primary_server_exposes_operations_logs_and_no_research_routes():
    source=(PYTHON_DIR/"buyhold_server.py").read_text(encoding="utf-8").lower()
    assert "from portfolio.locale import resolve_locale" in source
    assert "/api/portfolio" in source
    assert '"operations"' in source
    assert '"logs"' in source
    assert "securities/resolve" in source
    assert "corporate-actions" in source
    assert "reconciliation" in source
    assert "/research" not in source
    assert "/optimizer" not in source
    assert "/runs/" not in source
    assert "backtest" not in source


def test_frontend_keeps_advanced_routes_but_hides_them_from_primary_navigation():
    client=(FRONTEND_SRC/"entry-client.jsx").read_text(encoding="utf-8").lower()
    ssr=(FRONTEND_SRC/"ssr-entry.jsx").read_text(encoding="utf-8").lower()
    nav=(FRONTEND_SRC/"components"/"AppNav.jsx").read_text(encoding="utf-8").lower()
    for source in (client, ssr):
        assert "operations" in source
        assert "logs" in source
        assert "risk" in source
        assert "snapshots" in source
        assert "settings" in source
        assert "optimizer" not in source
        assert "research" not in source
    for hidden in ("operations", "logs", "risk", "snapshots", "settings"):
        assert hidden not in nav
    for primary in ("portfolio", "transactions", "performance", "guide"):
        assert primary in nav


def test_transactions_use_simple_history_and_advanced_optional_fields():
    source=(FRONTEND_SRC/"pages"/"TransactionsPage.jsx").read_text(encoding="utf-8")
    assert "window.prompt" not in source
    assert "window.confirm" not in source
    assert "Advanced details" in source
    assert "Broker" in source
    assert "inline-delete" in source
    assert "Save broker" not in source
    assert "Institutional ledger rules" not in source
    assert "Correction audit log" not in source


def test_scheduler_never_writes_transactions_or_corporate_actions():
    source=(PORTFOLIO_DIR/"scheduler.py").read_text(encoding="utf-8")
    assert ".sync_daily()" in source
    assert "append_event" not in source
    assert "post_corporate_action" not in source
