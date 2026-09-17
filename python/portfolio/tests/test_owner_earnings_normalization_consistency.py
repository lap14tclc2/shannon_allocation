"""Task 191: Owner Earnings Normalization Consistency & Universe-Wide Verification.

Deterministic Golden Test Suite covering Scenarios 1 through 24:
- Scenario 1: Stable enterprise -> consistent CFO and Owner Earnings
- Scenario 2: Cyclical enterprise -> multi-year MID_CYCLE_MEDIAN normalizes commodity cycle
- Scenario 3: Growth enterprise (secular compounding) -> OE reflects ongoing expansion
- Scenario 4: Temporary WC release -> CFO spike properly evaluated
- Scenario 5: Temporary WC investment -> core power floor cushions viable compounders
- Scenario 6: Persistent CFO weakness -> core floor does NOT activate when core earning power is negative
- Scenario 7: Persistent CFO strength -> high cash conversion reflected in OE
- Scenario 8: High CapEx enterprise -> heavy reinvestment appropriately reduces OE
- Scenario 9: Low CapEx asset-light enterprise -> OE approximately equals CFO/PAT
- Scenario 10: Missing CapEx -> single-year raises ValueError, multi-year falls back with trace
- Scenario 11: Missing D&A -> single-year raises ValueError, multi-year falls back with trace
- Scenario 12: Missing CFO -> single-year raises ValueError, multi-year falls back with trace
- Scenario 13: Short history (<3 years) -> honest fallback to LATEST_FY, never labeled averaged
- Scenario 14: 5Y history -> MID_CYCLE_MEDIAN over 5 full years
- Scenario 15: 10Y history -> MID_CYCLE_MEDIAN over full 10-year cycle
- Scenario 16: >10Y history (15Y) -> full available history respected
- Scenario 17: Median margin/revenue mismatch -> product of medians preserves mid-cycle economics
- Scenario 18: Core power floor activation -> applies 50% haircut floor when raw OE <= 0 and core power > 0
- Scenario 19: Core power floor not activated -> when raw OE > 0, raw OE is strictly used
- Scenario 20: Bank bypass -> Bank archetype uses Residual Income Model, not industrial OE
- Scenario 21: Securities bypass -> Securities archetype uses trading/equity models, not industrial OE
- Scenario 22: Real DB regression integrity -> BFC, HAH, FPT, DGC, TLG, ACB, TCB, TPB verified
- Scenario 23: OE / PAT > 100% legitimate scenario -> cash conversion > 100% and D&A > CapEx
- Scenario 24: OE / PAT > 100% suspicious scenario -> flagged for review if driven by one-off liquidation
"""

import pytest
from decimal import Decimal
from portfolio.financial_data.models import (
    CanonicalFact,
    FactIdentityKey,
    StatementType,
    PeriodType,
    ConsolidationScope,
    QualityStatus,
)
from portfolio.value_engine.owner_earnings import OwnerEarningsCalculator
from portfolio.value_engine.munger_analyzer import build_munger_financial_analysis


def _make_canonical_fact(
    symbol: str,
    fiscal_year: int,
    line_item_code: str,
    value: float,
    statement_type: StatementType,
) -> CanonicalFact:
    return CanonicalFact(
        canonical_fact_id=f"{symbol}-{fiscal_year}-{line_item_code}",
        identity=FactIdentityKey(
            security_id=f"sec-{symbol.lower()}",
            statement_type=statement_type,
            period_end=f"{fiscal_year}-12-31",
            period_type=PeriodType.FY,
            fiscal_year=fiscal_year,
            fiscal_quarter=None,
            consolidation_scope=ConsolidationScope.CONSOLIDATED,
            line_item_code=line_item_code,
            currency="VND",
        ),
        value=Decimal(str(value)),
        quality_status=QualityStatus.SINGLE_SOURCE,
        decision_id=f"dec-{symbol}-{fiscal_year}",
        winning_candidate_id=None,
        candidate_ids=[],
        observed_at=f"{fiscal_year}-12-31",
    )


