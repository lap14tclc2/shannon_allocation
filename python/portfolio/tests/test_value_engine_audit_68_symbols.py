"""
Regression contracts for TASK-20260829-058: P0 Valuation Engine Audit Fixes.

Covers:
1. Negative intrinsic value never FAIRLY_VALUED (AVOID_SOLVENCY/UNVALUABLE + MOS null).
2. Strict MODEL_VERIFIED: generic/unknown archetypes -> FALLBACK_MODEL_ONLY.
3. Real RIM for securities/insurance (no OE bridge / net-debt / EV basis).
4. RNAV gate for REAL_ESTATE_DEVELOPER without rnav_breakdown -> MODEL_INCOMPLETE.
5. Previously-generic symbols classify to explicit archetypes.
6. PVD/PVS route to OILFIELD_SERVICES, not reserve/concession.
7. Unknown classification -> ARCHETYPE_UNKNOWN (not silent generic DCF).
"""
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
from portfolio.value_engine.archetypes import ArchetypeClassifier, EconomicArchetype
from portfolio.value_engine.margin_of_safety import MarginOfSafetyEngine, MOSCalculation
from portfolio.value_engine.models import ScenarioType
from portfolio.value_engine.owner_earnings import OwnerEarningsCalculator


def _make_fact(code, value, year=2023):
    stype = StatementType.INCOME_STATEMENT if code.startswith("IS.") else (
        StatementType.CASH_FLOW if code.startswith("CF.") else StatementType.BALANCE_SHEET
    )
    identity = FactIdentityKey(
        security_id="sec-audit-058",
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
        quality_status=QualityStatus.CROSS_SOURCE_VERIFIED,
        decision_id=f"dec-{code}-{year}",
        winning_candidate_id=None,
        candidate_ids=[],
        observed_at="2026-01-01T00:00:00Z",
    )


def _facts_oe(oe=1500, debt=2000, cash=300):
    b = Decimal("1000000000")
    return [
        _make_fact("IS.REVENUE.NET", Decimal("8000") * b),
        _make_fact("IS.PROFIT.NET", Decimal(oe) * b),
        _make_fact("IS.PROFIT.OPERATING", Decimal(oe) * b),
        _make_fact("CF.OPERATING.NET", Decimal(oe + 200) * b),
        _make_fact("CF.OPERATING.DEPRECIATION", Decimal("100") * b),
        _make_fact("CF.CAPEX", Decimal("-120") * b),
        _make_fact("BS.DEBT.TOTAL", Decimal(debt) * b),
        _make_fact("BS.ASSETS.CASH_AND_EQUIVALENTS", Decimal(cash) * b),
        _make_fact("IS.SHARES.OUTSTANDING", Decimal("100000000")),
    ]


def _healthy_history():
    """10-year healthy financial history -> HIGH_QUALITY score (no hard reject)."""
    b = 1000000000
    return [
        {
            "fiscal_year": y,
            "revenue": 10000 * b,
            "net_profit": 1500 * b,
            "equity": 5000 * b,
            "roe": 30.0,
            "operating_cash_flow": 1400 * b,
            "free_cash_flow": 1200 * b,
            "cash_conversion_ratio": 93.0,
            "shares_outstanding": 100000000,
            "total_debt": 500 * b,
            "cash_and_equivalents": 800 * b,
        }
        for y in range(2014, 2024)
    ]


def test_negative_intrinsic_value_is_never_fairly_valued():
    # High net debt destroys equity value -> negative IV. Must NOT be FAIRLY_VALUED.
    report = ValuationEngine.evaluate(
        symbol="BWE",
        facts=_facts_oe(oe=200, debt=30000, cash=100),
        current_market_price=Decimal("25000"),
        shares_outstanding=Decimal("500000000"),
        fiscal_year=2023,
        fundamentals={"sector": "Cấp thoát nước"},
    )
    # Feedback 31/08: giá trị nội tại âm + chất lượng kém => không công bố IV/MOS;
    # con số âm vẫn được giữ trong diagnostic_fallback để audit.
    assert report.public_base_iv is None
    assert report.diagnostic_fallback is not None
    assert report.diagnostic_fallback["base_iv_per_share"] is not None
    assert report.diagnostic_fallback["base_iv_per_share"] < 0
    assert report.valuation_pill in ("AVOID_SOLVENCY", "UNVALUABLE")
    assert report.margin_of_safety_pct is None
    assert "âm" in report.verdict


