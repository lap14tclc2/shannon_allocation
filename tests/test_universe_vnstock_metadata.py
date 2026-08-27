from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "python"))

from portfolio import finance_catalog  # noqa: E402


def test_merge_vnstock_universe_uses_exchange_and_top_level_icb_industry():
    rows = finance_catalog._merge_vnstock_universe_rows(
        [
            {"symbol": "VNM", "organ_name": "Vinamilk", "exchange": "HOSE", "type": "stock"},
            {"symbol": "AAA", "organ_name": "An Phat", "exchange": "HNX", "type": "stock"},
        ],
        [
            {"symbol": "VNM", "icb_level": 3, "icb_name": "Sản phẩm thực phẩm"},
            {"symbol": "VNM", "icb_level": 1, "icb_name": "Hàng tiêu dùng"},
        ],
    )

    normalized = [finance_catalog._normalize_universe_row(row) for row in rows]

    assert normalized[0]["exchange"] == "HOSE"
    assert normalized[0]["company_name"] == "Vinamilk"
    assert normalized[0]["industry"] == "Hàng tiêu dùng"
    assert normalized[1]["exchange"] == "HNX"
    assert normalized[1]["industry"] == "UNKNOWN"


def test_universe_sync_contains_no_tcbs_overview_helpers():
    assert not hasattr(finance_catalog, "_load_tcbs_overview")
    assert not hasattr(finance_catalog, "_tcbs_overview_headers")
