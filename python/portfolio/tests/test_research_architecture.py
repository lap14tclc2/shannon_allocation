"""Research architecture boundaries (T09-T13 audit).

Guards:
- research code never mutates the ledger or auto-trades;
- allocation V1 remains independent of research results;
- no expected_alpha / Kelly in production allocation;
- no random train/test split for time-series;
- no fetched_at-as-publication shortcut;
- research results are never exposed as production BUY/SELL.
"""
from __future__ import annotations

import ast
from pathlib import Path

PORTFOLIO_DIR = Path(__file__).resolve().parents[1]
RESEARCH_DIR = PORTFOLIO_DIR / "research"
ALLOCATION_DIR = PORTFOLIO_DIR / "allocation"
API = Path(__file__).resolve().parents[3] / "app" / "main.py"


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


def test_research_never_mutates_ledger():
    for path in RESEARCH_DIR.glob("*.py"):
        source = _source(path)
        assert "append_event" not in source
        assert "apply_event(" not in source
        assert "store.append" not in source
        assert "append_ledger" not in source


def test_research_never_auto_trades():
    for path in RESEARCH_DIR.glob("*.py"):
        source = _source(path).lower()
        for forbidden in ("execute_trade", "auto_trade", "place_order", "create_transaction"):
            assert forbidden not in source


def test_research_does_not_import_production_ledger_services():
    imports = set()
    for path in RESEARCH_DIR.glob("*.py"):
        imports.update(_imports(path))
    for forbidden in ("portfolio.accounting", "portfolio.correctable_service", "portfolio.automated_service"):
        assert forbidden not in imports


def test_no_expected_alpha_or_kelly_in_research_and_allocation():
    for folder in (RESEARCH_DIR, ALLOCATION_DIR):
        for path in folder.glob("*.py"):
            lower = _source(path).lower()
            for forbidden in ("expected_alpha", "kelly_fraction", "fractional_kelly", "calculate_kelly"):
                assert forbidden not in lower


def test_no_expected_alpha_exposed_to_production_allocation_api():
    api = _source(API)
    # Research endpoints must not be production recommendation endpoints.
    assert "expected_alpha" not in api.lower()
    assert "/research" not in api


def test_research_api_is_not_a_user_buy_sell_endpoint():
    # The research CLI is the only interface; no route in main.py.
    api = _source(API)
    assert "research" not in api


def test_allocation_v1_does_not_depend_on_research():
    imports = set()
    for path in ALLOCATION_DIR.glob("*.py"):
        imports.update(_imports(path))
    for forbidden in ("portfolio.research", "research.benchmark", "research.factors", "research.validation"):
        assert forbidden not in imports
    api = _source(API)
    assert "from portfolio.research" not in api and "portfolio.research" not in api


def test_no_random_train_test_split_for_time_series():
    source = _source(RESEARCH_DIR / "validation.py") + _source(RESEARCH_DIR / "walk_forward.py")
    lower = source.lower()
    assert "shuffle" not in lower
    assert "train_test_split" not in lower
    assert "random.split" not in lower
    assert "walk_forward" in lower
    assert "sealed" in lower


def test_no_fetched_at_as_publication_shortcut():
    source = _source(RESEARCH_DIR / "pit.py")
    assert "observed_at" in source or "fetched_at" in source
    # The PIT module must explicitly never use fetched_at as availability.
    assert "never" in source.lower() or "NOT" in source
    assert "available_from" in source


def test_benchmark_uses_index_points_not_vnd_scaling():
    source = _source(RESEARCH_DIR / "benchmark.py")
    assert "canonical_vnd_price" not in source
    assert "points" in source.lower()


def test_research_package_structure_matches_plan():
    expected = {"__init__.py", "pit.py", "benchmark.py", "factors.py", "snapshots.py",
                "outcomes.py", "validation.py", "walk_forward.py"}
    actual = {path.name for path in RESEARCH_DIR.glob("*.py")}
    assert expected.issubset(actual)


def test_factor_snapshots_are_versioned_and_hashed():
    source = _source(RESEARCH_DIR / "snapshots.py")
    assert "factor_version" in source
    assert "source_hash" in source
    assert "sha256" in source or "hashlib" in source


def test_sealed_oos_protection_is_enforced_in_code():
    source = _source(RESEARCH_DIR / "walk_forward.py") + _source(RESEARCH_DIR / "validation.py")
    assert "assert_not_sealed" in source
    assert "sealed" in source.lower()