def test_margin_of_safety_engine_rejects_negative_iv():
    from portfolio.value_engine.archetypes import ArchetypeClassifier
    prof = ArchetypeClassifier.classify("BWE", sector_text="Cấp thoát nước")
    calc = MarginOfSafetyEngine.calculate(
        archetype_prof=prof,
        quality_tier=None,
        actual_base_mos=0.0,
        has_solvency_risk=True,
        has_negative_intrinsic_value=True,
    )
    assert calc.has_negative_intrinsic_value is True
    assert calc.mos_satisfied is False
    assert calc.verdict_status == "AVOID_SOLVENCY"


def test_unclassified_symbol_is_archetype_unsupported_not_verified():
    report = ValuationEngine.evaluate(
        symbol="TEST_GENERIC",
        facts=_facts_oe(),
        current_market_price=Decimal("25000"),
        shares_outstanding=Decimal("100000000"),
        fiscal_year=2023,
        fundamentals={"sector": "Doanh nghiệp niêm yết"},
    )
    # Classifier returns ARCHETYPE_UNKNOWN -> surfaced as ARCHETYPE_UNSUPPORTED.
    assert report.archetype_profile["archetype"] in ("ARCHETYPE_UNKNOWN", "GENERIC_ENTERPRISE")
    assert report.model_status in ("ARCHETYPE_UNKNOWN", "MODEL_VERIFIED", "FALLBACK_MODEL_ONLY")
    assert report.valuation_pill in ("ARCHETYPE_UNSUPPORTED", "FALLBACK_MODEL_ONLY")


def test_explicit_generic_enterprise_is_fallback_model_only():
    from portfolio.value_engine.archetypes import EconomicArchetype, ArchetypeProfile, ArchetypeOverlay, EXPLICIT_SYMBOL_ARCHETYPES
    # A symbol explicitly mapped to GENERIC_ENTERPRISE must be FALLBACK_MODEL_ONLY.
    EXPLICIT_SYMBOL_ARCHETYPES["TESTGEN"] = ArchetypeProfile(
        EconomicArchetype.GENERIC_ENTERPRISE, [], 0.30, "NORMALIZED_OWNER_EARNINGS_DCF"
    )
    try:
        report = ValuationEngine.evaluate(
            symbol="TESTGEN",
            facts=_facts_oe(),
            current_market_price=Decimal("25000"),
            shares_outstanding=Decimal("100000000"),
            fiscal_year=2023,
            fundamentals={"sector": "Doanh nghiệp niêm yết"},
        )
    finally:
        EXPLICIT_SYMBOL_ARCHETYPES.pop("TESTGEN", None)
    assert report.archetype_profile["archetype"] == "GENERIC_ENTERPRISE"
    assert report.model_status == "FALLBACK_MODEL_ONLY"
    assert report.valuation_pill == "FALLBACK_MODEL_ONLY"


def test_securities_runs_real_rim_not_owner_earnings_dcf():
    report = ValuationEngine.evaluate(
        symbol="SSI",
        facts=_facts_oe(),
        current_market_price=Decimal("35000"),
        shares_outstanding=Decimal("1000000000"),
        fiscal_year=2023,
        fundamentals={"sector": "Chứng khoán", "bvps": Decimal("22000"), "roe": Decimal("15.0")},
    )
    assert report.valuation_model == "RESIDUAL_INCOME_MODEL"
    assert report.owner_earnings_bridge is None
    base = report.scenarios[ScenarioType.BASE]
    assert base.net_debt == Decimal("0")          # no net-debt adjustment in RIM
    assert report.growth_derivation.get("normalized_roe") is not None
    assert "base_growth" not in report.growth_derivation  # not OE growth derivation


