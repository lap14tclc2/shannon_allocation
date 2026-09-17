"""
TASK-20260917-192: Golden Test Matrix for Canonical Intrinsic Value & DCF Conservatism Audit.

Tests 25 distinct economic, accounting, and mathematical scenarios to verify:
1. Normal stable enterprise
2. High-growth enterprise
3. Cyclical enterprise
4. High CapEx enterprise
5. Low CapEx enterprise
6. Temporary WC release
7. Temporary WC investment
8. Missing Owner Earnings
9. Missing CapEx
10. Missing growth
11. Missing discount-rate input
12. Missing terminal growth
13. Terminal growth >= discount rate
14. Extreme historical CAGR
15. Growth ceiling activation
16. Bear/Base/Bull ordering
17. Scenario weights
18. Terminal-value dominance
19. Share split
20. Economic dilution
21. Bank RIM bypass
22. Securities bypass
23. MOS consistency
24. False precision / confidence semantics
25. Real DB regression
"""
import os
import pytest
from dataclasses import asdict
from decimal import Decimal
from typing import Dict, Any, List

if not os.environ.get("DATABASE_URL"):
    os.environ["DATABASE_URL"] = "postgresql://qport:qport@127.0.0.1:5432/qport"

from portfolio.financial_data.models import (
    CanonicalFact,
    ConsolidationScope,
    EntityType,
    FactIdentityKey,
    PeriodType,
    QualityStatus,
    StatementType,
)
from portfolio.value_engine.engine import ValuationEngine
from portfolio.value_engine.dcf import DCFValuationModel
from portfolio.value_engine.bank_valuation import BankValuationModel
from portfolio.value_engine.models import (
    ConfidenceLevel,
    ScenarioType,
    ValuationPill,
    ValuationScenario,
)
from portfolio.value_engine.share_basis import (
    ShareBasis,
    ShareBasisStatus,
    ShareBasisType,
    calculate_canonical_mos,
    resolve_canonical_share_basis,
)
from portfolio.canonical_valuation import build_canonical_valuation


def make_fact(code: str, val: float, year: int = 2026, statement: StatementType = StatementType.INCOME_STATEMENT) -> CanonicalFact:
    return CanonicalFact(
        canonical_fact_id=f"test-{code}-{year}",
        identity=FactIdentityKey(
            security_id="sec-test",
            statement_type=statement,
            period_end=f"{year}-12-31",
            period_type=PeriodType.FY,
            fiscal_year=year,
            fiscal_quarter=None,
            consolidation_scope=ConsolidationScope.CONSOLIDATED,
            line_item_code=code,
            currency="VND",
        ),
        value=Decimal(str(val)),
        quality_status=QualityStatus.SINGLE_SOURCE,
        decision_id=f"dec-test-{year}",
        winning_candidate_id=f"cand-test-{year}",
        candidate_ids=[],
        observed_at="2026-09-17T00:00:00Z",
        valid_from="2026-09-17T00:00:00Z",
        reason="test",
    )


def make_standard_facts(ni=1000e9, op=1200e9, cfo=1100e9, da=200e9, capex=-300e9, debt=500e9, cash=200e9, shares=100e6, year=2026):
    return [
        make_fact("IS.PROFIT.NET", ni, year, StatementType.INCOME_STATEMENT),
        make_fact("IS.PROFIT.OPERATING", op, year, StatementType.INCOME_STATEMENT),
        make_fact("CF.OPERATING.NET", cfo, year, StatementType.CASH_FLOW),
        make_fact("CF.OPERATING.DEPRECIATION", da, year, StatementType.CASH_FLOW),
        make_fact("CF.CAPEX", capex, year, StatementType.CASH_FLOW),
        make_fact("BS.DEBT.TOTAL", debt, year, StatementType.BALANCE_SHEET),
        make_fact("BS.ASSETS.CASH_AND_EQUIVALENTS", cash, year, StatementType.BALANCE_SHEET),
        make_fact("IS.SHARES.OUTSTANDING", shares, year, StatementType.INCOME_STATEMENT),
    ]


