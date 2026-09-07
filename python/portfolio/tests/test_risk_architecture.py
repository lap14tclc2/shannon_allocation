"""Architecture tests verifying strict separation of Risk diagnostic engine from Allocation decisions and ledger mutations."""

import ast
import inspect
import portfolio.risk
import portfolio.risk_warnings


def test_risk_warnings_module_dependencies():
    """Risk Warning module must depend on canonical risk outputs, but must NOT depend on allocation, transaction execution, or ledger mutation modules."""
    source_warnings = inspect.getsource(portfolio.risk_warnings)
    tree = ast.parse(source_warnings)

    imported_modules = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imported_modules.append(alias.name)
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                imported_modules.append(node.module)

    forbidden_modules = ["portfolio.allocation", "portfolio.execution", "portfolio.ledger", "portfolio.opportunity"]

    for imported in imported_modules:
        for forbidden in forbidden_modules:
            assert not imported.startswith(forbidden), (
                f"Risk warning engine violates architectural isolation! Found forbidden import '{imported}'."
            )


def test_risk_module_isolation():
    """Risk module remains diagnostic/advisory and must not depend on allocation execution."""
    source_risk = inspect.getsource(portfolio.risk)

    forbidden = ["portfolio.allocation", "allocation_service", "create_order", "mutate"]
    for item in forbidden:
        assert item not in source_risk, (
            f"Risk engine violates architectural isolation! Found reference to '{item}'."
        )