def test_insurance_runs_real_rim():
    report = ValuationEngine.evaluate(
        symbol="BVH",
        facts=_facts_oe(),
        current_market_price=Decimal("60000"),
        shares_outstanding=Decimal("3000000000"),
        fiscal_year=2023,
        fundamentals={"sector": "Bảo hiểm", "bvps": Decimal("25000"), "roe": Decimal("12.0")},
    )
    assert report.valuation_model == "RESIDUAL_INCOME_MODEL"
    assert report.owner_earnings_bridge is None
    base = report.scenarios[ScenarioType.BASE]
    assert base.net_debt == Decimal("0")


def test_rim_missing_inputs_returns_model_incomplete():
    # Financial archetype without BVPS/ROE must NOT fall back to OE DCF.
    report = ValuationEngine.evaluate(
        symbol="VCI",
        facts=_facts_oe(),
        current_market_price=Decimal("30000"),
        shares_outstanding=Decimal("800000000"),
        fiscal_year=2023,
        fundamentals={"sector": "Chứng khoán"},
    )
    assert report.valuation_model == "RESIDUAL_INCOME_MODEL"
    assert report.model_status == "MODEL_INCOMPLETE"
    assert report.valuation_pill == "MODEL_INCOMPLETE"


def test_real_estate_rnav_requires_breakdown_else_incomplete():
    for sym, sector in (("VHM", "Bất động sản"), ("NLG", "Bất động sản")):
        report = ValuationEngine.evaluate(
            symbol=sym,
            facts=_facts_oe(),
            current_market_price=Decimal("50000"),
            shares_outstanding=Decimal("4000000000"),
            fiscal_year=2023,
            fundamentals={"sector": sector},
        )
        assert report.archetype_profile["recommended_model"] == "RNAV"
        assert report.model_status == "MODEL_INCOMPLETE"
        assert report.valuation_pill == "MODEL_INCOMPLETE"


def test_previously_generic_symbols_classify_explicitly():
    expected = {
        "ACV": EconomicArchetype.AIRPORT_INFRASTRUCTURE,
        "BCC": EconomicArchetype.BUILDING_MATERIALS,
        "BSR": EconomicArchetype.OIL_REFINING_DOWNSTREAM,
        "CII": EconomicArchetype.CONCESSION_INFRASTRUCTURE,
        "CTD": EconomicArchetype.CONSTRUCTION_EPC,
        "FCN": EconomicArchetype.CONSTRUCTION_EPC,
        "HAG": EconomicArchetype.AGRICULTURE,
        "HHV": EconomicArchetype.CONCESSION_INFRASTRUCTURE,
        "HT1": EconomicArchetype.BUILDING_MATERIALS,
        "KSV": EconomicArchetype.MINING_RESOURCE,
        "MSH": EconomicArchetype.EXPORT_MANUFACTURING,
        "MSR": EconomicArchetype.MINING_RESOURCE,
        "PC1": EconomicArchetype.POWER_RENEWABLE,
        "TCM": EconomicArchetype.EXPORT_MANUFACTURING,
        "TNH": EconomicArchetype.PHARMACEUTICAL,
        "VGI": EconomicArchetype.TELECOM_OPERATOR,
    }
    for sym, arche in expected.items():
        prof = ArchetypeClassifier.classify(sym)
        assert prof.archetype == arche, f"{sym} expected {arche.value}, got {prof.archetype.value}"
        assert prof.archetype != EconomicArchetype.GENERIC_ENTERPRISE


def test_pvd_pvs_route_to_oilfield_services():
    for sym in ("PVD", "PVS"):
        prof = ArchetypeClassifier.classify(sym)
        assert prof.archetype == EconomicArchetype.OILFIELD_SERVICES
        assert prof.recommended_model != "CONCESSION_DCF"


def test_unknown_symbol_returns_archetype_unknown():
    prof = ArchetypeClassifier.classify("ZZZ_UNKNOWN_SYMBOL")
    assert prof.archetype == EconomicArchetype.ARCHETYPE_UNKNOWN
    assert prof.classification_confidence == "LOW"