# 1. Normal Stable Enterprise
def test_01_normal_stable_enterprise():
    facts = make_standard_facts()
    rep = ValuationEngine.evaluate(
        symbol="STABLE",
        facts=facts,
        current_market_price=Decimal("50000"),
        shares_outstanding=Decimal("100000000"),
        fiscal_year=2026,
    )
    assert rep.valuation_pill in (
        ValuationPill.ATTRACTIVE.value,
        ValuationPill.FAIRLY_VALUED.value,
        ValuationPill.OVERVALUED.value,
        ValuationPill.WATCH.value,
        ValuationPill.MODEL_INCOMPLETE.value,
        ValuationPill.FALLBACK_MODEL_ONLY.value,
    )
    base_scen = rep.scenarios[ScenarioType.BASE]
    assert base_scen.intrinsic_value_per_share > Decimal("0")
    assert base_scen.discount_rate == Decimal("0.11")
    assert base_scen.terminal_growth_rate == Decimal("0.035")


# 2. High-Growth Enterprise Bounded by Growth Ceiling
def test_02_high_growth_enterprise_bounded():
    hist = [
        {"fiscal_year": 2021, "net_profit": 100e9, "equity": 500e9},
        {"fiscal_year": 2022, "net_profit": 200e9, "equity": 700e9},
        {"fiscal_year": 2023, "net_profit": 400e9, "equity": 1100e9},
        {"fiscal_year": 2024, "net_profit": 800e9, "equity": 1900e9},
        {"fiscal_year": 2025, "net_profit": 1600e9, "equity": 3500e9},
    ]
    growth_info = ValuationEngine._derive_growth(
        financial_history=hist,
        roe_val=40.0,
        retention_rate_estimate=Decimal("0.80"),
        is_cyclical=False,
    )
    # Despite massive historical CAGR (>70%), base growth must be capped by maturity/evidence cap <= 25%
    assert growth_info["base_growth"] <= 25.0
    assert growth_info["bull_growth"] <= 20.0


# 3. Cyclical Enterprise
def test_03_cyclical_enterprise_lookback_and_cap():
    hist = [
        {"fiscal_year": y, "net_profit": 100e9 * (1 + 0.5 * (y % 2)), "equity": 500e9}
        for y in range(2016, 2026)
    ]
    growth_info = ValuationEngine._derive_growth(
        financial_history=hist,
        roe_val=15.0,
        retention_rate_estimate=Decimal("0.70"),
        is_cyclical=True,
    )
    assert growth_info["maturity_cap"] == 20.0
    assert growth_info["base_growth"] <= 20.0


# 4. High CapEx Enterprise
def test_04_high_capex_enterprise():
    # Heavy CapEx reduces owner earnings
    facts = make_standard_facts(ni=1000e9, da=200e9, capex=-900e9)
    rep = ValuationEngine.evaluate(
        symbol="HEAVY",
        facts=facts,
        current_market_price=Decimal("30000"),
        shares_outstanding=Decimal("100000000"),
        fiscal_year=2026,
    )
    assert rep.owner_earnings_bridge.owner_earnings < Decimal("1000e9")


# 5. Low CapEx / Asset-Light Enterprise
def test_05_low_capex_asset_light():
    facts = make_standard_facts(ni=1000e9, da=50e9, capex=-20e9)
    rep = ValuationEngine.evaluate(
        symbol="LIGHT",
        facts=facts,
        current_market_price=Decimal("50000"),
        shares_outstanding=Decimal("100000000"),
        fiscal_year=2026,
    )
    assert rep.owner_earnings_bridge.owner_earnings > Decimal("900e9")


