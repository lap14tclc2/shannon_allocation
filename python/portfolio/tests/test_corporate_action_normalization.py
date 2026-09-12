"""Corporate Action & Share-Basis Normalization Test Suite (TASK-152).

Covers all 15 required test scenarios:
1. No corporate action
2. 2:1 stock split
3. Reverse split (1:2)
4. Bonus shares (20%)
5. Dividend before split
6. Dividend after split
7. Historical EPS normalization
8. Historical DPS normalization
9. Historical price normalization
10. No double price adjustment
11. No double dividend counting
12. Valuation consistency (Equity Value vs IV per share)
13. Portfolio position consistency (total cost basis invariant)
14. Current price remains current basis
15. Historical CAGR unaffected by split
"""
from __future__ import annotations

from decimal import Decimal
import pytest

from portfolio.corporate_action_normalizer import (
    CORPORATE_ACTION_VIETNAMESE,
    CorporateActionEvent,
    CorporateActionType,
    adjust_position_for_corporate_action,
    calculate_cumulative_multiplier,
    normalize_historical_financial_series,
    normalize_per_share_metric,
    normalize_price_series,
    reconcile_retained_earnings,
    verify_no_dividend_double_counting,
)
from portfolio.value_engine.dcf import DCFValuationModel
from portfolio.value_engine.models import ScenarioType


# 1. No corporate action
def test_1_no_corporate_action():
    events = []
    mult = calculate_cumulative_multiplier(events, "2020-01-01", "2024-01-01")
    assert mult == 1.0

    fin_hist = [
        {"fiscal_year": 2020, "net_profit": 1_000_000_000, "shares_outstanding": 100_000_000},
        {"fiscal_year": 2024, "net_profit": 2_000_000_000, "shares_outstanding": 100_000_000},
    ]
    norm = normalize_historical_financial_series(fin_hist)
    assert norm[0]["eps_normalized"] == 10.0
    assert norm[1]["eps_normalized"] == 20.0


# 2. 2:1 stock split
def test_2_stock_split_2_to_1():
    action = CorporateActionEvent(
        symbol="ABC",
        action_type=CorporateActionType.STOCK_SPLIT.value,
        effective_date="2022-06-15",
        split_factor=2.0,
    )
    assert action.multiplier == 2.0
    assert action.is_non_economic is True

    mult = calculate_cumulative_multiplier([action], "2020-01-01", "2024-01-01")
    assert mult == 2.0


# 3. Reverse split (1:2)
def test_3_reverse_split():
    action = CorporateActionEvent(
        symbol="XYZ",
        action_type=CorporateActionType.REVERSE_SPLIT.value,
        effective_date="2023-01-01",
        split_factor=0.5,
    )
    assert action.multiplier == 0.5
    assert action.is_non_economic is True

    mult = calculate_cumulative_multiplier([action], "2020-01-01", "2024-01-01")
    assert mult == 0.5


# 4. Bonus shares (20%)
def test_4_bonus_shares():
    action = CorporateActionEvent(
        symbol="FPT",
        action_type=CorporateActionType.BONUS_SHARE.value,
        effective_date="2023-05-10",
        stock_ratio=0.20,
    )
    assert action.multiplier == 1.20
    assert action.is_non_economic is True


# 5. Dividend before split
def test_5_dividend_before_split():
    """Cash dividend before split: DPS on current share basis = Raw DPS / Multiplier."""
    # Pre-split: 100M shares, 2,000 VND DPS -> Total cash = 200B VND
    # Post-split 2:1: 200M shares -> Normalized DPS = 200B / 200M = 1,000 VND
    fin_hist = [
        {"fiscal_year": 2021, "shares_outstanding": 100_000_000, "dps": 2000.0, "net_profit": 500_000_000_000},
        {"fiscal_year": 2024, "shares_outstanding": 200_000_000, "dps": 1500.0, "net_profit": 800_000_000_000},
    ]
    norm = normalize_historical_financial_series(fin_hist, current_shares=200_000_000)
    assert norm[0]["dps_normalized"] == 1000.0
    assert norm[1]["dps_normalized"] == 1500.0

    # Total dividend economics is preserved: 1,000 * 200M = 200B == 2,000 * 100M
    assert norm[0]["dps_normalized"] * 200_000_000 == 200_000_000_000.0