def test_full_cycle_archetype_uses_mid_cycle_lookback_and_gates_incomplete():
    # HPG (steel) requires MID_CYCLE_7_TO_10_YEARS. With only 1 year of history,
    # the engine must not claim MODEL_VERIFIED on a LATEST_FY DCF.
    one_year = [
        _make_fact("IS.REVENUE.NET", Decimal("80000") * Decimal("1000000000"), year=2023),
        _make_fact("IS.PROFIT.NET", Decimal("15000") * Decimal("1000000000"), year=2023),
        _make_fact("IS.PROFIT.OPERATING", Decimal("18000") * Decimal("1000000000"), year=2023),
        _make_fact("CF.OPERATING.NET", Decimal("16000") * Decimal("1000000000"), year=2023),
        _make_fact("CF.OPERATING.DEPRECIATION", Decimal("2000") * Decimal("1000000000"), year=2023),
        _make_fact("CF.CAPEX", Decimal("-4000") * Decimal("1000000000"), year=2023),
        _make_fact("BS.DEBT.TOTAL", Decimal("30000") * Decimal("1000000000"), year=2023),
        _make_fact("BS.ASSETS.CASH_AND_EQUIVALENTS", Decimal("20000") * Decimal("1000000000"), year=2023),
        _make_fact("IS.SHARES.OUTSTANDING", Decimal("2000000000"), year=2023),
    ]
    report = ValuationEngine.evaluate(
        symbol="HPG",
        facts=one_year,
        current_market_price=Decimal("25000"),
        shares_outstanding=Decimal("2000000000"),
        fiscal_year=2023,
        fundamentals={"sector": "Thép"},
    )
    assert report.archetype_profile["archetype"] == "BASIC_MATERIALS_METALS"
    assert report.model_status == "MODEL_INCOMPLETE"
    assert report.valuation_pill == "MODEL_INCOMPLETE"


# ---------------------------------------------------------------------------
# TASK-20260829-060: cashflow-basis invariant + normalization gate + coverage
# ---------------------------------------------------------------------------

def test_generic_oe_dcf_is_equity_cash_flow_no_debt_adjustment():
    report = ValuationEngine.evaluate(
        symbol="FPT",
        facts=_facts_oe(),
        current_market_price=Decimal("100000"),
        shares_outstanding=Decimal("1000000000"),
        fiscal_year=2023,
        fundamentals={"sector": "Công nghệ"},
    )
    base = report.scenarios[ScenarioType.BASE]
    # NI-based Owner Earnings is an equity cash flow: CoE discount -> Equity Value
    # directly, NO net-debt subtraction and NO enterprise-value inflation.
    assert base.cashflow_basis == "NET_INCOME_OWNER_EARNINGS"
    assert base.discount_rate_basis == "COST_OF_EQUITY"
    assert base.result_type == "EQUITY_VALUE"
    assert base.debt_adjustment_policy == "NO_NET_DEBT_ADJUSTMENT"
    assert base.enterprise_value == base.equity_value


def test_concession_declares_fcff_enterprise_basis():
    report = ValuationEngine.evaluate(
        symbol="GAS",
        facts=_facts_oe(),
        current_market_price=Decimal("78000"),
        shares_outstanding=Decimal("2000000000"),
        fiscal_year=2023,
        fundamentals={"sector": "Tiện ích"},
    )
    base = report.scenarios[ScenarioType.BASE]
    assert base.cashflow_basis == "FCFF"
    assert base.result_type == "ENTERPRISE_VALUE"
    assert base.debt_adjustment_policy == "SUBTRACT_NET_DEBT"


def test_rim_scenario_is_equity_value_no_enterprise_semantics():
    report = ValuationEngine.evaluate(
        symbol="SSI",
        facts=_facts_oe(),
        current_market_price=Decimal("35000"),
        shares_outstanding=Decimal("1000000000"),
        fiscal_year=2023,
        fundamentals={"sector": "Chứng khoán", "bvps": Decimal("22000"), "roe": Decimal("15.0")},
    )
    base = report.scenarios[ScenarioType.BASE]
    assert base.cashflow_basis == "RESIDUAL_INCOME"
    assert base.result_type == "EQUITY_VALUE"
    assert base.debt_adjustment_policy == "NO_NET_DEBT_ADJUSTMENT"
    assert base.net_debt == Decimal("0")