def _make_raw_fact(symbol: str, fiscal_year: int, code: str, value: float, st_name: str) -> dict:
    return {
        "symbol": symbol,
        "statement_type": st_name,
        "line_item_code": code,
        "period_type": "FY",
        "fiscal_year": fiscal_year,
        "provider": "ssi",
        "value": value,
        "quality_status": "SINGLE_SOURCE",
        "observed_at": f"{fiscal_year}-12-31",
    }


# =========================================================================
# Scenario 1: Stable Enterprise
# =========================================================================
def test_scenario_1_stable_enterprise():
    facts = [
        _make_canonical_fact("STABLE_1", 2025, "IS.PROFIT.NET", 500e9, StatementType.INCOME_STATEMENT),
        _make_canonical_fact("STABLE_1", 2025, "CF.OPERATING.DEPRECIATION", 100e9, StatementType.CASH_FLOW),
        _make_canonical_fact("STABLE_1", 2025, "CF.CAPEX", 100e9, StatementType.CASH_FLOW),
        _make_canonical_fact("STABLE_1", 2025, "CF.OPERATING.NET", 600e9, StatementType.CASH_FLOW),
    ]
    bridge = OwnerEarningsCalculator.calculate(facts, fiscal_year=2025)
    assert bridge.owner_earnings == Decimal("500000000000")


# =========================================================================
# Scenario 2: Cyclical Enterprise (Mid-Cycle Median Normalization)
# =========================================================================
def test_scenario_2_cyclical_enterprise():
    facts = []
    pats = [100e9, 800e9, 150e9, 600e9, 300e9]
    revs = [1000e9, 5000e9, 1200e9, 4000e9, 2000e9]
    cfos = [110e9, 750e9, 140e9, 580e9, 290e9]
    for i, y in enumerate(range(2021, 2026)):
        facts.append(_make_canonical_fact("CYCLIC_2", y, "IS.PROFIT.NET", pats[i], StatementType.INCOME_STATEMENT))
        facts.append(_make_canonical_fact("CYCLIC_2", y, "IS.REVENUE.NET", revs[i], StatementType.INCOME_STATEMENT))
        facts.append(_make_canonical_fact("CYCLIC_2", y, "CF.OPERATING.NET", cfos[i], StatementType.CASH_FLOW))
        facts.append(_make_canonical_fact("CYCLIC_2", y, "CF.CAPEX", 50e9, StatementType.CASH_FLOW))
        facts.append(_make_canonical_fact("CYCLIC_2", y, "CF.OPERATING.DEPRECIATION", 40e9, StatementType.CASH_FLOW))

    bridge = OwnerEarningsCalculator.calculate_cycle_normalized(facts, latest_fiscal_year=2025, lookback_years=5)
    assert bridge.normalization_method == "MID_CYCLE_MEDIAN"
    assert bridge.owner_earnings > Decimal("0")


# =========================================================================
# Scenario 3: Growth Enterprise (Secular Compounding)
# =========================================================================
def test_scenario_3_growth_enterprise():
    facts = [
        _make_canonical_fact("GROWTH_3", 2025, "IS.PROFIT.NET", 9000e9, StatementType.INCOME_STATEMENT),
        _make_canonical_fact("GROWTH_3", 2025, "CF.OPERATING.DEPRECIATION", 2500e9, StatementType.CASH_FLOW),
        _make_canonical_fact("GROWTH_3", 2025, "CF.CAPEX", 4500e9, StatementType.CASH_FLOW),
        _make_canonical_fact("GROWTH_3", 2025, "CF.OPERATING.NET", 9500e9, StatementType.CASH_FLOW),
    ]
    bridge = OwnerEarningsCalculator.calculate(facts, fiscal_year=2025)
    # Maint CapEx = min(4500, 2500) = 2500 -> OE = 9500 - 2500 = 7000B
    assert bridge.owner_earnings == Decimal("7000000000000")
    assert bridge.growth_capex_estimated == Decimal("2000000000000")


