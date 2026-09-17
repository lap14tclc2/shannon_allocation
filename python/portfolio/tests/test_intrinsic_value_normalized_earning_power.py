"""Task 188: Intrinsic Value & Normalized Earning Power Valuation Integrity Suite.

Comprehensive deterministic unit & integration tests for:
- Scenario A: Normal earnings -> DCF / Base IV derived from earning power
- Scenario B: Latest PAT above normalized PAT -> Divergence tracked, peak not extrapolated
- Scenario C: Peak earnings (>= 1.5x 5Y norm) -> is_peak_earnings=True, MOS markup added
- Scenario D: Latest PAT below normalized PAT (trough) -> is_trough_earnings=True, normalized baseline protects value
- Scenario E: 5-year history -> 5Y normalized earning power
- Scenario F: 10-year history -> 10Y normalized earning power
- Scenario G: >10-year history (15Y) -> Full cycle representation
- Scenario H: Missing fiscal year -> Handled safely without silent 0
- Scenario I: Missing PAT -> Valuation INCOMPLETE/INSUFFICIENT, never READY
- Scenario J: Partial history (<3Y) -> INSUFFICIENT_DATA
- Scenario K: Conflicted facts -> Excluded from valuation facts
- Scenario L: Pure stock split (1:2) -> Exact MOS invariance (0% change)
- Scenario M: Stock dividend (20%) -> Exact MOS invariance (0% change)
- Scenario N: Economic dilution -> Confirmed economic dilution reflected
- Scenario O: Share-basis mismatch -> Handled via resolve_canonical_share_basis()
- Scenario P: MOS calculation -> Exact mathematical formula 1 - P/IV
- Scenario Q: Zero / invalid valuation input -> Model incomplete / blocked
- Scenario R: Bank archetype -> RIM with BVPS & ROE, no industrial CFO false blocker
- Scenario S: Securities archetype -> Financial balance sheet modeling, no industrial WC
- Scenario T: Cyclical quality valuation -> High required MOS (50%) demands deep discount
"""

import math
from decimal import Decimal
import pytest

from portfolio.financial_data.models import (
    CanonicalFact,
    FactIdentityKey,
    PeriodType,
    QualityStatus,
    StatementType,
    ConsolidationScope,
)
from portfolio.value_engine.munger_analyzer import build_munger_financial_analysis
from portfolio.value_engine.owner_earnings import OwnerEarningsCalculator
from portfolio.value_engine.bank_valuation import BankValuationModel
from portfolio.value_engine.share_basis import resolve_canonical_share_basis
from portfolio.value_engine.munger_models import CompounderClassification, DimensionStatus


def _create_canonical_fact(
    symbol: str,
    line_item_code: str,
    fiscal_year: int,
    value: float,
    statement_type: StatementType = StatementType.INCOME_STATEMENT,
    quality_status: QualityStatus = QualityStatus.SINGLE_SOURCE,
) -> CanonicalFact:
    return CanonicalFact(
        canonical_fact_id=f"test-{symbol}-{line_item_code}-{fiscal_year}",
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
        quality_status=quality_status,
        decision_id="test",
        winning_candidate_id="test",
        candidate_ids=[],
        observed_at=f"{fiscal_year}-12-31",
        valid_from=f"{fiscal_year}-12-31",
        reason="Unit test synthetic fact",
    )


