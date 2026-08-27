from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "python"))

from portfolio.finance_catalog import _normalize_universe_row  # noqa: E402


def test_normalize_vnstock_exchange_aliases():
    assert _normalize_universe_row({"symbol": "abc", "exchangeCode": "hsx"})["exchange"] == "HOSE"
    assert _normalize_universe_row({"symbol": "abc", "comGroupCode": "HNX"})["exchange"] == "HNX"
    assert _normalize_universe_row({"symbol": "abc", "market": "UPCOM"})["exchange"] == "UPCOM"


def test_normalize_vnstock_reports_unrecognized_exchange():
    row = _normalize_universe_row({"symbol": "abc", "comGroupCode": "VN30"})
    assert row["exchange"] == "UNKNOWN"
    assert row["unrecognized_exchange"] is True


def test_normalize_vnstock_uses_industry_schema_variants():
    row = _normalize_universe_row({"symbol": "abc", "icbName2": "Financial Services"})
    assert row["industry"] == "Financial Services"
    assert row["industry_source"] == "icbname2"