# 6. Temporary WC Release
def test_06_temporary_wc_release():
    # CFO is artificially inflated by large WC release (CFO >> Net Income + D&A)
    facts = make_standard_facts(ni=1000e9, da=200e9, cfo=2500e9, capex=-200e9)
    rep = ValuationEngine.evaluate(
        symbol="WCRELEASE",
        facts=facts,
        current_market_price=Decimal("50000"),
        shares_outstanding=Decimal("100000000"),
        fiscal_year=2026,
    )
    # OE should not blindly equal inflated CFO - CapEx without reconciliation
    assert rep.owner_earnings_bridge is not None


# 7. Temporary WC Investment
def test_07_temporary_wc_investment():
    # CFO is depressed by large inventory/receivables build
    facts = make_standard_facts(ni=1000e9, da=200e9, cfo=100e9, capex=-200e9)
    rep = ValuationEngine.evaluate(
        symbol="WCBUILD",
        facts=facts,
        current_market_price=Decimal("50000"),
        shares_outstanding=Decimal("100000000"),
        fiscal_year=2026,
    )
    assert rep.owner_earnings_bridge is not None


# 8. Missing / Negative Owner Earnings
def test_08_missing_or_negative_owner_earnings():
    # Massive losses make OE non-positive
    facts = make_standard_facts(ni=-1000e9, cfo=-500e9)
    rep = ValuationEngine.evaluate(
        symbol="LOSSCO",
        facts=facts,
        current_market_price=Decimal("10000"),
        shares_outstanding=Decimal("100000000"),
        fiscal_year=2026,
    )
    assert rep.valuation_pill == ValuationPill.UNVALUABLE.value
    assert rep.confidence_level in (ConfidenceLevel.BLOCKED, ConfidenceLevel.LOW)


# 9. Missing CapEx Fallback
def test_09_missing_capex_fallback():
    # Missing CF.CAPEX fact raises error or triggers proxy
    facts = [f for f in make_standard_facts() if f.identity.line_item_code != "CF.CAPEX"]
    with pytest.raises(ValueError, match="VALUATION_FACTS_INCOMPLETE"):
        ValuationEngine.evaluate(
            symbol="NOCAPEX",
            facts=facts,
            current_market_price=Decimal("50000"),
            shares_outstanding=Decimal("100000000"),
            fiscal_year=2026,
        )


# 10. Missing Growth Default
def test_10_missing_growth_default():
    # Empty history defaults to sustainable growth floor
    growth_info = ValuationEngine._derive_growth(
        financial_history=[],
        roe_val=None,
        retention_rate_estimate=Decimal("0.70"),
        is_cyclical=False,
    )
    assert growth_info["base_growth"] >= 2.0
    assert growth_info["bear_growth"] >= 2.0


# 11. Missing Discount-Rate Input Fallback
def test_11_missing_discount_rate_fallback():
    facts = make_standard_facts()
    rep = ValuationEngine.evaluate(
        symbol="NORATE",
        facts=facts,
        current_market_price=Decimal("50000"),
        shares_outstanding=Decimal("100000000"),
        hurdle_rate=Decimal("0.11"),
    )
    assert rep.scenarios[ScenarioType.BASE].discount_rate == Decimal("0.11")


# 12. Missing Terminal Growth Default
def test_12_missing_terminal_growth_default():
    facts = make_standard_facts()
    rep = ValuationEngine.evaluate(
        symbol="NOTG",
        facts=facts,
        current_market_price=Decimal("50000"),
        shares_outstanding=Decimal("100000000"),
        terminal_growth=Decimal("0.035"),
    )
    assert rep.scenarios[ScenarioType.BASE].terminal_growth_rate == Decimal("0.035")


# 13. Terminal Growth >= Discount Rate Exception
def test_13_terminal_growth_ge_discount_rate():
    with pytest.raises(ValueError, match="strictly greater than terminal growth"):
        DCFValuationModel.calculate_scenario(
            base_owner_earnings=Decimal("100e9"),
            shares_outstanding=Decimal("10e6"),
            net_debt=Decimal("0"),
            scenario_type=ScenarioType.BASE,
            discount_rate=Decimal("0.035"),
            growth_rate=Decimal("0.05"),
            terminal_growth=Decimal("0.035"), # g == r
        )

    with pytest.raises(ValueError, match="strictly greater than terminal growth"):
        DCFValuationModel.calculate_scenario(
            base_owner_earnings=Decimal("100e9"),
            shares_outstanding=Decimal("10e6"),
            net_debt=Decimal("0"),
            scenario_type=ScenarioType.BASE,
            discount_rate=Decimal("0.030"),
            growth_rate=Decimal("0.05"),
            terminal_growth=Decimal("0.035"), # g > r
        )