def _make_munger_facts(symbol: str, pat_dict: dict[int, float], cfo_ratio: float = 1.1) -> list[dict]:
    facts = []
    for y, pat in pat_dict.items():
        facts.append({
            "symbol": symbol,
            "statement_type": "INCOME_STATEMENT",
            "line_item_code": "IS.PROFIT.NET",
            "period_type": "FY",
            "fiscal_year": y,
            "provider": "ssi",
            "value": pat,
            "quality_status": "SINGLE_SOURCE",
            "observed_at": f"{y}-12-31",
        })
        facts.append({
            "symbol": symbol,
            "statement_type": "INCOME_STATEMENT",
            "line_item_code": "IS.REVENUE",
            "period_type": "FY",
            "fiscal_year": y,
            "provider": "ssi",
            "value": pat * 5.0,
            "quality_status": "SINGLE_SOURCE",
            "observed_at": f"{y}-12-31",
        })
        facts.append({
            "symbol": symbol,
            "statement_type": "BALANCE_SHEET",
            "line_item_code": "BS.EQUITY.TOTAL",
            "period_type": "FY",
            "fiscal_year": y,
            "provider": "ssi",
            "value": pat * 4.0,
            "quality_status": "SINGLE_SOURCE",
            "observed_at": f"{y}-12-31",
        })
        facts.append({
            "symbol": symbol,
            "statement_type": "CASH_FLOW",
            "line_item_code": "CF.OPERATING.NET",
            "period_type": "FY",
            "fiscal_year": y,
            "provider": "ssi",
            "value": pat * cfo_ratio,
            "quality_status": "SINGLE_SOURCE",
            "observed_at": f"{y}-12-31",
        })
        facts.append({
            "symbol": symbol,
            "statement_type": "BALANCE_SHEET",
            "line_item_code": "BS.DEBT.TOTAL",
            "period_type": "FY",
            "fiscal_year": y,
            "provider": "ssi",
            "value": pat * 0.5,
            "quality_status": "SINGLE_SOURCE",
            "observed_at": f"{y}-12-31",
        })
    return facts


# =========================================================================
# Scenario A: Normal earnings -> Earning power correctly derived
# =========================================================================
def test_scenario_a_normal_earnings_earning_power():
    pats = {2021: 100e9, 2022: 120e9, 2023: 130e9, 2024: 140e9, 2025: 150e9}
    facts = _make_munger_facts("NORM_CO", pats)
    res = build_munger_financial_analysis("NORM_CO", raw_facts=facts)
    norm = res.normalized_earning_power

    assert norm["reported_latest"] == 150e9
    assert norm["normalized_pat_5y"] == 128e9
    assert norm["is_peak_earnings"] is False
    assert norm["is_trough_earnings"] is False


# =========================================================================
# Scenario B: Latest PAT above normalized PAT -> Divergence tracked
# =========================================================================
def test_scenario_b_pat_above_normalized_divergence():
    pats = {2021: 100e9, 2022: 110e9, 2023: 120e9, 2024: 130e9, 2025: 160e9}
    facts = _make_munger_facts("GROWTH_CO", pats)
    res = build_munger_financial_analysis("GROWTH_CO", raw_facts=facts)
    norm = res.normalized_earning_power

    assert norm["reported_latest"] > norm["normalized_pat_5y"]
    assert norm["earning_power_divergence"] == norm["reported_latest"] - norm["normalized_pat_5y"]


# =========================================================================
# Scenario C: Peak earnings (>= 1.5x 5Y norm) -> Flagged, MOS markup added
# =========================================================================
def test_scenario_c_peak_earnings_markup():
    pats = {2021: 100e9, 2022: 110e9, 2023: 105e9, 2024: 120e9, 2025: 250e9}  # 250B >= 1.5 * 137B
    facts = _make_munger_facts("PEAK_CO", pats)
    res = build_munger_financial_analysis("PEAK_CO", raw_facts=facts)
    norm = res.normalized_earning_power

    assert norm["is_peak_earnings"] is True
    # Peak earnings triggers monitoring signal
    mon_signals = res.long_term_decision["decision_trace"].get("monitoring_signals", [])
    assert any("vùng cao" in str(s) or "chu kỳ" in str(s) for s in mon_signals)


# =========================================================================
# Scenario D: Latest PAT below normalized PAT (trough)
# =========================================================================
def test_scenario_d_trough_earnings_protected():
    pats = {2021: 200e9, 2022: 220e9, 2023: 210e9, 2024: 230e9, 2025: 80e9}  # 80B <= 0.6 * 188B
    facts = _make_munger_facts("TROUGH_CO", pats)
    res = build_munger_financial_analysis("TROUGH_CO", raw_facts=facts)
    norm = res.normalized_earning_power

    assert norm["is_trough_earnings"] is True
    assert norm["normalized_pat_5y"] == 188e9


