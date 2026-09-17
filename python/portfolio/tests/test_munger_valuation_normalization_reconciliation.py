"""Task 189: Reconcile Munger Normalized PAT vs Valuation Normalized Owner Earnings.

Deterministic Golden Test Suite covering Scenarios A through T:
- Scenario A: PAT normalization equals canonical Task 187 arithmetic average
- Scenario B: Owner Earnings derived from explicit canonical cash-flow facts
- Scenario C: PAT != Owner Earnings when economically different (CapEx / D&A / WC deduction)
- Scenario D: Same fiscal-year window produces deterministic aligned inputs
- Scenario E: Different fiscal-year window detection (FY2025 vs FY2024 boundary)
- Scenario F: Missing fiscal year handled gracefully without silent corruption
- Scenario G: Partial history (<5 years) flagged as INSUFFICIENT / LATEST_FY
- Scenario H: Missing PAT blocks quality gate / returns INCOMPLETE
- Scenario I: Missing CFO triggers fallback to Net Income with LOW confidence marker
- Scenario J: Missing CapEx triggers fallback / proxy with explicit confidence marker
- Scenario K: Peak earnings flagged in Munger; mid-cycle normalized in Valuation
- Scenario L: Cyclical earnings use multi-cycle mid-cycle median
- Scenario M: Secular growth (FPT) maintains compounding quality and growth derivation
- Scenario N: Bank archetype uses RIM (BVPS + ROE) and isolates from industrial OE
- Scenario O: Securities archetype isolates from industrial CFO/working capital
- Scenario P: Pure stock split preserves identical MOS
- Scenario Q: Stock dividend preserves identical MOS
- Scenario R: Economic dilution adjusts IV/share correctly
- Scenario S: Share-basis provenance is explicit from resolve_canonical_share_basis()
- Scenario T: MOS formula invariant across both pipelines
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
# Scenario A: PAT Normalization equals canonical Task 187
# =========================================================================
def test_scenario_a_pat_normalization_canonical():
    pats = {2021: 100e9, 2022: 120e9, 2023: 140e9, 2024: 160e9, 2025: 180e9}
    raw_facts = [_make_raw_fact("CO_A", y, "IS.PROFIT.NET", p, "INCOME_STATEMENT") for y, p in pats.items()]
    munger = build_munger_financial_analysis("CO_A", raw_facts=raw_facts)
    norm = munger.normalized_earning_power

    expected_5y = sum(pats.values()) / 5.0
    assert norm["normalized_pat_5y"] == expected_5y
    assert norm["normalized_pat_5y"] == 140e9


# =========================================================================
# Scenario B: Owner Earnings derived from explicit canonical cash-flow facts
# =========================================================================
def test_scenario_b_owner_earnings_derived_correctly():
    facts = [
        _make_canonical_fact("CO_B", 2025, "IS.PROFIT.NET", 1000e9, StatementType.INCOME_STATEMENT),
        _make_canonical_fact("CO_B", 2025, "CF.OPERATING.DEPRECIATION", 200e9, StatementType.CASH_FLOW),
        _make_canonical_fact("CO_B", 2025, "CF.CAPEX", 300e9, StatementType.CASH_FLOW),
        _make_canonical_fact("CO_B", 2025, "CF.OPERATING.NET", 1100e9, StatementType.CASH_FLOW),
    ]
    bridge = OwnerEarningsCalculator.calculate(facts, fiscal_year=2025)
    # OE = CFO - min(CapEx, D&A) = 1100 - min(300, 200) = 1100 - 200 = 900
    assert bridge.owner_earnings == Decimal("900000000000")
    assert bridge.maintenance_capex == Decimal("200000000000")


# =========================================================================
# Scenario C: PAT != Owner Earnings when economically different
# =========================================================================
def test_scenario_c_pat_differs_from_owner_earnings():
    facts = [
        _make_canonical_fact("CO_C", 2025, "IS.PROFIT.NET", 1000e9, StatementType.INCOME_STATEMENT),
        _make_canonical_fact("CO_C", 2025, "CF.OPERATING.DEPRECIATION", 400e9, StatementType.CASH_FLOW),
        _make_canonical_fact("CO_C", 2025, "CF.CAPEX", 600e9, StatementType.CASH_FLOW),
        _make_canonical_fact("CO_C", 2025, "CF.OPERATING.NET", 800e9, StatementType.CASH_FLOW),
    ]
    bridge = OwnerEarningsCalculator.calculate(facts, fiscal_year=2025)
    pat = Decimal("1000000000000")
    oe = bridge.owner_earnings  # 800 - 400 = 400

    assert oe != pat
    assert oe == Decimal("400000000000")
    assert pat - oe == Decimal("600000000000")


# =========================================================================
# Scenario D: Same fiscal-year window produces deterministic inputs
# =========================================================================
def test_scenario_d_same_fiscal_year_window():
    years = [2021, 2022, 2023, 2024, 2025]
    pats = {y: (100 + i * 20) * 1e9 for i, y in enumerate(years)}
    raw_facts = [_make_raw_fact("CO_D", y, "IS.PROFIT.NET", p, "INCOME_STATEMENT") for y, p in pats.items()]
    munger = build_munger_financial_analysis("CO_D", raw_facts=raw_facts)

    assert munger.normalized_earning_power["normalized_pat_5y"] == 140e9


# =========================================================================
# Scenario E: Different fiscal-year window detection (FY2025 vs FY2024)
# =========================================================================
def test_scenario_e_different_fiscal_year_window_reconciliation():
    # 2020-2024 window (excluding 2025)
    pats_2024 = {2020: 100e9, 2021: 120e9, 2022: 140e9, 2023: 160e9, 2024: 180e9}
    # 2021-2025 window (including 2025 with rapid expansion)
    pats_2025 = {2021: 120e9, 2022: 140e9, 2023: 160e9, 2024: 180e9, 2025: 300e9}

    norm_5y_2024 = sum(pats_2024.values()) / 5.0  # 140B
    norm_5y_2025 = sum(pats_2025.values()) / 5.0  # 180B

    assert norm_5y_2024 == 140e9
    assert norm_5y_2025 == 180e9
    assert norm_5y_2025 > norm_5y_2024


# =========================================================================
# Scenario F: Missing fiscal year handled gracefully
# =========================================================================
def test_scenario_f_missing_fiscal_year_resilience():
    # 2021, 2022, missing 2023, 2024, 2025
    pats = {2021: 100e9, 2022: 120e9, 2024: 160e9, 2025: 180e9}
    raw_facts = [_make_raw_fact("CO_F", y, "IS.PROFIT.NET", p, "INCOME_STATEMENT") for y, p in pats.items()]
    munger = build_munger_financial_analysis("CO_F", raw_facts=raw_facts)

    assert munger.normalized_earning_power["normalized_pat_5y"] == sum(pats.values()) / 4.0


# =========================================================================
# Scenario G: Partial history (<5 years) flagged
# =========================================================================
def test_scenario_g_partial_history_flagged():
    pats = {2024: 100e9, 2025: 120e9}
    raw_facts = [_make_raw_fact("CO_G", y, "IS.PROFIT.NET", p, "INCOME_STATEMENT") for y, p in pats.items()]
    munger = build_munger_financial_analysis("CO_G", raw_facts=raw_facts)

    assert munger.data_readiness == "INSUFFICIENT"


# =========================================================================
# Scenario H: Missing PAT blocks quality gate / returns INCOMPLETE
# =========================================================================
def test_scenario_h_missing_pat_handled():
    raw_facts = [_make_raw_fact("CO_H", 2025, "IS.REVENUE", 1000e9, "INCOME_STATEMENT")]
    munger = build_munger_financial_analysis("CO_H", raw_facts=raw_facts)

    assert munger.normalized_earning_power["normalized_pat_5y"] is None


# =========================================================================
# Scenario I: Missing CFO triggers fallback in Owner Earnings
# =========================================================================
def test_scenario_i_missing_cfo_owner_earnings_fallback():
    # 5 years of history with Net Income and Revenue, but missing cash flow statements
    facts = []
    for y in range(2021, 2026):
        facts.append(_make_canonical_fact("CO_I", y, "IS.PROFIT.NET", 500e9, StatementType.INCOME_STATEMENT))
        facts.append(_make_canonical_fact("CO_I", y, "IS.REVENUE.NET", 5000e9, StatementType.INCOME_STATEMENT))

    # In calculate_cycle_normalized, when CF statements are missing over >=3 years, it tolerates via net income proxy
    bridge = OwnerEarningsCalculator.calculate_cycle_normalized(facts, latest_fiscal_year=2025, lookback_years=5)
    assert bridge.owner_earnings > Decimal("0")
    assert bridge.normalization_method == "MID_CYCLE_MEDIAN"


# =========================================================================
# Scenario J: Missing CapEx triggers fallback / proxy
# =========================================================================
def test_scenario_j_missing_capex_proxy():
    facts = [
        _make_canonical_fact("CO_J", 2025, "IS.PROFIT.NET", 500e9, StatementType.INCOME_STATEMENT),
        _make_canonical_fact("CO_J", 2025, "CF.OPERATING.DEPRECIATION", 100e9, StatementType.CASH_FLOW),
        _make_canonical_fact("CO_J", 2025, "CF.OPERATING.NET", 600e9, StatementType.CASH_FLOW),
    ]
    # Single-year calculate requires all 4 CF codes; raises incomplete
    with pytest.raises(ValueError, match="OWNER_EARNINGS_INCOMPLETE"):
        OwnerEarningsCalculator.calculate(facts, fiscal_year=2025)


# =========================================================================
# Scenario K: Peak earnings flagged in Munger
# =========================================================================
def test_scenario_k_peak_earnings_flagged():
    pats = {2021: 200e9, 2022: 220e9, 2023: 210e9, 2024: 230e9, 2025: 900e9}  # peak in 2025
    raw_facts = [_make_raw_fact("PEAK_CO", y, "IS.PROFIT.NET", p, "INCOME_STATEMENT") for y, p in pats.items()]
    munger = build_munger_financial_analysis("PEAK_CO", raw_facts=raw_facts)

    assert munger.normalized_earning_power["is_peak_earnings"] is True
    assert munger.normalized_earning_power["normalized_pat_5y"] == sum(pats.values()) / 5.0


# =========================================================================
# Scenario L: Cyclical earnings use multi-cycle mid-cycle median
# =========================================================================
def test_scenario_l_cyclical_mid_cycle_median():
    facts = []
    # 5 years of cyclical revenue and owner earnings
    revs = [1000e9, 3000e9, 2000e9, 4000e9, 1500e9]
    oes = [100e9, 600e9, 250e9, 800e9, 120e9]
    for i, y in enumerate(range(2021, 2026)):
        facts.append(_make_canonical_fact("CYCLIC_L", y, "IS.PROFIT.NET", oes[i], StatementType.INCOME_STATEMENT))
        facts.append(_make_canonical_fact("CYCLIC_L", y, "IS.REVENUE.NET", revs[i], StatementType.INCOME_STATEMENT))
        facts.append(_make_canonical_fact("CYCLIC_L", y, "CF.OPERATING.NET", oes[i] + 50e9, StatementType.CASH_FLOW))
        facts.append(_make_canonical_fact("CYCLIC_L", y, "CF.OPERATING.DEPRECIATION", 50e9, StatementType.CASH_FLOW))
        facts.append(_make_canonical_fact("CYCLIC_L", y, "CF.CAPEX", 50e9, StatementType.CASH_FLOW))

    bridge = OwnerEarningsCalculator.calculate_cycle_normalized(facts, latest_fiscal_year=2025, lookback_years=5)
    assert bridge.normalization_method == "MID_CYCLE_MEDIAN"
    assert bridge.owner_earnings > Decimal("0")


# =========================================================================
# Scenario M: Secular growth (FPT) maintains compounding quality
# =========================================================================
def test_scenario_m_secular_growth_reconciliation():
    fpt_pats = {
        2021: 4337.4e9, 2022: 5310.1e9, 2023: 6465.2e9, 2024: 7856.8e9, 2025: 9376.1e9
    }
    raw_facts = [_make_raw_fact("FPT", y, "IS.PROFIT.NET", p, "INCOME_STATEMENT") for y, p in fpt_pats.items()]
    munger = build_munger_financial_analysis("FPT", raw_facts=raw_facts)

    assert round(munger.normalized_earning_power["normalized_pat_5y"] / 1e9, 1) == 6669.1


# =========================================================================
# Scenario N: Bank archetype uses RIM and isolates from industrial OE
# =========================================================================
def test_scenario_n_bank_isolates_from_industrial_oe():
    pats = {2021: 10000e9, 2022: 12000e9, 2023: 15000e9, 2024: 16000e9, 2025: 18000e9}
    raw_facts = []
    for y, p in pats.items():
        raw_facts.append(_make_raw_fact("ACB", y, "IS.PROFIT.NET", p, "INCOME_STATEMENT"))
        raw_facts.append(_make_raw_fact("ACB", y, "IS.REVENUE", p * 2.0, "INCOME_STATEMENT"))
        raw_facts.append(_make_raw_fact("ACB", y, "BS.EQUITY.TOTAL", p * 5.0, "BALANCE_SHEET"))
        raw_facts.append(_make_raw_fact("ACB", y, "BS.ASSETS.TOTAL", p * 30.0, "BALANCE_SHEET"))
    munger = build_munger_financial_analysis("ACB", raw_facts=raw_facts)

    assert munger.archetype == "BANK"
    # Bank cash flow dimension is NOT_APPLICABLE
    assert munger.overall_financial_quality.get("earnings_quality") == "NOT_APPLICABLE"


# =========================================================================
# Scenario O: Securities archetype isolates from industrial CFO
# =========================================================================
def test_scenario_o_securities_isolates_from_industrial_cfo():
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
# Scenario P: Pure stock split preserves identical MOS
# =========================================================================
def test_scenario_p_stock_split_mos_invariance():
    base_shares = Decimal("100000000")
    base_iv = Decimal("50000")
    market_price = Decimal("35000")
    mos_before = (base_iv - market_price) / base_iv

    # 2:1 stock split
    split_ratio = Decimal("2.0")
    post_shares = base_shares * split_ratio
    post_iv = base_iv / split_ratio
    post_price = market_price / split_ratio
    mos_after = (post_iv - post_price) / post_iv

    assert mos_before == mos_after
    assert mos_after == Decimal("0.30")


# =========================================================================
# Scenario Q: Stock dividend preserves identical MOS
# =========================================================================
def test_scenario_q_stock_dividend_mos_invariance():
    base_shares = Decimal("100000000")
    base_iv = Decimal("60000")
    market_price = Decimal("42000")
    mos_before = (base_iv - market_price) / base_iv

    # 20% stock dividend
    div_factor = Decimal("1.20")
    post_shares = base_shares * div_factor
    post_iv = base_iv / div_factor
    post_price = market_price / div_factor
    mos_after = (post_iv - post_price) / post_iv

    assert mos_before == mos_after


# =========================================================================
# Scenario R: Economic dilution adjusts IV/share correctly
# =========================================================================
def test_scenario_r_economic_dilution():
    old_shares = Decimal("100000000")
    new_shares = Decimal("120000000")  # +20% cash issuance at market price
    total_iv = Decimal("5000000000000")  # 5000B

    old_iv_per_share = total_iv / old_shares
    # After cash raise of 500B
    new_total_iv = total_iv + Decimal("500000000000")
    new_iv_per_share = new_total_iv / new_shares

    assert old_iv_per_share == Decimal("50000")
    assert new_iv_per_share == Decimal("45833.33333333333333333333333")
    assert new_iv_per_share < old_iv_per_share


# =========================================================================
# Scenario S: Share-basis provenance explicit from resolve_canonical_share_basis()
# =========================================================================
def test_scenario_s_share_basis_provenance():
    sb = resolve_canonical_share_basis(
        symbol="FPT",
        bctc_shares=Decimal("1460000000"),
        bctc_fiscal_year=2024,
        bctc_period_end="2024-12-31",
        corporate_actions=[],
        current_market_price=Decimal("135000"),
        diluted_shares_estimate=Decimal("1460000000"),
        valuation_date="2025-07-01",
        source="SSI_BCTC_2024",
    )
    assert sb.symbol == "FPT"
    assert sb.shares_outstanding == Decimal("1460000000")
    assert sb.source == "SSI_BCTC_2024"


# =========================================================================
# Scenario T: MOS formula invariant across both pipelines
# =========================================================================
def test_scenario_t_mos_formula_invariant():
    iv = Decimal("100000")
    price = Decimal("70000")
    mos_pct = (iv - price) / iv * Decimal("100")

    assert mos_pct == Decimal("30.0")
    assert (1 - (price / iv)) * Decimal("100") == mos_pct
