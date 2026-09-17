from __future__ import annotations

from unittest.mock import patch
import os
import pandas as pd
import pytest

os.environ["DATABASE_URL"] = os.environ.get("DATABASE_URL", "postgresql://qport:qport@127.0.0.1:5432/qport")

from app.main import api_portfolio_business


def test_api_portfolio_business_fetches_live_price():
    """Verify api_portfolio_business fetches live price from provider and calculates MOS based on it."""
    fake_user = {"id": 1, "username": "test_user"}
    fake_df = pd.DataFrame(
        {
            "open": [70.0, 71.0],
            "high": [72.0, 75.0],
            "low": [69.0, 70.0],
            "close": [70.0, 80.0],
            "volume": [100000, 200000],
        },
        index=pd.to_datetime(["2026-09-16", "2026-09-17"]),
    )

    with patch("app.main.require_portfolio_user", return_value=fake_user), \
         patch("portfolio.market_data.AutoMarketData.daily_history_with_source", return_value=(fake_df, "vndirect")):
        res = api_portfolio_business("FPT")
        assert res["ok"] is True
        val = res["canonical_valuation"]
        assert val.get("current_price") == 80000.0
        # If Base IV is ~95282.6, actual MOS % with price 80000 is ~16.04%
        if val.get("base_iv"):
            expected_mos = round((val["base_iv"] - 80000.0) / val["base_iv"] * 100, 2)
            assert round(val.get("actual_mos_pct", 0), 2) == expected_mos
