import pytest
from decimal import Decimal
from portfolio.financial_data.models import (
    CanonicalFact,
    ConsolidationScope,
    EntityType,
    FactIdentityKey,
    PeriodType,
    QualityStatus,
    StatementType,
)
from portfolio.value_engine import ValuationEngine
from portfolio.value_engine.bank_valuation import BankValuationModel
from portfolio.value_engine.owner_earnings import OwnerEarningsCalculator
from portfolio.value_engine.models import ScenarioType


def _make_fact(code, year, value, qs=QualityStatus.CROSS_SOURCE_VERIFIED):
    stype = StatementType.INCOME_STATEMENT if code.startswith("IS.") else (
        StatementType.CASH_FLOW if code.startswith("CF.") else StatementType.BALANCE_SHEET
    )
    identity = FactIdentityKey(
        security_id="sec-tst-001",
        statement_type=stype,
        period_end=f"{year}-12-31",
        period_type=PeriodType.FY,
        fiscal_year=year,
        fiscal_quarter=None,
        consolidation_scope=ConsolidationScope.CONSOLIDATED,
        line_item_code=code,
        currency="VND",
    )
    return CanonicalFact(
        canonical_fact_id=f"{code}-{year}",
        identity=identity,
        value=value,
        quality_status=qs,
        decision_id=f"dec-{code}-{year}",
        winning_candidate_id=None,
        candidate_ids=[],
        observed_at="2026-01-01T00:00:00Z",
    )


def _facts_for_oe():
    # 5 years of stable profitable history with revenue facts
    facts = []
    for y in range(2019, 2024):
        facts += [
            _make_fact("IS.REVENUE.NET", y, Decimal("1000000000000")),   # 1000 tỷ
            _make_fact("IS.PROFIT.NET", y, Decimal("200000000000")),     # 200 tỷ
            _make_fact("CF.OPERATING.NET", y, Decimal("240000000000")),
            _make_fact("CF.OPERATING.DEPRECIATION", y, Decimal("60000000000")),
            _make_fact("CF.CAPEX", y, Decimal("-80000000000")),
        ]
    return facts


def test_cycle_normalized_uses_mid_cycle_median_not_fy1():
    facts = _facts_for_oe()
    bridge = OwnerEarningsCalculator.calculate_cycle_normalized(
        facts=facts,
        latest_fiscal_year=2023,
        lookback_years=5,
    )
    assert bridge.normalization_method == "MID_CYCLE_MEDIAN"
    assert bridge.normalization_years == 5
    assert bridge.mid_cycle_margin is not None
    assert bridge.mid_cycle_revenue is not None
    # Description must NOT claim a single-year calculation was averaged
    assert "chu kỳ" in bridge.formula_description
    assert "LATEST_FY" not in bridge.normalization_method


def test_cycle_normalized_falls_back_honestly_when_insufficient():
    # Only 1 valid year -> must be LATEST_FY and clearly labelled, never "5Y averaged"
    facts = [
        _make_fact("IS.REVENUE.NET", 2023, Decimal("1000000000000")),
        _make_fact("IS.PROFIT.NET", 2023, Decimal("200000000000")),
        _make_fact("CF.OPERATING.NET", 2023, Decimal("240000000000")),
        _make_fact("CF.OPERATING.DEPRECIATION", 2023, Decimal("60000000000")),
        _make_fact("CF.CAPEX", 2023, Decimal("-80000000000")),
    ]
    bridge = OwnerEarningsCalculator.calculate_cycle_normalized(
        facts=facts,
        latest_fiscal_year=2023,
        lookback_years=7,
    )
    assert bridge.normalization_method == "LATEST_FY"
    assert bridge.normalization_years == 1
    assert "chưa đủ" in bridge.formula_description


def test_bank_sensitivity_is_rim_not_generic_dcf():
    matrix = BankValuationModel.calculate_rim_sensitivity(
        current_bvps=Decimal("18000"),
        base_roe=Decimal("0.19"),
        shares_outstanding=Decimal("5000000000"),
        current_market_price=Decimal("22000"),
        roe_rates=[Decimal("0.15"), Decimal("0.17"), Decimal("0.19"), Decimal("0.21")],
        cost_of_equity_rates=[Decimal("0.10"), Decimal("0.11"), Decimal("0.12"), Decimal("0.13")],
    )
    assert matrix.sensitivity_type == "RIM_ROE_COE"
    assert len(matrix.grid_values_per_share) == 4
    assert len(matrix.grid_values_per_share[0]) == 4
    assert matrix.col_label == "Tỷ suất Sinh lời trên Vốn (ROE)"
    # Higher ROE at same CoE must give higher IV
    assert matrix.grid_values_per_share[3][1] > matrix.grid_values_per_share[0][1]


