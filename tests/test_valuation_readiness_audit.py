from pathlib import Path


def test_readiness_contract_requires_complete_fy_inputs_and_blocks_quarters():
    source = Path("python/portfolio/finance_catalog.py").read_text(encoding="utf-8")
    engine = Path("python/portfolio/value_engine/engine.py").read_text(encoding="utf-8")
    assert "VALUE_ENGINE_REQUIRED_FACTS" in source
    assert "valuation_readiness_audit" in source
    assert 'row.get("period_type") == "FY"' in source
    assert "FINANCE_DATA_NOT_READY" in source
    assert "TTM_REQUIRED" in engine
    assert 'Decimal("1000000000000")' not in engine
    assert "OWNER_EARNINGS_NON_POSITIVE" in engine