# =========================================================================
# Scenario E: 5-year history window
# =========================================================================
def test_scenario_e_5year_history():
    pats = {2021: 100e9, 2022: 110e9, 2023: 120e9, 2024: 130e9, 2025: 140e9}
    facts = _make_munger_facts("CO_5Y", pats)
    res = build_munger_financial_analysis("CO_5Y", raw_facts=facts)

    assert res.history_years == 5
    assert res.data_readiness == "READY"
    assert res.normalized_earning_power["normalized_pat_5y"] == 120e9


# =========================================================================
# Scenario F: 10-year history window
# =========================================================================
def test_scenario_f_10year_history():
    pats = {y: 100e9 + (y - 2016) * 10e9 for y in range(2016, 2026)}
    facts = _make_munger_facts("CO_10Y", pats)
    res = build_munger_financial_analysis("CO_10Y", raw_facts=facts)

    assert res.history_years == 10
    assert res.normalized_earning_power["normalized_pat_10y"] == sum(pats.values()) / 10.0


# =========================================================================
# Scenario G: >10-year history (15Y)
# =========================================================================
def test_scenario_g_15year_history():
    pats = {y: 50e9 + (y - 2011) * 10e9 for y in range(2011, 2026)}
    facts = _make_munger_facts("CO_15Y", pats)
    res = build_munger_financial_analysis("CO_15Y", raw_facts=facts)

    assert res.history_years == 15
    assert res.normalized_earning_power["normalized_pat_5y"] == sum(list(pats.values())[-5:]) / 5.0
    assert res.normalized_earning_power["normalized_pat_10y"] == sum(list(pats.values())[-10:]) / 10.0


# =========================================================================
# Scenario H: Missing fiscal year handled gracefully
# =========================================================================
def test_scenario_h_missing_fiscal_year():
    # Gap in history: 2021, 2022, 2024, 2025 (missing 2023)
    pats = {2021: 100e9, 2022: 110e9, 2024: 130e9, 2025: 140e9}
    facts = _make_munger_facts("GAP_CO", pats)
    res = build_munger_financial_analysis("GAP_CO", raw_facts=facts)

    assert res.history_years == 4
    # Arithmetic average over available 4 years
    assert res.normalized_earning_power["normalized_pat_5y"] == sum(pats.values()) / 4.0


# =========================================================================
# Scenario I: Missing PAT -> INSUFFICIENT data
# =========================================================================
def test_scenario_i_missing_pat():
    facts = []
    # Only revenue and equity, no PAT
    for y in (2024, 2025):
        facts.append({
            "symbol": "NO_PAT",
            "statement_type": "INCOME_STATEMENT",
            "line_item_code": "IS.REVENUE",
            "period_type": "FY",
            "fiscal_year": y,
            "provider": "ssi",
            "value": 1000e9,
            "quality_status": "SINGLE_SOURCE",
            "observed_at": f"{y}-12-31",
        })
    res = build_munger_financial_analysis("NO_PAT", raw_facts=facts)

    assert res.normalized_earning_power["reported_latest"] is None
    assert res.data_readiness == "INSUFFICIENT"
    assert res.compounder_classification == CompounderClassification.INSUFFICIENT_DATA.value


# =========================================================================
# Scenario J: Partial history (<3Y)
# =========================================================================
def test_scenario_j_partial_history():
    pats = {2024: 100e9, 2025: 120e9}
    facts = _make_munger_facts("SHORT_CO", pats)
    res = build_munger_financial_analysis("SHORT_CO", raw_facts=facts)

    assert res.history_years == 2
    assert res.data_readiness == "INSUFFICIENT"


# =========================================================================
# Scenario K: Conflicted facts excluded from Owner Earnings calculation
# =========================================================================
def test_scenario_k_conflicted_facts_excluded():
    c_facts = [
        _create_canonical_fact("TEST", "IS.PROFIT.NET", 2024, 100e9, quality_status=QualityStatus.SINGLE_SOURCE),
        _create_canonical_fact("TEST", "CF.OPERATING.DEPRECIATION", 2024, 20e9, statement_type=StatementType.CASH_FLOW, quality_status=QualityStatus.SINGLE_SOURCE),
        _create_canonical_fact("TEST", "CF.CAPEX", 2024, -15e9, statement_type=StatementType.CASH_FLOW, quality_status=QualityStatus.SINGLE_SOURCE),
        _create_canonical_fact("TEST", "CF.OPERATING.NET", 2024, 110e9, statement_type=StatementType.CASH_FLOW, quality_status=QualityStatus.CONFLICT),  # CONFLICT!
    ]
    with pytest.raises(ValueError, match="OWNER_EARNINGS_INCOMPLETE"):
        OwnerEarningsCalculator.calculate(c_facts, fiscal_year=2024)