def test_growth_derivation_caps_by_history():
    hist = []
    for i in range(7):
        yr = 2017 + i
        hist.append({
            "fiscal_year": yr,
            "net_profit": (100e9 * (1.01 ** i)),  # ~1% historical CAGR (weak)
            "equity": 1e12 + i * 50e9,
            "revenue": 3e12 + i * 0.2e12,
        })
    der = ValuationEngine._derive_growth(
        financial_history=hist,
        roe_val=20.0,
        retention_rate_estimate=Decimal("0.70"),
        is_cyclical=False,
    )
    assert der["method"] == "REINVESTMENT_X_INCREMENTAL_RETURN"
    assert der["base_growth"] is not None
    # History cap must be applied: ~1% CAGR cannot yield ~14% base growth
    assert der["base_growth"] <= 8.0
    assert der["confidence_downgrade"] is True


def test_growth_derivation_high_history_allows_higher_growth():
    hist = []
    for i in range(7):
        yr = 2017 + i
        hist.append({
            "fiscal_year": yr,
            "net_profit": (100e9 * (1.25 ** i)),  # ~25% historical CAGR
            "equity": 1e12 + i * 0.2e12,
            "revenue": 3e12 + i * 1e12,
        })
    der = ValuationEngine._derive_growth(
        financial_history=hist,
        roe_val=25.0,
        retention_rate_estimate=Decimal("0.70"),
        is_cyclical=False,
    )
    assert der["confidence_downgrade"] is False
    assert der["base_growth"] >= 10.0


def test_negative_cumulative_iroic_penalizes_capital_allocation():
    from portfolio.value_engine.quality_scorer import QualityScorer
    from portfolio.value_engine.archetypes import ArchetypeClassifier

    # History where equity grew significantly but net profit dropped (value destruction on retained capital)
    hist = []
    for i in range(5):
        yr = 2019 + i
        hist.append({
            "fiscal_year": yr,
            "revenue": 10e12,
            "net_profit": 1e12 - i * 0.2e12,  # Falling from 1.0T to 0.2T
            "equity": 5e12 + i * 1.5e12,      # Growing from 5.0T to 11.0T
            "roe": 10.0 - i * 2.0,
            "operating_cash_flow": 1e12,
        })

    prof = ArchetypeClassifier.classify("TEST_SYM")
    scorecard = QualityScorer.evaluate(
        archetype_prof=prof,
        financial_history_10y=hist,
        five_year_avg_roe=8.0,
        five_year_avg_cash_conversion=100.0,
        net_debt_vnd=0.0,
        latest_cfo=1e12,
        true_dilution_5y_pct=0.0,
    )
    # Cumulative 3Y iROIC is deeply negative: capital allocation cannot score 15/15
    assert scorecard.capital_allocation_score <= 6
    assert scorecard.capital_allocation_evidence.get("cumulative_3y_iroic_pct") is not None
    assert scorecard.capital_allocation_evidence["cumulative_3y_iroic_pct"] < 0


def test_terminal_value_contribution_warning_and_bank_isolation():
    from portfolio.value_engine.dcf import DCFValuationModel
    from portfolio.value_engine.models import ScenarioType

    # Scenario with high growth causing Terminal Value > 75%
    scenario = DCFValuationModel.calculate_scenario(
        base_owner_earnings=Decimal("100000000000"),
        shares_outstanding=Decimal("1000000000"),
        net_debt=Decimal("0"),
        scenario_type=ScenarioType.BASE,
        discount_rate=Decimal("0.09"),
        growth_rate=Decimal("0.20"),
        growth_years=5,
        terminal_growth=Decimal("0.04"),
    )
    assert scenario.terminal_value_contribution_pct is not None
    assert scenario.terminal_value_contribution_pct > Decimal("75")
    assert len(scenario.scenario_warnings) > 0
    assert "Terminal Value" in scenario.scenario_warnings[0]

    # Bank isolation test
    mbb_facts = [
        _make_fact("BS.EQUITY.TOTAL", 2023, Decimal("80000000000000")),
    ]
    report = ValuationEngine.evaluate(
        symbol="MBB",
        facts=mbb_facts,
        current_market_price=Decimal("24000"),
        shares_outstanding=Decimal("5200000000"),
        fiscal_year=2023,
        entity_type=EntityType.BANK,
        fundamentals={"sector": "Ngân hàng", "pb": 1.2, "roe": 22.0, "bvps": 20000},
    )
    # Banks remove Owner Earnings / CapEx schema
    assert report.owner_earnings_bridge is None
    assert report.valuation_model == "RESIDUAL_INCOME_MODEL"
    assert report.growth_derivation.get("normalized_roe") is not None
    assert "base_growth" not in report.growth_derivation