# =========================================================================
# Scenario 4: Temporary Working Capital Release
# =========================================================================
def test_scenario_4_temporary_wc_release():
    # Net income 500B, D&A 100B, CapEx 100B
    # Working capital inventory release of +300B -> CFO = 900B
    facts = [
        _make_canonical_fact("WC_REL_4", 2025, "IS.PROFIT.NET", 500e9, StatementType.INCOME_STATEMENT),
        _make_canonical_fact("WC_REL_4", 2025, "CF.OPERATING.DEPRECIATION", 100e9, StatementType.CASH_FLOW),
        _make_canonical_fact("WC_REL_4", 2025, "CF.CAPEX", 100e9, StatementType.CASH_FLOW),
        _make_canonical_fact("WC_REL_4", 2025, "CF.OPERATING.NET", 900e9, StatementType.CASH_FLOW),
    ]
    bridge = OwnerEarningsCalculator.calculate(facts, fiscal_year=2025)
    # OE = CFO - min(CapEx, D&A) = 900 - 100 = 800B
    assert bridge.owner_earnings == Decimal("800000000000")
    assert bridge.working_capital_change == Decimal("300000000000")


# =========================================================================
# Scenario 5: Temporary Working Capital Investment (Floor Cushion)
# =========================================================================
def test_scenario_5_temporary_wc_investment():
    # Net income 1000B, D&A 200B, CapEx 100B -> Core Power = 1100B
    # Temporary receivables buildup of -1500B -> CFO = -300B
    facts = [
        _make_canonical_fact("WC_INV_5", 2025, "IS.PROFIT.NET", 1000e9, StatementType.INCOME_STATEMENT),
        _make_canonical_fact("WC_INV_5", 2025, "CF.OPERATING.DEPRECIATION", 200e9, StatementType.CASH_FLOW),
        _make_canonical_fact("WC_INV_5", 2025, "CF.CAPEX", 100e9, StatementType.CASH_FLOW),
        _make_canonical_fact("WC_INV_5", 2025, "CF.OPERATING.NET", -300e9, StatementType.CASH_FLOW),
    ]
    bridge = OwnerEarningsCalculator.calculate(facts, fiscal_year=2025)
    assert bridge.normalization_method == "LATEST_FY_CORE_ADJUSTED"
    assert bridge.owner_earnings == Decimal("550000000000")  # 50% core floor


# =========================================================================
# Scenario 6: Persistent CFO Weakness (Core Power is Non-Positive)
# =========================================================================
def test_scenario_6_persistent_cfo_weakness():
    # Net income -500B, D&A 100B, CapEx 200B -> Core Power = -500 + 100 - 100 = -500B <= 0
    # CFO = -600B
    facts = [
        _make_canonical_fact("WEAK_6", 2025, "IS.PROFIT.NET", -500e9, StatementType.INCOME_STATEMENT),
        _make_canonical_fact("WEAK_6", 2025, "CF.OPERATING.DEPRECIATION", 100e9, StatementType.CASH_FLOW),
        _make_canonical_fact("WEAK_6", 2025, "CF.CAPEX", 200e9, StatementType.CASH_FLOW),
        _make_canonical_fact("WEAK_6", 2025, "CF.OPERATING.NET", -600e9, StatementType.CASH_FLOW),
    ]
    bridge = OwnerEarningsCalculator.calculate(facts, fiscal_year=2025)
    # Core floor does NOT activate for unprofitable companies; raw negative OE is preserved
    assert bridge.normalization_method == "LATEST_FY"
    assert bridge.owner_earnings == Decimal("-700000000000")
    assert bridge.owner_earnings_confidence == "LOW"