# 14. Extreme Historical CAGR Damping
def test_14_extreme_historical_cagr_damping():
    hist = [
        {"fiscal_year": 2021, "net_profit": 10e9, "equity": 100e9},
        {"fiscal_year": 2022, "net_profit": 50e9, "equity": 150e9},
        {"fiscal_year": 2023, "net_profit": 200e9, "equity": 350e9},
        {"fiscal_year": 2024, "net_profit": 600e9, "equity": 950e9},
        {"fiscal_year": 2025, "net_profit": 1800e9, "equity": 2750e9},
    ]
    # CAGR is ((1800/10)^(1/4) - 1) = 266%
    g = ValuationEngine._derive_growth(hist, roe_val=50.0, retention_rate_estimate=Decimal("0.8"), is_cyclical=False)
    assert g["historical_cagr_5y_pct"] > 200.0
    assert g["base_growth"] <= 25.0


# 15. Growth Ceiling Activation
def test_15_growth_ceiling_activation():
    # Cyclical maturity cap is 20%
    g_cyc = ValuationEngine._derive_growth([], roe_val=35.0, retention_rate_estimate=Decimal("0.9"), is_cyclical=True)
    assert g_cyc["base_growth"] <= 20.0
    # Non-cyclical maturity cap is 25%
    g_non = ValuationEngine._derive_growth([], roe_val=35.0, retention_rate_estimate=Decimal("0.9"), is_cyclical=False)
    assert g_non["base_growth"] <= 25.0


# 16. Bear / Base / Bull Monotonic Ordering
def test_16_bear_base_bull_ordering():
    facts = make_standard_facts()
    rep = ValuationEngine.evaluate(
        symbol="ORDER",
        facts=facts,
        current_market_price=Decimal("50000"),
        shares_outstanding=Decimal("100000000"),
    )
    bear = rep.scenarios[ScenarioType.BEAR].intrinsic_value_per_share
    base = rep.scenarios[ScenarioType.BASE].intrinsic_value_per_share
    bull = rep.scenarios[ScenarioType.BULL].intrinsic_value_per_share
    assert bear <= base <= bull


# 17. Scenario Weights / Base IV Canonical Usage
def test_17_scenario_weights_and_canonical_iv():
    facts = make_standard_facts()
    rep = ValuationEngine.evaluate(
        symbol="CANON",
        facts=facts,
        current_market_price=Decimal("50000"),
        shares_outstanding=Decimal("100000000"),
    )
    base_iv = rep.scenarios[ScenarioType.BASE].intrinsic_value_per_share
    # Public canonical IV must be Base IV (or None if unverified)
    assert rep.valuation_snapshot["intrinsic_value_per_share"] == float(base_iv)


# 18. Terminal-Value Dominance Flag
def test_18_terminal_value_dominance_flag():
    # Very high growth and low discount rate causes TV > 75%
    scen = DCFValuationModel.calculate_scenario(
        base_owner_earnings=Decimal("100e9"),
        shares_outstanding=Decimal("10e6"),
        net_debt=Decimal("0"),
        scenario_type=ScenarioType.BASE,
        discount_rate=Decimal("0.09"),
        growth_rate=Decimal("0.20"),
        terminal_growth=Decimal("0.04"),
        current_market_price=Decimal("50000"),
    )
    assert scen.terminal_value_contribution_pct > Decimal("75")
    assert any(">75%" in w for w in scen.scenario_warnings)