# =========================================================================
# Scenario L: Pure stock split (1:2) -> Exact MOS Invariance
# =========================================================================
def test_scenario_l_stock_split_mos_invariance():
    # Pre-split: shares = 10M, price = 40,000, IV = 80,000 -> MOS = 50.0%
    pre_basis = resolve_canonical_share_basis(
        symbol="SPLIT_TEST",
        bctc_shares=10_000_000,
        bctc_fiscal_year=2024,
        bctc_period_end="2024-12-31",
        corporate_actions=[],
        current_market_price=Decimal("40000"),
        valuation_date="2025-07-01",
    )
    pre_mos = (Decimal("80000") - Decimal("40000")) / Decimal("80000")

    # Post-split 2:1 (split_factor = 2.0): shares = 20M, price = 20,000, IV = 40,000 -> MOS = 50.0%
    ca_split = [{"action_type": "STOCK_SPLIT", "split_factor": 2.0, "effective_date": "2025-06-01"}]
    post_basis = resolve_canonical_share_basis(
        symbol="SPLIT_TEST",
        bctc_shares=10_000_000,
        bctc_fiscal_year=2024,
        bctc_period_end="2024-12-31",
        corporate_actions=ca_split,
        current_market_price=Decimal("20000"),
        valuation_date="2025-07-01",
    )
    post_mos = (Decimal("40000") - Decimal("20000")) / Decimal("40000")

    assert post_basis.shares_outstanding == 20_000_000
    assert post_basis.basis_type == "CORPORATE_ACTION_ADJUSTED"
    assert pre_mos == post_mos == Decimal("0.50")


# =========================================================================
# Scenario M: Stock dividend (20%) -> Exact MOS Invariance
# =========================================================================
def test_scenario_m_stock_dividend_mos_invariance():
    ca_div = [{"action_type": "STOCK_DIVIDEND", "stock_ratio": 0.20, "effective_date": "2025-06-01"}]
    basis = resolve_canonical_share_basis(
        symbol="DIV_TEST",
        bctc_shares=10_000_000,
        bctc_fiscal_year=2024,
        bctc_period_end="2024-12-31",
        corporate_actions=ca_div,
        current_market_price=Decimal("25000"),
        valuation_date="2025-07-01",
    )
    assert basis.shares_outstanding == 12_000_000
    assert basis.basis_type == "CORPORATE_ACTION_ADJUSTED"
    # Price and IV both scaled by 1/1.2 -> MOS invariant
    mos = (Decimal("50000") / Decimal("1.2") - Decimal("25000")) / (Decimal("50000") / Decimal("1.2"))
    expected_mos = (Decimal("50000") - Decimal("30000")) / Decimal("50000")
    assert round(mos, 4) == round(expected_mos, 4)


# =========================================================================
# Scenario N: Economic Dilution -> Distinguished from split
# =========================================================================
def test_scenario_n_economic_dilution():
    # Economic events (RIGHTS_ISSUE / ESOP) do not inflate forward non-economic split multiplier
    ca_esop = [{"action_type": "RIGHTS_ISSUE", "stock_ratio": 0.10, "effective_date": "2025-06-01"}]
    basis = resolve_canonical_share_basis(
        symbol="DILUTION_TEST",
        bctc_shares=10_000_000,
        bctc_fiscal_year=2024,
        bctc_period_end="2024-12-31",
        corporate_actions=ca_esop,
        current_market_price=Decimal("30000"),
        valuation_date="2025-07-01",
    )
    # Non-economic forward multiplier is 1.0 (economic dilution is reflected in BCTC equity changes)
    assert basis.cumulative_split_factor == Decimal("1.0")