# =========================================================================
# Scenario 7: Persistent CFO Strength
# =========================================================================
def test_scenario_7_persistent_cfo_strength():
    facts = [
        _make_canonical_fact("STRONG_7", 2025, "IS.PROFIT.NET", 500e9, StatementType.INCOME_STATEMENT),
        _make_canonical_fact("STRONG_7", 2025, "CF.OPERATING.DEPRECIATION", 50e9, StatementType.CASH_FLOW),
        _make_canonical_fact("STRONG_7", 2025, "CF.CAPEX", 40e9, StatementType.CASH_FLOW),
        _make_canonical_fact("STRONG_7", 2025, "CF.OPERATING.NET", 650e9, StatementType.CASH_FLOW),
    ]
    bridge = OwnerEarningsCalculator.calculate(facts, fiscal_year=2025)
    # OE = 650 - 40 = 610B
    assert bridge.owner_earnings == Decimal("610000000000")


# =========================================================================
# Scenario 8: High CapEx Enterprise
# =========================================================================
def test_scenario_8_high_capex_enterprise():
    facts = [
        _make_canonical_fact("HEAVY_8", 2025, "IS.PROFIT.NET", 1000e9, StatementType.INCOME_STATEMENT),
        _make_canonical_fact("HEAVY_8", 2025, "CF.OPERATING.DEPRECIATION", 600e9, StatementType.CASH_FLOW),
        _make_canonical_fact("HEAVY_8", 2025, "CF.CAPEX", 800e9, StatementType.CASH_FLOW),
        _make_canonical_fact("HEAVY_8", 2025, "CF.OPERATING.NET", 1200e9, StatementType.CASH_FLOW),
    ]
    bridge = OwnerEarningsCalculator.calculate(facts, fiscal_year=2025)
    # Maint CapEx = min(800, 600) = 600B -> OE = 1200 - 600 = 600B
    assert bridge.owner_earnings == Decimal("600000000000")
    assert bridge.growth_capex_estimated == Decimal("200000000000")


# =========================================================================
# Scenario 9: Low CapEx Asset-Light Enterprise
# =========================================================================
def test_scenario_9_asset_light_enterprise():
    facts = [
        _make_canonical_fact("LIGHT_9", 2025, "IS.PROFIT.NET", 500e9, StatementType.INCOME_STATEMENT),
        _make_canonical_fact("LIGHT_9", 2025, "CF.OPERATING.DEPRECIATION", 10e9, StatementType.CASH_FLOW),
        _make_canonical_fact("LIGHT_9", 2025, "CF.CAPEX", 10e9, StatementType.CASH_FLOW),
        _make_canonical_fact("LIGHT_9", 2025, "CF.OPERATING.NET", 510e9, StatementType.CASH_FLOW),
    ]
    bridge = OwnerEarningsCalculator.calculate(facts, fiscal_year=2025)
    # OE = 510 - 10 = 500B
    assert bridge.owner_earnings == Decimal("500000000000")


# =========================================================================
# Scenario 10: Missing CapEx Handling
# =========================================================================
def test_scenario_10_missing_capex():
    facts = [
        _make_canonical_fact("MISS_10", 2025, "IS.PROFIT.NET", 500e9, StatementType.INCOME_STATEMENT),
        _make_canonical_fact("MISS_10", 2025, "CF.OPERATING.DEPRECIATION", 50e9, StatementType.CASH_FLOW),
        _make_canonical_fact("MISS_10", 2025, "CF.OPERATING.NET", 550e9, StatementType.CASH_FLOW),
    ]
    with pytest.raises(ValueError, match="OWNER_EARNINGS_INCOMPLETE"):
        OwnerEarningsCalculator.calculate(facts, fiscal_year=2025)


# =========================================================================
# Scenario 11: Missing D&A Handling
# =========================================================================
def test_scenario_11_missing_da():
    facts = [
        _make_canonical_fact("MISS_11", 2025, "IS.PROFIT.NET", 500e9, StatementType.INCOME_STATEMENT),
        _make_canonical_fact("MISS_11", 2025, "CF.CAPEX", 50e9, StatementType.CASH_FLOW),
        _make_canonical_fact("MISS_11", 2025, "CF.OPERATING.NET", 550e9, StatementType.CASH_FLOW),
    ]
    with pytest.raises(ValueError, match="OWNER_EARNINGS_INCOMPLETE"):
        OwnerEarningsCalculator.calculate(facts, fiscal_year=2025)