# 6. Dividend after split
def test_6_dividend_after_split():
    """Cash dividend declared after split is already on the current share basis."""
    action = CorporateActionEvent(
        symbol="ACB",
        action_type=CorporateActionType.STOCK_SPLIT.value,
        effective_date="2022-01-01",
        split_factor=2.0,
    )
    # Action happened in 2022, dividend declared in 2023
    mult = calculate_cumulative_multiplier([action], "2023-01-01", "2024-01-01")
    assert mult == 1.0


# 7. Historical EPS normalization
def test_7_historical_eps_normalization():
    # In 2015: 100M shares, 1,000B NP -> raw EPS = 10,000
    # In 2025: 400M shares (after splits), 4,000B NP -> raw EPS = 10,000
    # Raw EPS shows 0% growth despite 4x business growth!
    # Normalized EPS on 400M share basis: 2015 EPS = 2,500, 2025 EPS = 10,000 (4x growth!)
    fin_hist = [
        {"fiscal_year": 2015, "shares_outstanding": 100_000_000, "net_profit": 1_000_000_000_000},
        {"fiscal_year": 2025, "shares_outstanding": 400_000_000, "net_profit": 4_000_000_000_000},
    ]
    norm = normalize_historical_financial_series(fin_hist, current_shares=400_000_000)
    assert norm[0]["raw_eps"] == 10000.0
    assert norm[0]["eps_normalized"] == 2500.0
    assert norm[1]["eps_normalized"] == 10000.0
    assert norm[1]["eps_normalized"] / norm[0]["eps_normalized"] == 4.0


# 8. Historical DPS normalization
def test_8_historical_dps_normalization():
    fin_hist = [
        {"fiscal_year": 2020, "shares_outstanding": 50_000_000, "cash_dividend_total": 100_000_000_000},
        {"fiscal_year": 2024, "shares_outstanding": 100_000_000, "cash_dividend_total": 250_000_000_000},
    ]
    norm = normalize_historical_financial_series(fin_hist, current_shares=100_000_000)
    assert norm[0]["dps_normalized"] == 1000.0
    assert norm[1]["dps_normalized"] == 2500.0
    # Total cash payout invariant
    assert norm[0]["dps_normalized"] * 100_000_000 == 100_000_000_000.0


# 9. Historical price normalization (raw price input)
def test_9_historical_price_normalization_raw():
    actions = [
        CorporateActionEvent(symbol="FPT", action_type="STOCK_SPLIT", effective_date="2022-01-01", split_factor=2.0)
    ]
    raw_prices = [
        {"trading_date": "2020-01-01", "close": 80000.0},
        {"trading_date": "2024-01-01", "close": 90000.0},
    ]
    # Provider unadjusted -> apply split backwards
    norm = normalize_price_series(raw_prices, actions, is_provider_adjusted=False)
    assert norm[0]["normalized_close"] == 40000.0
    assert norm[1]["normalized_close"] == 90000.0


# 10. No double price adjustment (provider already adjusted)
def test_10_no_double_price_adjustment():
    actions = [
        CorporateActionEvent(symbol="FPT", action_type="STOCK_SPLIT", effective_date="2022-01-01", split_factor=2.0)
    ]
    # VNDIRECT / VNSTOCK dchart API already returns split-adjusted prices
    provider_prices = [
        {"trading_date": "2020-01-01", "close": 40000.0},
        {"trading_date": "2024-01-01", "close": 90000.0},
    ]
    norm = normalize_price_series(provider_prices, actions, is_provider_adjusted=True)
    assert norm[0]["normalized_close"] == 40000.0
    assert norm[1]["normalized_close"] == 90000.0
    assert norm[0]["adjustment_source"] == "PROVIDER_ADJUSTED"


# 11. No double dividend counting test
def test_11_dividend_double_count_test():
    audit_dcf = verify_no_dividend_double_counting(
        valuation_model_name="OWNER_EARNINGS_DCF",
        valuation_inputs={"cashflow_basis": "NET_INCOME_OWNER_EARNINGS", "add_dividends_to_dcf": False},
    )
    assert audit_dcf["ok"] is True
    assert audit_dcf["double_counting_detected"] is False

    audit_bad = verify_no_dividend_double_counting(
        valuation_model_name="OWNER_EARNINGS_DCF",
        valuation_inputs={"cashflow_basis": "NET_INCOME_OWNER_EARNINGS", "add_dividends_to_dcf": True},
    )
    assert audit_bad["ok"] is False
    assert audit_bad["double_counting_detected"] is True