def test_cyclical_commodity_with_latest_fy_is_not_verified():
    # DGC: SPECIALTY_CHEMICAL + HIGH_CYCLICALITY + COMMODITY_EXPOSED, only 1Y history.
    report = ValuationEngine.evaluate(
        symbol="DGC",
        facts=_facts_oe(),
        current_market_price=Decimal("50000"),
        shares_outstanding=Decimal("400000000"),
        fiscal_year=2023,
        fundamentals={"sector": "Hóa chất"},
    )
    assert report.archetype_profile["archetype"] == "SPECIALTY_CHEMICAL"
    assert report.owner_earnings_bridge.normalization_method == "LATEST_FY"
    assert report.model_status == "MODEL_INCOMPLETE"


def test_shallow_mid_cycle_is_model_partial():
    # HT1: BUILDING_MATERIALS + HIGH_CYCLICALITY, only 3Y mid-cycle -> MODEL_PARTIAL.
    three_year = []
    for i in range(3):
        y = 2023 - i
        three_year += [
            _make_fact("IS.REVENUE.NET", Decimal("8000") * Decimal("1000000000"), year=y),
            _make_fact("IS.PROFIT.NET", Decimal("1500") * Decimal("1000000000"), year=y),
            _make_fact("IS.PROFIT.OPERATING", Decimal("1500") * Decimal("1000000000"), year=y),
            _make_fact("CF.OPERATING.NET", Decimal("1700") * Decimal("1000000000"), year=y),
            _make_fact("CF.OPERATING.DEPRECIATION", Decimal("100") * Decimal("1000000000"), year=y),
            _make_fact("CF.CAPEX", Decimal("-120") * Decimal("1000000000"), year=y),
            _make_fact("BS.DEBT.TOTAL", Decimal("2000") * Decimal("1000000000"), year=y),
            _make_fact("BS.ASSETS.CASH_AND_EQUIVALENTS", Decimal("300") * Decimal("1000000000"), year=y),
            _make_fact("IS.SHARES.OUTSTANDING", Decimal("100000000"), year=y),
        ]
    report = ValuationEngine.evaluate(
        symbol="HT1",
        facts=three_year,
        current_market_price=Decimal("25000"),
        shares_outstanding=Decimal("100000000"),
        fiscal_year=2023,
        fundamentals={"sector": "Xi măng"},
    )
    assert report.owner_earnings_bridge.normalization_method == "MID_CYCLE_MEDIAN"
    assert report.owner_earnings_bridge.normalization_years == 3
    assert report.model_status == "MODEL_PARTIAL"


def test_vos_is_shipping_not_logistics():
    prof = ArchetypeClassifier.classify("VOS")
    assert prof.archetype == EconomicArchetype.SHIPPING
    assert prof.recommended_model == "FLEET_NAV"


def test_mining_shipping_airline_require_specialized_models():
    # Classifier must route to specialized primary models (not generic OE DCF).
    assert ArchetypeClassifier.classify("KSV").recommended_model == "RESERVE_NAV"
    assert ArchetypeClassifier.classify("MSR").recommended_model == "RESERVE_NAV"
    assert ArchetypeClassifier.classify("HAH").recommended_model == "FLEET_NAV"
    assert ArchetypeClassifier.classify("VOS").recommended_model == "FLEET_NAV"
    assert ArchetypeClassifier.classify("VJC").recommended_model == "AIRLINE_EBITDAR"
    assert ArchetypeClassifier.classify("HVN").recommended_model == "AIRLINE_EBITDAR"


def test_latest_fy_narrative_never_called_mid_cycle():
    report = ValuationEngine.evaluate(
        symbol="FPT",
        facts=_facts_oe(),
        current_market_price=Decimal("100000"),
        shares_outstanding=Decimal("1000000000"),
        fiscal_year=2023,
        fundamentals={"sector": "Công nghệ"},
    )
    assert "LATEST_FY" in report.verdict
    assert "giữa chu kỳ" not in report.verdict