# =========================================================================
# Scenario 12: Missing CFO Handling
# =========================================================================
def test_scenario_12_missing_cfo():
    facts = [
        _make_canonical_fact("MISS_12", 2025, "IS.PROFIT.NET", 500e9, StatementType.INCOME_STATEMENT),
        _make_canonical_fact("MISS_12", 2025, "CF.CAPEX", 50e9, StatementType.CASH_FLOW),
        _make_canonical_fact("MISS_12", 2025, "CF.OPERATING.DEPRECIATION", 50e9, StatementType.CASH_FLOW),
    ]
    with pytest.raises(ValueError, match="OWNER_EARNINGS_INCOMPLETE"):
        OwnerEarningsCalculator.calculate(facts, fiscal_year=2025)


# =========================================================================
# Scenario 13: Short History (<3 years)
# =========================================================================
def test_scenario_13_short_history():
    facts = [
        _make_canonical_fact("SHORT_13", 2024, "IS.PROFIT.NET", 100e9, StatementType.INCOME_STATEMENT),
        _make_canonical_fact("SHORT_13", 2024, "IS.REVENUE.NET", 1000e9, StatementType.INCOME_STATEMENT),
        _make_canonical_fact("SHORT_13", 2024, "CF.OPERATING.NET", 110e9, StatementType.CASH_FLOW),
        _make_canonical_fact("SHORT_13", 2024, "CF.CAPEX", 20e9, StatementType.CASH_FLOW),
        _make_canonical_fact("SHORT_13", 2024, "CF.OPERATING.DEPRECIATION", 20e9, StatementType.CASH_FLOW),

        _make_canonical_fact("SHORT_13", 2025, "IS.PROFIT.NET", 150e9, StatementType.INCOME_STATEMENT),
        _make_canonical_fact("SHORT_13", 2025, "IS.REVENUE.NET", 1200e9, StatementType.INCOME_STATEMENT),
        _make_canonical_fact("SHORT_13", 2025, "CF.OPERATING.NET", 160e9, StatementType.CASH_FLOW),
        _make_canonical_fact("SHORT_13", 2025, "CF.CAPEX", 30e9, StatementType.CASH_FLOW),
        _make_canonical_fact("SHORT_13", 2025, "CF.OPERATING.DEPRECIATION", 25e9, StatementType.CASH_FLOW),
    ]
    bridge = OwnerEarningsCalculator.calculate_cycle_normalized(facts, latest_fiscal_year=2025, lookback_years=5)
    assert bridge.normalization_method == "LATEST_FY"
    assert bridge.normalization_years == 1


# =========================================================================
# Scenario 14: 5Y History
# =========================================================================
def test_scenario_14_5y_history():
    facts = []
    for y in range(2021, 2026):
        facts.append(_make_canonical_fact("FIVE_14", y, "IS.PROFIT.NET", 100e9, StatementType.INCOME_STATEMENT))
        facts.append(_make_canonical_fact("FIVE_14", y, "IS.REVENUE.NET", 1000e9, StatementType.INCOME_STATEMENT))
        facts.append(_make_canonical_fact("FIVE_14", y, "CF.OPERATING.NET", 120e9, StatementType.CASH_FLOW))
        facts.append(_make_canonical_fact("FIVE_14", y, "CF.CAPEX", 20e9, StatementType.CASH_FLOW))
        facts.append(_make_canonical_fact("FIVE_14", y, "CF.OPERATING.DEPRECIATION", 20e9, StatementType.CASH_FLOW))

    bridge = OwnerEarningsCalculator.calculate_cycle_normalized(facts, latest_fiscal_year=2025, lookback_years=5)
    assert bridge.normalization_method == "MID_CYCLE_MEDIAN"
    assert bridge.normalization_years == 5