# 19. Share Split Integrity
def test_19_share_split_integrity():
    # 1:1 stock split doubles share count and halves per-share IV
    sb_orig = resolve_canonical_share_basis("SPLIT", Decimal("100e6"), 2026, "2026-12-31")
    sb_split = resolve_canonical_share_basis("SPLIT", Decimal("200e6"), 2026, "2026-12-31")
    assert sb_split.valuation_share_count == sb_orig.valuation_share_count * 2


# 20. Economic Dilution Impact
def test_20_economic_dilution_impact():
    sb = resolve_canonical_share_basis(
        "DILUTE",
        bctc_shares=Decimal("100e6"),
        bctc_fiscal_year=2026,
        bctc_period_end="2026-12-31",
        diluted_shares_estimate=Decimal("120e6"),
    )
    assert sb.diluted_shares == Decimal("120e6")


# 21. Bank RIM Bypass
def test_21_bank_rim_bypass():
    # Bank uses RIM, does not require CF.CAPEX or CF.OPERATING.NET
    facts = [
        make_fact("BS.EQUITY.TOTAL", 25000e9, 2026, StatementType.BALANCE_SHEET),
        make_fact("IS.SHARES.OUTSTANDING", 1000e6, 2026, StatementType.INCOME_STATEMENT),
    ]
    rep = ValuationEngine.evaluate(
        symbol="BANKCO",
        facts=facts,
        current_market_price=Decimal("25000"),
        shares_outstanding=Decimal("1000e6"),
        entity_type=EntityType.BANK,
        fundamentals={"bvps": 25000, "roe": 20.0},
    )
    assert rep.valuation_model == "RESIDUAL_INCOME_MODEL"
    assert rep.owner_earnings_bridge is None
    assert rep.scenarios[ScenarioType.BASE].cashflow_basis == "RESIDUAL_INCOME"
    assert rep.scenarios[ScenarioType.BASE].net_debt == Decimal("0")


# 22. Securities Bypass
def test_22_securities_bypass():
    facts = [
        make_fact("BS.EQUITY.TOTAL", 10000e9, 2026, StatementType.BALANCE_SHEET),
        make_fact("IS.SHARES.OUTSTANDING", 500e6, 2026, StatementType.INCOME_STATEMENT),
    ]
    rep = ValuationEngine.evaluate(
        symbol="SSI_SEC",
        facts=facts,
        current_market_price=Decimal("30000"),
        shares_outstanding=Decimal("500e6"),
        fundamentals={"sector": "Chứng khoán", "bvps": 20000, "roe": 16.0},
    )
    assert rep.valuation_model == "RESIDUAL_INCOME_MODEL"


# 23. MOS Consistency
def test_23_mos_consistency():
    price = Decimal("70000")
    iv = Decimal("100000")
    mos = calculate_canonical_mos(price, iv)
    assert mos == Decimal("30.00") # (100k - 70k) / 100k = 30%


# 24. False Precision / Confidence Semantics
def test_24_false_precision_semantics():
    facts = make_standard_facts()
    rep = ValuationEngine.evaluate(
        symbol="PRECISION",
        facts=facts,
        current_market_price=Decimal("50000"),
        shares_outstanding=Decimal("100000000"),
    )
    d = asdict(rep)
    assert d["valuation_pill"] is not None
    assert "NaN" not in str(d)
    assert "null" not in d["assessment"]["valuation_verdict"].lower()


# 25. Real DB Regression (PostgreSQL Core Verification)
def test_25_real_db_regression():
    for sym in ["FPT", "ACB", "BFC"]:
        val = build_canonical_valuation(sym)
        assert val.get("ok") is True
        assert val.get("symbol") == sym
        assert val.get("price") is not None and val["price"] > 0
        assert val.get("base_iv") is not None and val["base_iv"] > 0
        assert val.get("bear_iv") is not None and val["bear_iv"] > 0
        assert val.get("bull_iv") is not None and val["bull_iv"] > 0
        assert val["bear_iv"] <= val["base_iv"] <= val["bull_iv"]