# 12. Valuation consistency (Equity Value vs IV per share)
def test_12_valuation_consistency_across_split():
    """A 2:1 stock split doubles shares and halves IV per share; Equity Value is invariant."""
    base_oe = Decimal("1000000000000")  # 1,000B VND
    discount_rate = Decimal("0.11")
    growth_rate = Decimal("0.10")

    # Before split: 100M shares
    scen_before = DCFValuationModel.calculate_scenario(
        base_owner_earnings=base_oe,
        shares_outstanding=Decimal("100000000"),
        net_debt=Decimal("0"),
        scenario_type=ScenarioType.BASE,
        discount_rate=discount_rate,
        growth_rate=growth_rate,
    )

    # After split 2:1: 200M shares
    scen_after = DCFValuationModel.calculate_scenario(
        base_owner_earnings=base_oe,
        shares_outstanding=Decimal("200000000"),
        net_debt=Decimal("0"),
        scenario_type=ScenarioType.BASE,
        discount_rate=discount_rate,
        growth_rate=growth_rate,
    )

    # Equity value must be identical
    assert scen_before.equity_value == scen_after.equity_value
    # IV per share must be exactly half
    assert scen_after.intrinsic_value_per_share == scen_before.intrinsic_value_per_share / Decimal("2")


# 13. Portfolio position consistency
def test_13_portfolio_position_consistency():
    action = CorporateActionEvent(
        symbol="FPT",
        action_type=CorporateActionType.STOCK_SPLIT.value,
        effective_date="2026-09-12",
        split_factor=2.0,
    )
    old_shares = 3000.0
    old_cost = 80000.0
    new_shares, new_cost, total_invested = adjust_position_for_corporate_action(
        old_shares, old_cost, action
    )
    assert new_shares == 6000.0
    assert new_cost == 40000.0
    assert total_invested == 240_000_000.0
    assert total_invested == old_shares * old_cost


# 14. Current price remains current basis
def test_14_current_price_remains_current_basis():
    prices = [
        {"trading_date": "2020-01-01", "close": 30000.0},
        {"trading_date": "2026-09-12", "close": 120000.0},
    ]
    norm = normalize_price_series(prices, is_provider_adjusted=True)
    assert norm[-1]["normalized_close"] == 120000.0


# 15. Historical CAGR unaffected by split
def test_15_historical_cagr_unaffected_by_split():
    # Net profit grows 10x over 10 years (100B -> 1,000B)
    # Shares split 4x over 10 years (10M -> 40M)
    fin_hist = [
        {"fiscal_year": 2015, "net_profit": 100_000_000_000, "shares_outstanding": 10_000_000},
        {"fiscal_year": 2025, "net_profit": 1_000_000_000_000, "shares_outstanding": 40_000_000},
    ]
    norm = normalize_historical_financial_series(fin_hist, current_shares=40_000_000)

    pat_cagr = (norm[1]["net_profit"] / norm[0]["net_profit"]) ** (1.0 / 10) - 1.0
    eps_norm_cagr = (norm[1]["eps_normalized"] / norm[0]["eps_normalized"]) ** (1.0 / 10) - 1.0

    assert abs(pat_cagr - eps_norm_cagr) < 1e-6
    # Raw EPS would erroneously show 2.5x growth instead of 10x
    raw_eps_growth = norm[1]["raw_eps"] / norm[0]["raw_eps"]
    assert raw_eps_growth == 2.5
    assert norm[1]["eps_normalized"] / norm[0]["eps_normalized"] == 10.0


# 16. Retained earnings clean surplus reconciliation
def test_16_retained_earnings_reconciliation():
    reconciled = reconcile_retained_earnings(
        beginning_re=10_000_000_000.0,
        net_income=3_000_000_000.0,
        cash_dividends=1_000_000_000.0,
        ending_re=12_000_000_000.0,
    )
    assert reconciled["is_reconciled"] is True
    assert reconciled["status"] == "RECONCILED"
    assert "khớp chuẩn mực" in reconciled["explanation"]


# 17. Vietnamese semantic mapping
def test_17_vietnamese_semantic_mapping():
    assert CORPORATE_ACTION_VIETNAMESE["STOCK_SPLIT"] == "Chia cổ phiếu"
    assert CORPORATE_ACTION_VIETNAMESE["BONUS_SHARE"] == "Cổ phiếu thưởng"
    assert CORPORATE_ACTION_VIETNAMESE["CASH_DIVIDEND"] == "Cổ tức tiền mặt"