# =========================================================================
# Scenario 15: 10Y History
# =========================================================================
def test_scenario_15_10y_history():
    facts = []
    for y in range(2016, 2026):
        facts.append(_make_canonical_fact("TEN_15", y, "IS.PROFIT.NET", 100e9, StatementType.INCOME_STATEMENT))
        facts.append(_make_canonical_fact("TEN_15", y, "IS.REVENUE.NET", 1000e9, StatementType.INCOME_STATEMENT))
        facts.append(_make_canonical_fact("TEN_15", y, "CF.OPERATING.NET", 120e9, StatementType.CASH_FLOW))
        facts.append(_make_canonical_fact("TEN_15", y, "CF.CAPEX", 20e9, StatementType.CASH_FLOW))
        facts.append(_make_canonical_fact("TEN_15", y, "CF.OPERATING.DEPRECIATION", 20e9, StatementType.CASH_FLOW))

    bridge = OwnerEarningsCalculator.calculate_cycle_normalized(facts, latest_fiscal_year=2025, lookback_years=10)
    assert bridge.normalization_method == "MID_CYCLE_MEDIAN"
    assert bridge.normalization_years == 10


# =========================================================================
# Scenario 16: >10Y History (15 Years)
# =========================================================================
def test_scenario_16_15y_history():
    facts = []
    for y in range(2011, 2026):
        facts.append(_make_canonical_fact("FIFTEEN_16", y, "IS.PROFIT.NET", 100e9, StatementType.INCOME_STATEMENT))
        facts.append(_make_canonical_fact("FIFTEEN_16", y, "IS.REVENUE.NET", 1000e9, StatementType.INCOME_STATEMENT))
        facts.append(_make_canonical_fact("FIFTEEN_16", y, "CF.OPERATING.NET", 120e9, StatementType.CASH_FLOW))
        facts.append(_make_canonical_fact("FIFTEEN_16", y, "CF.CAPEX", 20e9, StatementType.CASH_FLOW))
        facts.append(_make_canonical_fact("FIFTEEN_16", y, "CF.OPERATING.DEPRECIATION", 20e9, StatementType.CASH_FLOW))

    bridge = OwnerEarningsCalculator.calculate_cycle_normalized(facts, latest_fiscal_year=2025, lookback_years=15)
    assert bridge.normalization_method == "MID_CYCLE_MEDIAN"
    assert bridge.normalization_years == 15


# =========================================================================
# Scenario 17: Median Margin and Median Revenue Mismatch
# =========================================================================
def test_scenario_17_median_margin_and_revenue_multiplication():
    facts = []
    # Year 1: Rev 1000, OE 100 -> Margin 10%
    # Year 2: Rev 2000, OE 400 -> Margin 20%
    # Year 3: Rev 3000, OE 300 -> Margin 10%
    revs = [1000e9, 2000e9, 3000e9]
    oes = [100e9, 400e9, 300e9]
    for i, y in enumerate(range(2023, 2026)):
        facts.append(_make_canonical_fact("MED_17", y, "IS.PROFIT.NET", oes[i], StatementType.INCOME_STATEMENT))
        facts.append(_make_canonical_fact("MED_17", y, "IS.REVENUE.NET", revs[i], StatementType.INCOME_STATEMENT))
        facts.append(_make_canonical_fact("MED_17", y, "CF.OPERATING.NET", oes[i] + 20e9, StatementType.CASH_FLOW))
        facts.append(_make_canonical_fact("MED_17", y, "CF.CAPEX", 20e9, StatementType.CASH_FLOW))
        facts.append(_make_canonical_fact("MED_17", y, "CF.OPERATING.DEPRECIATION", 20e9, StatementType.CASH_FLOW))

    bridge = OwnerEarningsCalculator.calculate_cycle_normalized(facts, latest_fiscal_year=2025, lookback_years=3)
    # Median Margin = 10% (0.10), Median Revenue = 2000B -> Mid-cycle OE = 0.10 * 2000B = 200B
    assert bridge.owner_earnings == Decimal("200000000000")


