from python.portfolio.finance_catalog import _normalize_universe_row, _universe_quality


def test_normalize_universe_maps_vnstock_schema_variants():
    row = _normalize_universe_row({
        "ticker": "abc",
        "comGroupCode": "HOSE",
        "organName": "ABC Corporation",
        "icbName": "Banks",
    })
    assert row["symbol"] == "ABC"
    assert row["exchange"] == "HOSE"
    assert row["company_name"] == "ABC Corporation"
    assert row["industry"] == "Banks"
    assert row["missing_exchange"] is False
    assert row["missing_industry"] is False


def test_normalize_universe_retains_symbol_when_optional_metadata_is_missing():
    row = _normalize_universe_row({"symbol": "xyz"})
    assert row["symbol"] == "XYZ"
    assert row["exchange"] == "UNKNOWN"
    assert row["industry"] == "UNKNOWN"
    assert row["missing_exchange"] is True
    assert row["missing_industry"] is True


def test_universe_quality_reports_missing_and_duplicate_metadata():
    rows = [{"symbol": "ABC"}, {"symbol": "ABC"}, {"symbol": None}]
    normalized = [_normalize_universe_row(row) for row in rows]
    assert _universe_quality(rows, normalized) == {
        "received": 3,
        "valid_symbols": 1,
        "duplicate_symbols": 1,
        "missing_symbol": 1,
        "unknown_exchange": 3,
        "missing_industry": 3,
    }