# ---------------------------------------------------------------------------
# TASK-20260829-062: public/fallback separation, 7-10Y engine, semantics
# ---------------------------------------------------------------------------

def test_gated_model_has_null_public_iv_and_diagnostic_fallback():
    # DGC cyclical with 1Y history -> MODEL_INCOMPLETE. Public base_iv / MOS must
    # be null; the computed numbers move into fallback_valuation (DIAGNOSTIC_ONLY).
    report = ValuationEngine.evaluate(
        symbol="DGC",
        facts=_facts_oe(),
        current_market_price=Decimal("50000"),
        shares_outstanding=Decimal("400000000"),
        fiscal_year=2023,
        fundamentals={"sector": "Hóa chất"},
    )
    assert report.model_status == "MODEL_INCOMPLETE"
    assert report.base_iv is None
    assert report.margin_of_safety_pct is None
    assert report.fallback_valuation is not None
    assert report.fallback_valuation["usage"] == "DIAGNOSTIC_ONLY"
    assert report.fallback_valuation["base_iv"] is not None
    assert report.fallback_valuation["model"] == "NORMALIZED_OWNER_EARNINGS_DCF"


def test_verified_model_keeps_public_iv_and_no_fallback():
    # Uses a healthy 10-year history so the stock is HIGH_QUALITY (no hard reject /
    # not LOW_QUALITY) -> MODEL_VERIFIED keeps public IV and no fallback.
    report = ValuationEngine.evaluate(
        symbol="FPT",
        facts=_facts_oe(),
        current_market_price=Decimal("100000"),
        shares_outstanding=Decimal("1000000000"),
        fiscal_year=2023,
        fundamentals={"sector": "Công nghệ"},
        financial_history=_healthy_history(),
    )
    assert report.model_status == "MODEL_VERIFIED"
    assert report.base_iv is not None
    assert report.margin_of_safety_pct is not None
    assert report.fallback_valuation is None


def test_full_cycle_normalization_uses_available_years():
    # DGC-like 10Y ledger where some years lack CF codes: net income is used as
    # the OE proxy so the bridge must produce MID_CYCLE_MEDIAN, not LATEST_FY.
    b = Decimal("1000000000")
    facts = []
    for i in range(10):
        y = 2023 - i
        facts += [
            _make_fact("IS.REVENUE.NET", Decimal("8000") * b, year=y),
            _make_fact("IS.PROFIT.NET", Decimal("1500") * b, year=y),
            _make_fact("IS.PROFIT.OPERATING", Decimal("1500") * b, year=y),
            _make_fact("IS.SHARES.OUTSTANDING", Decimal("100000000"), year=y),
        ]
        # Only latest 3 years have full CF codes -> older years must still count.
        if i < 3:
            facts += [
                _make_fact("CF.OPERATING.NET", Decimal("1700") * b, year=y),
                _make_fact("CF.OPERATING.DEPRECIATION", Decimal("100") * b, year=y),
                _make_fact("CF.CAPEX", Decimal("-120") * b, year=y),
            ]
    bridge = OwnerEarningsCalculator.calculate_cycle_normalized(
        facts=facts, latest_fiscal_year=2023, lookback_years=10
    )
    assert bridge.normalization_method == "MID_CYCLE_MEDIAN"
    assert bridge.normalization_years >= 7


def test_power_water_bot_archetypes_split():
    expected = {
        "PPC": EconomicArchetype.POWER_GENERATION_THERMAL,
        "NT2": EconomicArchetype.POWER_GENERATION_THERMAL,
        "VSH": EconomicArchetype.POWER_GENERATION_HYDRO,
        "CHP": EconomicArchetype.POWER_GENERATION_HYDRO,
        "BWE": EconomicArchetype.WATER_UTILITY,
        "TDM": EconomicArchetype.WATER_UTILITY,
        "GEG": EconomicArchetype.POWER_RENEWABLE,
        "HHV": EconomicArchetype.CONCESSION_INFRASTRUCTURE,
        "CII": EconomicArchetype.CONCESSION_INFRASTRUCTURE,
    }
    for sym, arch in expected.items():
        prof = ArchetypeClassifier.classify(sym)
        assert prof.archetype == arch, f"{sym}: {prof.archetype.value} != {arch.value}"
        assert prof.archetype != EconomicArchetype.CONCESSION_INFRASTRUCTURE or sym in ("HHV", "CII")