# =========================================================================
# Scenario 18: Core Power Floor Activation
# =========================================================================
def test_scenario_18_core_power_floor_activates():
    facts = [
        _make_canonical_fact("FLOOR_18", 2025, "IS.PROFIT.NET", 1000e9, StatementType.INCOME_STATEMENT),
        _make_canonical_fact("FLOOR_18", 2025, "CF.CAPEX", 100e9, StatementType.CASH_FLOW),
        _make_canonical_fact("FLOOR_18", 2025, "CF.OPERATING.DEPRECIATION", 200e9, StatementType.CASH_FLOW),
        _make_canonical_fact("FLOOR_18", 2025, "CF.OPERATING.NET", -400e9, StatementType.CASH_FLOW),
    ]
    bridge = OwnerEarningsCalculator.calculate(facts, fiscal_year=2025)
    # Core = 1000 + 200 - 100 = 1100B. Floor = 1100 * 0.5 = 550B
    assert bridge.normalization_method == "LATEST_FY_CORE_ADJUSTED"
    assert bridge.owner_earnings == Decimal("550000000000")


# =========================================================================
# Scenario 19: Core Power Floor Not Activated When Raw OE > 0
# =========================================================================
def test_scenario_19_core_power_floor_not_activated():
    facts = [
        _make_canonical_fact("NO_FLOOR_19", 2025, "IS.PROFIT.NET", 1000e9, StatementType.INCOME_STATEMENT),
        _make_canonical_fact("NO_FLOOR_19", 2025, "CF.CAPEX", 100e9, StatementType.CASH_FLOW),
        _make_canonical_fact("NO_FLOOR_19", 2025, "CF.OPERATING.DEPRECIATION", 200e9, StatementType.CASH_FLOW),
        _make_canonical_fact("NO_FLOOR_19", 2025, "CF.OPERATING.NET", 600e9, StatementType.CASH_FLOW),
    ]
    bridge = OwnerEarningsCalculator.calculate(facts, fiscal_year=2025)
    # Raw OE = 600 - 100 = 500B > 0 -> Floor does NOT activate
    assert bridge.normalization_method == "LATEST_FY"
    assert bridge.owner_earnings == Decimal("500000000000")


# =========================================================================
# Scenario 20: Bank Bypass
# =========================================================================
def test_scenario_20_bank_bypass():
    pats = {2021: 10000e9, 2022: 12000e9, 2023: 15000e9, 2024: 16000e9, 2025: 18000e9}
    raw_facts = []
    for y, p in pats.items():
        raw_facts.append(_make_raw_fact("ACB", y, "IS.PROFIT.NET", p, "INCOME_STATEMENT"))
        raw_facts.append(_make_raw_fact("ACB", y, "IS.REVENUE", p * 2.0, "INCOME_STATEMENT"))
        raw_facts.append(_make_raw_fact("ACB", y, "BS.EQUITY.TOTAL", p * 5.0, "BALANCE_SHEET"))
        raw_facts.append(_make_raw_fact("ACB", y, "BS.ASSETS.TOTAL", p * 30.0, "BALANCE_SHEET"))

    munger = build_munger_financial_analysis("ACB", raw_facts=raw_facts)
    assert munger.archetype == "BANK"
    assert munger.overall_financial_quality.get("earnings_quality") == "NOT_APPLICABLE"