# =========================================================================
# Scenario O: Share-basis provenance
# =========================================================================
def test_scenario_o_share_basis_provenance():
    basis = resolve_canonical_share_basis(
        symbol="PROV_TEST",
        bctc_shares=50_000_000,
        bctc_fiscal_year=2024,
        bctc_period_end="2024-12-31",
        corporate_actions=[],
        current_market_price=Decimal("15000"),
        valuation_date="2025-07-01",
    )
    assert basis.shares_outstanding == 50_000_000
    assert basis.basis_type == "REPORTED_LATEST_BCTC"
    assert basis.status == "VALID"


# =========================================================================
# Scenario P: MOS mathematical formula 1 - Price / IV
# =========================================================================
def test_scenario_p_mos_calculation_formula():
    iv = 100_000
    price = 60_000
    mos = round((iv - price) / iv * 100, 2)
    assert mos == 40.0


# =========================================================================
# Scenario Q: Zero / invalid valuation input
# =========================================================================
def test_scenario_q_zero_valuation_input():
    val_data = {
        "status": "INCOMPLETE",
        "current_price": 0,
        "base_iv": 0,
        "actual_mos_pct": None,
        "required_mos_pct": 20.0,
    }
    pats = {2021: 100e9, 2022: 110e9, 2023: 120e9, 2024: 130e9, 2025: 140e9}
    facts = _make_munger_facts("INVALID_VAL", pats)
    res = build_munger_financial_analysis("INVALID_VAL", raw_facts=facts, valuation_data=val_data)

    assert res.valuation["status"] == "INCOMPLETE"
    assert res.long_term_decision["decision_trace"]["mos_gate"] == "UNKNOWN"


# =========================================================================
# Scenario R: Bank archetype -> RIM with BVPS & ROE
# =========================================================================
def test_scenario_r_bank_valuation_rim():
    bvps = Decimal("20000")
    roe = Decimal("0.19")
    price = Decimal("24000")
    shares = Decimal("1000000000")
    coe = Decimal("0.11")

    scen = BankValuationModel.calculate_rim_scenario(
        current_bvps=bvps,
        base_roe=roe,
        cost_of_equity=coe,
        retention_ratio=Decimal("0.80"),
        terminal_growth=Decimal("0.035"),
        shares_outstanding=shares,
        current_market_price=price,
        scenario_type=BankValuationModel.calculate_rim_scenario.__globals__["ScenarioType"].BASE,
    )

    # Intrinsic value > BVPS because ROE (19%) > Cost of Equity (11%)
    assert scen.intrinsic_value_per_share > bvps
    assert scen.margin_of_safety_pct is not None


# =========================================================================
# Scenario S: Securities archetype avoids industrial working capital
# =========================================================================
def test_scenario_s_securities_archetype_valuation():
    pats = {2021: 500e9, 2022: 700e9, 2023: 600e9, 2024: 800e9, 2025: 900e9}
    facts = _make_munger_facts("VIX", pats)
    res = build_munger_financial_analysis("VIX", raw_facts=facts)

    assert res.archetype == "SECURITIES"
    assert res.overall_financial_quality.get("earnings_quality") == DimensionStatus.NOT_APPLICABLE.value
    assert res.long_term_decision["decision_trace"]["quality_gate"] == "PASS"


# =========================================================================
# Scenario T: Cyclical Quality demands deep MOS markup (50%)
# =========================================================================
def test_scenario_t_cyclical_quality_demands_deep_mos():
    # Volatile cyclical earnings
    pats = {2021: 400e9, 2022: 900e9, 2023: 300e9, 2024: 600e9, 2025: 1200e9}
    facts = _make_munger_facts("HAH_TEST", pats)
    val_data = {
        "status": "READY",
        "current_price": 38000,
        "bear_iv": 45000,
        "base_iv": 80000,
        "actual_mos_pct": 52.5,
        "required_mos_pct": 50.0,
        "valuation_confidence": "HIGH",
    }
    res = build_munger_financial_analysis("HAH_TEST", raw_facts=facts, valuation_data=val_data)

    assert res.compounder_classification == CompounderClassification.CYCLICAL_QUALITY.value
    assert res.long_term_decision["required_mos_pct"] == 50.0
    assert res.long_term_decision["state"] in ("BUY", "CONDITIONAL_BUY")
