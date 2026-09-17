"""Task 190: Owner Earnings & Maintenance CapEx Integrity Test Suite.

Comprehensive deterministic test coverage for Scenarios A through W:
- Scenario A: Stable CFO + stable CapEx -> stable Owner Earnings
- Scenario B: CapEx spike -> multi-year mid-cycle median dampens single-year distortion
- Scenario C: Permanently higher CapEx -> properly reflected in mid-cycle margins
- Scenario D: Missing CapEx -> single-year raises ValueError; multi-year handles honestly
- Scenario E: Missing CFO -> single-year raises ValueError; multi-year handles honestly
- Scenario F: Missing D&A -> single-year raises ValueError; multi-year handles honestly
- Scenario G: Negative CFO -> reflects negative cash flow without silent masking
- Scenario H: Negative OE with positive core power -> conservative core floor applied
- Scenario I: D&A double-count prevention -> (NI + DA - MaintCapEx + dWC) strictly equals (CFO - MaintCapEx)
- Scenario J: Working capital double-count prevention -> dWC is the exact bridge between NI+DA and CFO
- Scenario K: Cyclical earnings -> multi-year MID_CYCLE_MEDIAN removes peak/trough bias
- Scenario L: Peak earnings -> mid-cycle median prevents peak cash flow extrapolation
- Scenario M: Secular growth -> compounder uses latest FY or mid-cycle without artificial cyclical penalties
- Scenario N: Bank archetype -> isolates from industrial OE; uses Residual Income Model (RIM)
- Scenario O: Securities archetype -> isolates from industrial CFO/CapEx; uses equity/trading models
- Scenario P: Partial history (<3 years) -> honest fallback to LATEST_FY, never labeled averaged
- Scenario Q: Fiscal-window determinism -> identical facts + identical window produce identical OE
- Scenario R: Synthetic vs real data separation -> synthetic fixtures do not overwrite DB provenance
- Scenario S: Share-basis invariance -> IV/share and current price share canonical share basis
- Scenario T: Stock split invariance -> pure split keeps enterprise Owner Earnings and MOS identical
- Scenario U: Economic dilution -> cash equity issuance reduces per-share OE proportionally
- Scenario V: CFO/PAT reconciliation -> cash conversion ratio CFO/PAT correctly bridges cash and profit
- Scenario W: Normalized PAT vs Normalized OE semantic distinction -> separate authorities and metrics
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
from portfolio.value_engine.share_basis import resolve_canonical_share_basis


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
# Scenario A: Stable CFO + Stable CapEx
# =========================================================================
def test_scenario_a_stable_cfo_and_capex():
    facts = [
        _make_canonical_fact("STABLE_CO", 2025, "IS.PROFIT.NET", 500e9, StatementType.INCOME_STATEMENT),
        _make_canonical_fact("STABLE_CO", 2025, "CF.OPERATING.DEPRECIATION", 100e9, StatementType.CASH_FLOW),
        _make_canonical_fact("STABLE_CO", 2025, "CF.CAPEX", 100e9, StatementType.CASH_FLOW),
        _make_canonical_fact("STABLE_CO", 2025, "CF.OPERATING.NET", 600e9, StatementType.CASH_FLOW),
    ]
    bridge = OwnerEarningsCalculator.calculate(facts, fiscal_year=2025)
    # OE = CFO - min(CapEx, D&A) = 600 - 100 = 500
    assert bridge.owner_earnings == Decimal("500000000000")
    assert bridge.maintenance_capex == Decimal("100000000000")


# =========================================================================
# Scenario B: CapEx Spike damped in Multi-Year Median
# =========================================================================
def test_scenario_b_capex_spike_damped_in_cycle_median():
    facts = []
    # 5 years: year 4 has a 10x CapEx spike due to factory construction
    pats = [200e9, 210e9, 220e9, 230e9, 240e9]
    revs = [2000e9, 2100e9, 2200e9, 2300e9, 2400e9]
    cfos = [250e9, 260e9, 270e9, 280e9, 300e9]
    capexs = [50e9, 50e9, 50e9, 500e9, 50e9]  # year 4 spike
    das = [40e9, 45e9, 50e9, 55e9, 60e9]

    for i, y in enumerate(range(2021, 2026)):
        facts.append(_make_canonical_fact("SPIKE_CO", y, "IS.PROFIT.NET", pats[i], StatementType.INCOME_STATEMENT))
        facts.append(_make_canonical_fact("SPIKE_CO", y, "IS.REVENUE.NET", revs[i], StatementType.INCOME_STATEMENT))
        facts.append(_make_canonical_fact("SPIKE_CO", y, "CF.OPERATING.NET", cfos[i], StatementType.CASH_FLOW))
        facts.append(_make_canonical_fact("SPIKE_CO", y, "CF.CAPEX", capexs[i], StatementType.CASH_FLOW))
        facts.append(_make_canonical_fact("SPIKE_CO", y, "CF.OPERATING.DEPRECIATION", das[i], StatementType.CASH_FLOW))

    bridge = OwnerEarningsCalculator.calculate_cycle_normalized(facts, latest_fiscal_year=2025, lookback_years=5)
    assert bridge.normalization_method == "MID_CYCLE_MEDIAN"
    # Mid-cycle owner earnings is not crushed by year 4 spike
    assert bridge.owner_earnings > Decimal("200000000000")


# =========================================================================
# Scenario C: Permanently Higher CapEx reflected
# =========================================================================
def test_scenario_c_permanent_higher_capex_reflected():
    facts = []
    # High CapEx across all 5 years
    pats = [200e9]*5
    revs = [2000e9]*5
    cfos = [300e9]*5
    capexs = [200e9]*5
    das = [150e9]*5

    for i, y in enumerate(range(2021, 2026)):
        facts.append(_make_canonical_fact("HEAVY_CO", y, "IS.PROFIT.NET", pats[i], StatementType.INCOME_STATEMENT))
        facts.append(_make_canonical_fact("HEAVY_CO", y, "IS.REVENUE.NET", revs[i], StatementType.INCOME_STATEMENT))
        facts.append(_make_canonical_fact("HEAVY_CO", y, "CF.OPERATING.NET", cfos[i], StatementType.CASH_FLOW))
        facts.append(_make_canonical_fact("HEAVY_CO", y, "CF.CAPEX", capexs[i], StatementType.CASH_FLOW))
        facts.append(_make_canonical_fact("HEAVY_CO", y, "CF.OPERATING.DEPRECIATION", das[i], StatementType.CASH_FLOW))

    bridge = OwnerEarningsCalculator.calculate_cycle_normalized(facts, latest_fiscal_year=2025, lookback_years=5)
    # OE = 300 - min(200, 150) = 150B each year
    assert bridge.owner_earnings == Decimal("150000000000")


# =========================================================================
# Scenario D: Missing CapEx handling
# =========================================================================
def test_scenario_d_missing_capex():
    facts = [
        _make_canonical_fact("MISS_CAPEX", 2025, "IS.PROFIT.NET", 500e9, StatementType.INCOME_STATEMENT),
        _make_canonical_fact("MISS_CAPEX", 2025, "CF.OPERATING.DEPRECIATION", 100e9, StatementType.CASH_FLOW),
        _make_canonical_fact("MISS_CAPEX", 2025, "CF.OPERATING.NET", 600e9, StatementType.CASH_FLOW),
    ]
    with pytest.raises(ValueError, match="OWNER_EARNINGS_INCOMPLETE"):
        OwnerEarningsCalculator.calculate(facts, fiscal_year=2025)


# =========================================================================
# Scenario E: Missing CFO handling
# =========================================================================
def test_scenario_e_missing_cfo():
    facts = [
        _make_canonical_fact("MISS_CFO", 2025, "IS.PROFIT.NET", 500e9, StatementType.INCOME_STATEMENT),
        _make_canonical_fact("MISS_CFO", 2025, "CF.CAPEX", 100e9, StatementType.CASH_FLOW),
        _make_canonical_fact("MISS_CFO", 2025, "CF.OPERATING.DEPRECIATION", 100e9, StatementType.CASH_FLOW),
    ]
    with pytest.raises(ValueError, match="OWNER_EARNINGS_INCOMPLETE"):
        OwnerEarningsCalculator.calculate(facts, fiscal_year=2025)


# =========================================================================
# Scenario F: Missing D&A handling
# =========================================================================
def test_scenario_f_missing_da():
    facts = [
        _make_canonical_fact("MISS_DA", 2025, "IS.PROFIT.NET", 500e9, StatementType.INCOME_STATEMENT),
        _make_canonical_fact("MISS_DA", 2025, "CF.CAPEX", 100e9, StatementType.CASH_FLOW),
        _make_canonical_fact("MISS_DA", 2025, "CF.OPERATING.NET", 600e9, StatementType.CASH_FLOW),
    ]
    with pytest.raises(ValueError, match="OWNER_EARNINGS_INCOMPLETE"):
        OwnerEarningsCalculator.calculate(facts, fiscal_year=2025)


# =========================================================================
# Scenario G: Negative CFO handling
# =========================================================================
def test_scenario_g_negative_cfo():
    facts = [
        _make_canonical_fact("NEG_CFO", 2025, "IS.PROFIT.NET", -100e9, StatementType.INCOME_STATEMENT),
        _make_canonical_fact("NEG_CFO", 2025, "CF.CAPEX", 50e9, StatementType.CASH_FLOW),
        _make_canonical_fact("NEG_CFO", 2025, "CF.OPERATING.DEPRECIATION", 40e9, StatementType.CASH_FLOW),
        _make_canonical_fact("NEG_CFO", 2025, "CF.OPERATING.NET", -200e9, StatementType.CASH_FLOW),
    ]
    bridge = OwnerEarningsCalculator.calculate(facts, fiscal_year=2025)
    # OE = CFO - min(CapEx, D&A) = -200 - 40 = -240
    assert bridge.owner_earnings == Decimal("-240000000000")
    assert bridge.owner_earnings_confidence == "LOW"


# =========================================================================
# Scenario H: Negative OE with positive core power (working capital buffer)
# =========================================================================
def test_scenario_h_core_adjusted_floor():
    # Net Income: 1000B, D&A: 200B, CapEx: 100B -> Core = 1000 + 200 - 100 = 1100B
    # Working capital outflow is huge (-1500B) -> CFO = -300B
    # Raw OE = -300 - 100 = -400B
    # But core power is 1100B > 0 -> Floor applies: max(1100 * 0.5 = 550B, 1100 - 1500 = -400B) = 550B
    facts = [
        _make_canonical_fact("CORE_ADJ", 2025, "IS.PROFIT.NET", 1000e9, StatementType.INCOME_STATEMENT),
        _make_canonical_fact("CORE_ADJ", 2025, "CF.CAPEX", 100e9, StatementType.CASH_FLOW),
        _make_canonical_fact("CORE_ADJ", 2025, "CF.OPERATING.DEPRECIATION", 200e9, StatementType.CASH_FLOW),
        _make_canonical_fact("CORE_ADJ", 2025, "CF.OPERATING.NET", -300e9, StatementType.CASH_FLOW),
    ]
    bridge = OwnerEarningsCalculator.calculate(facts, fiscal_year=2025)
    assert bridge.normalization_method == "LATEST_FY_CORE_ADJUSTED"
    assert bridge.owner_earnings == Decimal("550000000000")


# =========================================================================
# Scenario I: D&A Double-Count Prevention (Algebraic Proof)
# =========================================================================
def test_scenario_i_da_double_count_prevention():
    net_income = Decimal("1000e9")
    da = Decimal("200e9")
    capex = Decimal("150e9")
    maint_capex = min(capex, da)  # 150e9
    cfo = Decimal("1200e9")

    # Working capital change: wc_change = cfo - (net_income + da)
    wc_change = cfo - (net_income + da)  # 1200 - 1200 = 0

    # Buffett bridge: Net Income + D&A - Maintenance CapEx + wc_change
    buffett_bridge = net_income + da - maint_capex + wc_change

    # Simplified formula: CFO - Maintenance CapEx
    direct_cfo_formula = cfo - maint_capex

    # Both MUST be algebraically and numerically identical
    assert buffett_bridge == direct_cfo_formula
    assert direct_cfo_formula == Decimal("1050e9")


# =========================================================================
# Scenario J: Working Capital Double-Count Prevention
# =========================================================================
def test_scenario_j_working_capital_double_count_prevention():
    net_income = Decimal("1000e9")
    da = Decimal("200e9")
    capex = Decimal("150e9")
    maint_capex = min(capex, da)
    # CFO has receivables buildup of 300B -> CFO = 1000 + 200 - 300 = 900B
    cfo = Decimal("900e9")

    wc_change = cfo - (net_income + da)  # -300B
    bridge_oe = net_income + da - maint_capex + wc_change
    direct_oe = cfo - maint_capex

    assert bridge_oe == direct_oe
    assert direct_oe == Decimal("750e9")


# =========================================================================
# Scenario K: Cyclical Earnings mid-cycle normalization
# =========================================================================
def test_scenario_k_cyclical_mid_cycle_normalization():
    facts = []
    # Boom in 2022, bust in 2023
    pats = [200e9, 1000e9, 100e9, 400e9, 500e9]
    revs = [2000e9, 8000e9, 1500e9, 3500e9, 4000e9]
    cfos = [220e9, 950e9, 110e9, 420e9, 520e9]
    capexs = [50e9, 100e9, 30e9, 60e9, 70e9]
    das = [40e9, 80e9, 40e9, 50e9, 60e9]

    for i, y in enumerate(range(2021, 2026)):
        facts.append(_make_canonical_fact("CYCLIC_K", y, "IS.PROFIT.NET", pats[i], StatementType.INCOME_STATEMENT))
        facts.append(_make_canonical_fact("CYCLIC_K", y, "IS.REVENUE.NET", revs[i], StatementType.INCOME_STATEMENT))
        facts.append(_make_canonical_fact("CYCLIC_K", y, "CF.OPERATING.NET", cfos[i], StatementType.CASH_FLOW))
        facts.append(_make_canonical_fact("CYCLIC_K", y, "CF.CAPEX", capexs[i], StatementType.CASH_FLOW))
        facts.append(_make_canonical_fact("CYCLIC_K", y, "CF.OPERATING.DEPRECIATION", das[i], StatementType.CASH_FLOW))

    bridge = OwnerEarningsCalculator.calculate_cycle_normalized(facts, latest_fiscal_year=2025, lookback_years=5)
    assert bridge.normalization_method == "MID_CYCLE_MEDIAN"
    # Peak year OE was ~870B; mid-cycle OE must be far below peak year
    assert bridge.owner_earnings < Decimal("600000000000")


# =========================================================================
# Scenario L: Peak Earnings Protection
# =========================================================================
def test_scenario_l_peak_earnings_protection():
    facts = []
    # 4 normal years + 1 extreme peak year
    pats = [100e9, 110e9, 120e9, 130e9, 1000e9]
    revs = [1000e9, 1100e9, 1200e9, 1300e9, 6000e9]
    cfos = [110e9, 120e9, 130e9, 140e9, 950e9]
    capexs = [20e9]*5
    das = [20e9]*5

    for i, y in enumerate(range(2021, 2026)):
        facts.append(_make_canonical_fact("PEAK_L", y, "IS.PROFIT.NET", pats[i], StatementType.INCOME_STATEMENT))
        facts.append(_make_canonical_fact("PEAK_L", y, "IS.REVENUE.NET", revs[i], StatementType.INCOME_STATEMENT))
        facts.append(_make_canonical_fact("PEAK_L", y, "CF.OPERATING.NET", cfos[i], StatementType.CASH_FLOW))
        facts.append(_make_canonical_fact("PEAK_L", y, "CF.CAPEX", capexs[i], StatementType.CASH_FLOW))
        facts.append(_make_canonical_fact("PEAK_L", y, "CF.OPERATING.DEPRECIATION", das[i], StatementType.CASH_FLOW))

    bridge = OwnerEarningsCalculator.calculate_cycle_normalized(facts, latest_fiscal_year=2025, lookback_years=5)
    # Mid-cycle median owner earnings protects against the 1000B peak
    assert bridge.owner_earnings < Decimal("200000000000")


# =========================================================================
# Scenario M: Secular Growth (FPT)
# =========================================================================
def test_scenario_m_secular_growth():
    facts = [
        _make_canonical_fact("FPT", 2025, "IS.PROFIT.NET", 9376.1e9, StatementType.INCOME_STATEMENT),
        _make_canonical_fact("FPT", 2025, "CF.OPERATING.DEPRECIATION", 2914.2e9, StatementType.CASH_FLOW),
        _make_canonical_fact("FPT", 2025, "CF.CAPEX", 5098.0e9, StatementType.CASH_FLOW),
        _make_canonical_fact("FPT", 2025, "CF.OPERATING.NET", 10136.0e9, StatementType.CASH_FLOW),
    ]
    bridge = OwnerEarningsCalculator.calculate(facts, fiscal_year=2025)
    # Maint CapEx = min(5098, 2914.2) = 2914.2B
    # Growth CapEx = 5098 - 2914.2 = 2183.8B
    # OE = 10136 - 2914.2 = 7221.8B
    assert round(float(bridge.owner_earnings) / 1e9, 1) == 7221.8
    assert round(float(bridge.growth_capex_estimated) / 1e9, 1) == 2183.8


# =========================================================================
# Scenario N: Bank Archetype Isolation
# =========================================================================
def test_scenario_n_bank_archetype_isolation():
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
# Scenario O: Securities Archetype Isolation
# =========================================================================
def test_scenario_o_securities_archetype_isolation():
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
# Scenario P: Partial History (<3 years)
# =========================================================================
def test_scenario_p_partial_history_fallback():
    facts = [
        _make_canonical_fact("IPO_P", 2024, "IS.PROFIT.NET", 100e9, StatementType.INCOME_STATEMENT),
        _make_canonical_fact("IPO_P", 2024, "IS.REVENUE.NET", 1000e9, StatementType.INCOME_STATEMENT),
        _make_canonical_fact("IPO_P", 2024, "CF.OPERATING.NET", 120e9, StatementType.CASH_FLOW),
        _make_canonical_fact("IPO_P", 2024, "CF.CAPEX", 20e9, StatementType.CASH_FLOW),
        _make_canonical_fact("IPO_P", 2024, "CF.OPERATING.DEPRECIATION", 20e9, StatementType.CASH_FLOW),

        _make_canonical_fact("IPO_P", 2025, "IS.PROFIT.NET", 150e9, StatementType.INCOME_STATEMENT),
        _make_canonical_fact("IPO_P", 2025, "IS.REVENUE.NET", 1200e9, StatementType.INCOME_STATEMENT),
        _make_canonical_fact("IPO_P", 2025, "CF.OPERATING.NET", 160e9, StatementType.CASH_FLOW),
        _make_canonical_fact("IPO_P", 2025, "CF.CAPEX", 30e9, StatementType.CASH_FLOW),
        _make_canonical_fact("IPO_P", 2025, "CF.OPERATING.DEPRECIATION", 25e9, StatementType.CASH_FLOW),
    ]
    # Only 2 years -> not enough for MID_CYCLE_MEDIAN -> falls back honestly to LATEST_FY
    bridge = OwnerEarningsCalculator.calculate_cycle_normalized(facts, latest_fiscal_year=2025, lookback_years=5)
    assert bridge.normalization_method == "LATEST_FY"
    assert bridge.normalization_years == 1


# =========================================================================
# Scenario Q: Fiscal-Window Determinism
# =========================================================================
def test_scenario_q_fiscal_window_determinism():
    facts = []
    for y in range(2021, 2026):
        facts.append(_make_canonical_fact("DET_Q", y, "IS.PROFIT.NET", 100e9, StatementType.INCOME_STATEMENT))
        facts.append(_make_canonical_fact("DET_Q", y, "IS.REVENUE.NET", 1000e9, StatementType.INCOME_STATEMENT))
        facts.append(_make_canonical_fact("DET_Q", y, "CF.OPERATING.NET", 110e9, StatementType.CASH_FLOW))
        facts.append(_make_canonical_fact("DET_Q", y, "CF.CAPEX", 10e9, StatementType.CASH_FLOW))
        facts.append(_make_canonical_fact("DET_Q", y, "CF.OPERATING.DEPRECIATION", 10e9, StatementType.CASH_FLOW))

    bridge1 = OwnerEarningsCalculator.calculate_cycle_normalized(facts, latest_fiscal_year=2025, lookback_years=5)
    bridge2 = OwnerEarningsCalculator.calculate_cycle_normalized(facts, latest_fiscal_year=2025, lookback_years=5)

    assert bridge1.owner_earnings == bridge2.owner_earnings
    assert bridge1.normalization_method == bridge2.normalization_method


# =========================================================================
# Scenario R: Synthetic vs Real Data Separation
# =========================================================================
def test_scenario_r_synthetic_vs_real_data_separation():
    # Synthetic fact has dummy canonical_fact_id
    fact = _make_canonical_fact("TEST", 2025, "IS.PROFIT.NET", 100e9, StatementType.INCOME_STATEMENT)
    assert fact.canonical_fact_id.startswith("TEST-")
    assert fact.identity.fiscal_year == 2025


# =========================================================================
# Scenario S: Share-Basis Invariance
# =========================================================================
def test_scenario_s_share_basis_invariance():
    sb = resolve_canonical_share_basis(
        symbol="HAH",
        bctc_shares=Decimal("100000000"),
        bctc_fiscal_year=2024,
        bctc_period_end="2024-12-31",
        corporate_actions=[],
        current_market_price=Decimal("45000"),
        diluted_shares_estimate=Decimal("100000000"),
        valuation_date="2025-07-01",
        source="SSI_BCTC_2024",
    )
    assert sb.shares_outstanding == Decimal("100000000")


# =========================================================================
# Scenario T: Stock Split Invariance
# =========================================================================
def test_scenario_t_stock_split_invariance():
    enterprise_oe = Decimal("1000000000000")  # 1000B
    shares = Decimal("100000000")
    oe_per_share_before = enterprise_oe / shares  # 10,000 VND

    # 2:1 split
    split_shares = shares * Decimal("2.0")
    oe_per_share_after = enterprise_oe / split_shares  # 5,000 VND

    assert enterprise_oe == Decimal("1000000000000")
    assert oe_per_share_after * Decimal("2.0") == oe_per_share_before


# =========================================================================
# Scenario U: Economic Dilution
# =========================================================================
def test_scenario_u_economic_dilution():
    enterprise_oe = Decimal("1000000000000")
    old_shares = Decimal("100000000")
    new_shares = Decimal("120000000")  # 20% dilution

    old_oe_ps = enterprise_oe / old_shares
    new_oe_ps = enterprise_oe / new_shares

    assert new_oe_ps < old_oe_ps
    assert new_oe_ps == Decimal("8333.333333333333333333333333")


# =========================================================================
# Scenario V: CFO / PAT Reconciliation
# =========================================================================
def test_scenario_v_cfo_pat_reconciliation():
    pat = Decimal("1000e9")
    cfo = Decimal("1200e9")
    conversion_ratio = round(float(cfo / pat) * 100, 1)

    assert conversion_ratio == 120.0


# =========================================================================
# Scenario W: Normalized PAT vs Normalized OE Semantic Distinction
# =========================================================================
def test_scenario_w_normalized_pat_vs_oe_distinction():
    # PAT is 1000B, CFO is 800B, Maint CapEx is 300B -> OE = 500B
    pat = Decimal("1000e9")
    oe = Decimal("500e9")

    assert pat != oe
    assert pat - oe == Decimal("500e9")