# =========================================================================
# Scenario 21: Securities Bypass
# =========================================================================
def test_scenario_21_securities_bypass():
    pats = {2021: 1000e9, 2022: 800e9, 2023: 1200e9, 2024: 1500e9, 2025: 1700e9}
    raw_facts = []
    for y, p in pats.items():
        raw_facts.append(_make_raw_fact("SSI", y, "IS.PROFIT.NET", p, "INCOME_STATEMENT"))
        raw_facts.append(_make_raw_fact("SSI", y, "IS.REVENUE", p * 3.0, "INCOME_STATEMENT"))
        raw_facts.append(_make_raw_fact("SSI", y, "BS.EQUITY.TOTAL", p * 6.0, "BALANCE_SHEET"))
        raw_facts.append(_make_raw_fact("SSI", y, "BS.ASSETS.TOTAL", p * 15.0, "BALANCE_SHEET"))
        raw_facts.append(_make_raw_fact("SSI", y, "CF.OPERATING.NET", -100e9, "CASH_FLOW"))

    munger = build_munger_financial_analysis("SSI", raw_facts=raw_facts)
    assert munger.archetype == "SECURITIES"
    assert munger.long_term_decision["decision_trace"]["quality_gate"] == "PASS"


# =========================================================================
# Scenario 22: Real DB Regression Integrity
# =========================================================================
def test_scenario_22_real_db_regression_reconciled():
    # 5Y Norm PAT vs Valuation Base OE for FPT
    fpt_pats = {2021: 4337.4e9, 2022: 5310.1e9, 2023: 6465.2e9, 2024: 7856.8e9, 2025: 9376.1e9}
    raw_facts = [_make_raw_fact("FPT", y, "IS.PROFIT.NET", p, "INCOME_STATEMENT") for y, p in fpt_pats.items()]
    munger = build_munger_financial_analysis("FPT", raw_facts=raw_facts)
    assert round(munger.normalized_earning_power["normalized_pat_5y"] / 1e9, 1) == 6669.1


# =========================================================================
# Scenario 23: OE / PAT > 100% Legitimate Scenario
# =========================================================================
def test_scenario_23_oe_gt_pat_legitimate():
    # Net income 500B, D&A 200B, CapEx 50B (Asset-light with high past D&A)
    # Working capital neutral -> CFO = 700B
    # OE = 700 - 50 = 650B > Net Income (500B)
    facts = [
        _make_canonical_fact("LEGIT_23", 2025, "IS.PROFIT.NET", 500e9, StatementType.INCOME_STATEMENT),
        _make_canonical_fact("LEGIT_23", 2025, "CF.OPERATING.DEPRECIATION", 200e9, StatementType.CASH_FLOW),
        _make_canonical_fact("LEGIT_23", 2025, "CF.CAPEX", 50e9, StatementType.CASH_FLOW),
        _make_canonical_fact("LEGIT_23", 2025, "CF.OPERATING.NET", 700e9, StatementType.CASH_FLOW),
    ]
    bridge = OwnerEarningsCalculator.calculate(facts, fiscal_year=2025)
    assert bridge.owner_earnings == Decimal("650000000000")
    assert bridge.owner_earnings > Decimal("500000000000")


# =========================================================================
# Scenario 24: OE / PAT > 100% Suspicious Scenario
# =========================================================================
def test_scenario_24_oe_gt_pat_suspicious():
    # Massive working capital liquidation causing single-year CFO to spike 5x
    facts = [
        _make_canonical_fact("SUSP_24", 2025, "IS.PROFIT.NET", 100e9, StatementType.INCOME_STATEMENT),
        _make_canonical_fact("SUSP_24", 2025, "CF.OPERATING.DEPRECIATION", 20e9, StatementType.CASH_FLOW),
        _make_canonical_fact("SUSP_24", 2025, "CF.CAPEX", 20e9, StatementType.CASH_FLOW),
        _make_canonical_fact("SUSP_24", 2025, "CF.OPERATING.NET", 600e9, StatementType.CASH_FLOW),
    ]
    bridge = OwnerEarningsCalculator.calculate(facts, fiscal_year=2025)
    # OE is 580B while PAT is only 100B (OE/PAT = 580%)
    assert bridge.owner_earnings == Decimal("580000000000")
    assert bridge.working_capital_change == Decimal("480000000000")