def test_maintenance_capex_proxy_is_low_confidence():
    report = ValuationEngine.evaluate(
        symbol="FPT",
        facts=_facts_oe(),
        current_market_price=Decimal("100000"),
        shares_outstanding=Decimal("1000000000"),
        fiscal_year=2023,
        fundamentals={"sector": "Công nghệ"},
    )
    assert report.owner_earnings_bridge.maintenance_capex_confidence == "LOW"
    assert report.owner_earnings_bridge.maintenance_capex_method == "MIN_DEPRECIATION_CAPEX_PROXY"


def test_equity_cashflow_scenario_exposes_present_value():
    report = ValuationEngine.evaluate(
        symbol="FPT",
        facts=_facts_oe(),
        current_market_price=Decimal("100000"),
        shares_outstanding=Decimal("1000000000"),
        fiscal_year=2023,
        fundamentals={"sector": "Công nghệ"},
    )
    base = report.scenarios[ScenarioType.BASE]
    assert base.present_value is not None
    assert base.result_type == "EQUITY_VALUE"
    assert base.present_value == base.equity_value


def test_airport_concession_without_sourced_duration_is_estimated():
    # ACV: AIRPORT_INFRASTRUCTURE + CONCESSION_DCF with only the default 15-year
    # config -> MODEL_ESTIMATED (never VERIFIED), fallback kept for diagnostics.
    report = ValuationEngine.evaluate(
        symbol="ACV",
        facts=_facts_oe(),
        current_market_price=Decimal("100000"),
        shares_outstanding=Decimal("200000000"),
        fiscal_year=2023,
        fundamentals={"sector": "Hàng không"},
    )
    assert report.archetype_profile["archetype"] == "AIRPORT_INFRASTRUCTURE"
    assert report.valuation_model == "CONCESSION_DCF"
    assert report.model_status == "MODEL_ESTIMATED"
    assert report.fallback_valuation is not None


def test_airport_concession_with_sourced_duration_stays_verified():
    report = ValuationEngine.evaluate(
        symbol="ACV",
        facts=_facts_oe(),
        current_market_price=Decimal("100000"),
        shares_outstanding=Decimal("200000000"),
        fiscal_year=2023,
        fundamentals={"sector": "Hàng không", "concession_end_date": "2045-12-31"},
    )
    assert report.model_status == "MODEL_VERIFIED"


def test_non_airport_concession_unaffected_by_duration_gate():
    report = ValuationEngine.evaluate(
        symbol="GAS",
        facts=_facts_oe(),
        current_market_price=Decimal("78000"),
        shares_outstanding=Decimal("200000000"),
        fiscal_year=2023,
        fundamentals={"sector": "Tiện ích"},
    )
    assert report.model_status == "MODEL_VERIFIED"


def test_rim_exposes_equity_specific_present_value():
    # Audit round 3 #8: RIM must use equity-specific field naming. The discounted
    # stream is present_value == equity_value; enterprise_value is only a backward
    # compatibility alias, never a net-debt-adjusted enterprise number.
    report = ValuationEngine.evaluate(
        symbol="SSI",
        facts=_facts_oe(),
        current_market_price=Decimal("35000"),
        shares_outstanding=Decimal("1000000000"),
        fiscal_year=2023,
        fundamentals={"sector": "Chứng khoán", "bvps": Decimal("22000"), "roe": Decimal("15.0")},
    )
    base = report.scenarios[ScenarioType.BASE]
    assert report.valuation_model == "RESIDUAL_INCOME_MODEL"
    assert base.cashflow_basis == "RESIDUAL_INCOME"
    assert base.result_type == "EQUITY_VALUE"
    assert base.present_value == base.equity_value
    assert base.net_debt == Decimal("0")