from __future__ import annotations

import ast
from pathlib import Path


PORTFOLIO_DIR = Path(__file__).resolve().parents[1]
PYTHON_DIR = PORTFOLIO_DIR.parent
REPO_DIR = PYTHON_DIR.parent
FRONTEND_SRC = REPO_DIR / "frontend" / "src"


def _imports(path: Path) -> list[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            out.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            out.append(node.module)
    return out


def test_portfolio_package_is_self_contained():
    offenders = {}
    for path in sorted(PORTFOLIO_DIR.glob("*.py")):
        bad = [name for name in _imports(path) if "backtest" in name or "optimizer" in name or "research" in name]
        if bad:
            offenders[path.name] = bad
    assert offenders == {}


def test_optimizer_research_stack_is_removed_from_repository():
    assert not (PYTHON_DIR / "backtest").exists()
    assert not (PYTHON_DIR / "optimize_main.py").exists()
    assert not (PYTHON_DIR / "research_main.py").exists()
    assert not (PYTHON_DIR / "research_legacy_server.py").exists()
    for name in ("OptimizerListPage.jsx", "OptimizerDetailPage.jsx", "ResearchPage.jsx", "RunPage.jsx", "ComboPage.jsx"):
        assert not (FRONTEND_SRC / "pages" / name).exists()


def test_operational_service_has_no_auto_trading_api():
    source = (PORTFOLIO_DIR / "service.py").read_text(encoding="utf-8").lower()
    for forbidden in ("apply_optimizer", "auto_rebalance", "annual_allocation", "run_optimizer"):
        assert forbidden not in source


def test_primary_server_exposes_portfolio_routes_only():
    source = (PYTHON_DIR / "buyhold_server.py").read_text(encoding="utf-8").lower()
    assert "from portfolio.locale import resolve_locale" in source
    assert '"/guide": "guide"' in source
    assert "/api/portfolio" in source
    assert "/research" not in source
    assert "/optimizer" not in source
    assert "/runs/" not in source
    assert "backtest" not in source


def test_frontend_runtime_has_no_research_or_optimizer_pages():
    client = (FRONTEND_SRC / "entry-client.jsx").read_text(encoding="utf-8").lower()
    ssr = (FRONTEND_SRC / "ssr-entry.jsx").read_text(encoding="utf-8").lower()
    nav = (FRONTEND_SRC / "components" / "AppNav.jsx").read_text(encoding="utf-8").lower()
    for source in (client, ssr, nav):
        assert "optimizer" not in source
        assert "research" not in source


def test_scheduler_never_writes_transactions():
    source = (PORTFOLIO_DIR / "scheduler.py").read_text(encoding="utf-8")
    assert ".sync_daily()" in source
    assert "append_event" not in source
    assert "append_transaction" not in source
