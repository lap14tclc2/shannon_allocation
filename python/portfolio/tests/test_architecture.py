from __future__ import annotations

import ast
from pathlib import Path


PORTFOLIO_DIR = Path(__file__).resolve().parents[1]
PYTHON_DIR = PORTFOLIO_DIR.parent


def _imports(path: Path) -> list[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            out.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            out.append(node.module)
    return out


def test_operational_portfolio_package_does_not_import_research_engine():
    offenders = {}
    for path in sorted(PORTFOLIO_DIR.glob("*.py")):
        bad = [name for name in _imports(path) if name == "backtest" or name.startswith("backtest.")]
        if bad:
            offenders[path.name] = bad
    assert offenders == {}


def test_operational_service_has_no_optimizer_apply_or_auto_rebalance_api():
    source = (PORTFOLIO_DIR / "service.py").read_text(encoding="utf-8").lower()
    assert "apply_optimizer" not in source
    assert "auto_rebalance" not in source
    assert "annual_allocation" not in source


def test_primary_entrypoints_are_buy_and_hold_not_optimizer():
    serve = (PYTHON_DIR / "serve.py").read_text(encoding="utf-8")
    main = (PYTHON_DIR / "main.py").read_text(encoding="utf-8")
    assert "from buyhold_server import" in serve
    assert "from portfolio.cli import main" in main
    assert "run_optimizer" not in main


def test_scheduler_does_not_require_transaction_writer():
    source = (PORTFOLIO_DIR / "scheduler.py").read_text(encoding="utf-8")
    assert ".sync_daily()" in source
    assert "append_event" not in source
    assert "append_transaction" not in source
