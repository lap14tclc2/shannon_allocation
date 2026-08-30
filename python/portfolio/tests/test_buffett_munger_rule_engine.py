import pytest
from portfolio.value_engine.archetypes import ArchetypeClassifier, EconomicArchetype
from portfolio.value_engine.quality_scorer import QualityScorer, QualityTier
from portfolio.value_engine.margin_of_safety import MarginOfSafetyEngine

def _fpt_history():
    # FPT-like: stable high-margin, high-ROE compounder across 10 years
    rows = []
    for i in range(10):
        yr = 2016 + i
        revenue = 15e12 + i * 2.0e12
        net_profit = 1.2e12 + i * 0.9e12
        equity = 8e12 + i * 1.5e12
        rows.append({
            "fiscal_year": yr,
            "revenue": revenue,
            "net_profit": net_profit,
            "equity": equity,
            "roe": round(net_profit / equity * 100, 1),
            "operating_cash_flow": net_profit * 1.05,
            "free_cash_flow": net_profit * 0.8,
            "cash_conversion_ratio": 105.0,
            "shares_outstanding": 3e9,
            "total_debt": 0,
            "cash_and_equivalents": 2e12,
        })
    return rows

def test_archetype_classification():
    # MBB -> COMMERCIAL_BANK
    mbb_prof = ArchetypeClassifier.classify("MBB")
    assert mbb_prof.archetype == EconomicArchetype.COMMERCIAL_BANK
    assert mbb_prof.recommended_model == "RESIDUAL_INCOME_MODEL"
    assert mbb_prof.base_required_mos == 0.25

    # FPT -> TECHNOLOGY_SERVICES
    fpt_prof = ArchetypeClassifier.classify("FPT")
    assert mbb_prof.archetype != fpt_prof.archetype
    assert fpt_prof.archetype == EconomicArchetype.TECHNOLOGY_SERVICES

    # HPG -> BASIC_MATERIALS_METALS
    hpg_prof = ArchetypeClassifier.classify("HPG")
    assert hpg_prof.archetype == EconomicArchetype.BASIC_MATERIALS_METALS
    assert hpg_prof.base_required_mos >= 0.40

def test_quality_scorer_and_dynamic_mos():
    fpt_prof = ArchetypeClassifier.classify("FPT")
    scorecard = QualityScorer.evaluate(
        archetype_prof=fpt_prof,
        financial_history_10y=_fpt_history(),
        five_year_avg_roe=24.0,
        five_year_avg_cash_conversion=105.0,
        net_debt_vnd=0.0,
        latest_cfo=10e12,
        true_dilution_5y_pct=0.0,
    )

    assert scorecard.total_score >= 80
    assert scorecard.tier in (QualityTier.EXCEPTIONAL, QualityTier.HIGH_QUALITY)
    # Moat must be evidence-based, not ROE-only (audit P1-5)
    assert scorecard.moat_score >= 12
    assert scorecard.moat_evidence.get("total") == scorecard.moat_score

    # HIGH confidence is required for HIGH_CONVICTION (audit P0-1)
    mos_high = MarginOfSafetyEngine.calculate(
        archetype_prof=fpt_prof,
        quality_tier=scorecard.tier,
        actual_base_mos=30.0,
        confidence_level="HIGH",
    )
    assert mos_high.required_mos_pct <= 25.0
    assert mos_high.mos_satisfied is True
    assert mos_high.verdict_status == "HIGH_CONVICTION_VALUE"

    # MEDIUM confidence must NOT produce HIGH_CONVICTION (audit P0-1)
    mos_med = MarginOfSafetyEngine.calculate(
        archetype_prof=fpt_prof,
        quality_tier=scorecard.tier,
        actual_base_mos=30.0,
        confidence_level="MEDIUM",
    )
    assert mos_med.verdict_status == "ATTRACTIVE"
    assert mos_med.confidence_penalty_pct >= 5.0

    # LOW confidence adds >= 10% MOS (audit P0-1)
    mos_low = MarginOfSafetyEngine.calculate(
        archetype_prof=fpt_prof,
        quality_tier=scorecard.tier,
        actual_base_mos=30.0,
        confidence_level="LOW",
    )
    assert mos_low.confidence_penalty_pct >= 10.0
    assert mos_low.required_mos_pct >= mos_high.required_mos_pct + 5.0


def test_industrial_real_estate_and_conflict_gate():
    # IDC, BCM, SZC, NTC, SIP -> INDUSTRIAL_REAL_ESTATE with LEASE_CASHFLOW_DCF
    idc_prof = ArchetypeClassifier.classify("IDC")
    assert idc_prof.archetype == EconomicArchetype.INDUSTRIAL_REAL_ESTATE
    assert idc_prof.recommended_model == "LEASE_CASHFLOW_DCF"

    bcm_prof = ArchetypeClassifier.classify("BCM")
    assert bcm_prof.archetype == EconomicArchetype.INDUSTRIAL_REAL_ESTATE

    ntc_prof = ArchetypeClassifier.classify("NTC")
    assert ntc_prof.archetype == EconomicArchetype.INDUSTRIAL_REAL_ESTATE

    # GVR -> RUBBER_PLANTATION with rubber & industrial park land conversion
    gvr_prof = ArchetypeClassifier.classify("GVR")
    assert gvr_prof.archetype in (EconomicArchetype.RUBBER_PLANTATION, EconomicArchetype.CONGLOMERATE)

    # Sector conflict resolution test
    generic_kcn = ArchetypeClassifier.classify("TEST_TICKER", sector_text="Bất động sản Khu công nghiệp")
    assert generic_kcn.archetype == EconomicArchetype.INDUSTRIAL_REAL_ESTATE

    generic_re = ArchetypeClassifier.classify("TEST_TICKER2", sector_text="Bất động sản Dân dụng")
    assert generic_re.archetype == EconomicArchetype.REAL_ESTATE_DEVELOPER


def test_moat_evidence_and_iroic_integrity():
    fpt_prof = ArchetypeClassifier.classify("FPT")
    scorecard = QualityScorer.evaluate(
        archetype_prof=fpt_prof,
        financial_history_10y=_fpt_history(),
        five_year_avg_roe=24.0,
        five_year_avg_cash_conversion=105.0,
        net_debt_vnd=0.0,
        latest_cfo=10e12,
        true_dilution_5y_pct=0.0,
    )
    # Check iROIC evidence structure
    cap_ev = scorecard.capital_allocation_evidence
    assert "incremental_return_median" in cap_ev
    assert "cumulative_3y_iroic_pct" in cap_ev
    assert scorecard.moat_evidence["moat_tier"] in ("WIDE", "NARROW", "NONE")


def test_registry_integrity_and_all_archetypes():
    from portfolio.value_engine.archetypes import ARCHETYPE_REGISTRY, EconomicArchetype
    assert len(ARCHETYPE_REGISTRY) >= 40
    for arch in EconomicArchetype:
        entry = ARCHETYPE_REGISTRY.get(arch)
        assert entry is not None, f"Missing registry entry for {arch}"
        assert entry.primary_model != ""
        assert entry.base_mos > 0


def test_idc_lease_cashflow_dcf_and_gas_concession_routing():
    from decimal import Decimal
    from portfolio.value_engine import ValuationEngine
    from portfolio.financial_data.models import (
        CanonicalFact,
        ConsolidationScope,
        EntityType,
        FactIdentityKey,
        PeriodType,
        QualityStatus,
        StatementType,
    )
    from portfolio.value_engine.models import ScenarioType

    def _f(code, val):
        return CanonicalFact(
            canonical_fact_id=f"{code}-2023",
            identity=FactIdentityKey(
                security_id="s1",
                statement_type=StatementType.INCOME_STATEMENT if code.startswith("IS.") else (
                    StatementType.CASH_FLOW if code.startswith("CF.") else StatementType.BALANCE_SHEET
                ),
                period_end="2023-12-31",
                period_type=PeriodType.FY,
                fiscal_year=2023,
                fiscal_quarter=None,
                consolidation_scope=ConsolidationScope.CONSOLIDATED,
                line_item_code=code,
                currency="VND",
            ),
            value=val,
            quality_status=QualityStatus.CROSS_SOURCE_VERIFIED,
            decision_id="d1",
            winning_candidate_id=None,
            candidate_ids=[],
            observed_at="2026-01-01T00:00:00Z",
        )

    facts = [
        _f("IS.REVENUE.NET", Decimal("7000000000000")),
        _f("IS.PROFIT.NET", Decimal("1500000000000")),
        _f("IS.PROFIT.OPERATING", Decimal("2000000000000")),
        _f("CF.OPERATING.NET", Decimal("2200000000000")),
        _f("CF.OPERATING.DEPRECIATION", Decimal("400000000000")),
        _f("CF.CAPEX", Decimal("-600000000000")),
        _f("BS.DEBT.TOTAL", Decimal("3000000000000")),
        _f("BS.ASSETS.CASH_AND_EQUIVALENTS", Decimal("4000000000000")),
        _f("IS.SHARES.OUTSTANDING", Decimal("330000000")),
    ]

    # IDC evaluation -> LEASE_CASHFLOW_DCF
    idc_report = ValuationEngine.evaluate(
        symbol="IDC",
        facts=facts,
        current_market_price=Decimal("55000"),
        shares_outstanding=Decimal("330000000"),
        fiscal_year=2023,
        fundamentals={"sector": "Bất động sản Khu công nghiệp"},
    )
    assert idc_report.archetype_profile["recommended_model"] == "LEASE_CASHFLOW_DCF"
    assert idc_report.scenarios[ScenarioType.BASE].intrinsic_value_per_share > Decimal("0")

    # GAS evaluation -> CONCESSION_DCF (Terminal Growth = 0)
    gas_report = ValuationEngine.evaluate(
        symbol="GAS",
        facts=facts,
        current_market_price=Decimal("78000"),
        shares_outstanding=Decimal("2000000000"),
        fiscal_year=2023,
        fundamentals={"sector": "Tiện ích"},
    )
    assert gas_report.archetype_profile["recommended_model"] == "CONCESSION_DCF"
    assert gas_report.scenarios[ScenarioType.BASE].terminal_growth_rate == Decimal("0")
    assert len(gas_report.scenarios[ScenarioType.BASE].scenario_warnings) > 0

    # GVR evaluation -> SOTP
    gvr_report = ValuationEngine.evaluate(
        symbol="GVR",
        facts=facts,
        current_market_price=Decimal("32000"),
        shares_outstanding=Decimal("4000000000"),
        fiscal_year=2023,
        fundamentals={"sector": "Tập đoàn Cao su"},
    )
    assert gvr_report.valuation_model == "SOTP"
    assert gvr_report.archetype_profile["recommended_model"] == "SOTP"
    assert gvr_report.sotp_breakdown is not None
    assert len(gvr_report.sotp_breakdown["components"]) >= 3
    assert gvr_report.sotp_breakdown["gross_asset_value"] > 0
    assert gvr_report.model_status == "MODEL_VERIFIED"

    # DGC overlay check
    from portfolio.value_engine.archetypes import ArchetypeOverlay
    dgc_prof = ArchetypeClassifier.classify("DGC")
    assert ArchetypeOverlay.COMMODITY_EXPOSED in dgc_prof.overlays

    # Owner Earnings current vs normalized separation check
    assert gvr_report.owner_earnings_bridge is not None
    assert gvr_report.owner_earnings_bridge.current_owner_earnings is not None
    assert gvr_report.owner_earnings_bridge.normalized_owner_earnings is not None


def test_model_validation_gate_rejection():
    from decimal import Decimal
    from portfolio.value_engine.archetypes import ArchetypeProfile, EconomicArchetype, ArchetypeOverlay, ARCHETYPE_REGISTRY
    entry = ARCHETYPE_REGISTRY.get(EconomicArchetype.COMMERCIAL_BANK)
    assert "NORMALIZED_OWNER_EARNINGS_DCF" in entry.forbidden_models
    assert "RESIDUAL_INCOME_MODEL" == entry.primary_model


def test_vea_holding_company_sotp_valuation():
    from decimal import Decimal
    from portfolio.value_engine import ValuationEngine
    from portfolio.financial_data.models import (
        CanonicalFact,
        ConsolidationScope,
        EntityType,
        FactIdentityKey,
        PeriodType,
        QualityStatus,
        StatementType,
    )
    from portfolio.value_engine.models import ScenarioType

    def _f(code, val):
        return CanonicalFact(
            canonical_fact_id=f"{code}-2023",
            identity=FactIdentityKey(
                security_id="s1",
                statement_type=StatementType.INCOME_STATEMENT if code.startswith("IS.") else (
                    StatementType.CASH_FLOW if code.startswith("CF.") else StatementType.BALANCE_SHEET
                ),
                period_end="2023-12-31",
                period_type=PeriodType.FY,
                fiscal_year=2023,
                fiscal_quarter=None,
                consolidation_scope=ConsolidationScope.CONSOLIDATED,
                line_item_code=code,
                currency="VND",
            ),
            value=val,
            quality_status=QualityStatus.CROSS_SOURCE_VERIFIED,
            decision_id="d1",
            winning_candidate_id=None,
            candidate_ids=[],
            observed_at="2026-01-01T00:00:00Z",
        )

    facts = [
        _f("IS.REVENUE.NET", Decimal("500000000000")),
        _f("IS.PROFIT.NET", Decimal("7200000000000")),
        _f("IS.PROFIT.OPERATING", Decimal("-100000000000")),
        _f("CF.OPERATING.NET", Decimal("-80000000000")),
        _f("CF.OPERATING.DEPRECIATION", Decimal("250000000000")),
        _f("CF.CAPEX", Decimal("-100000000000")),
        _f("BS.DEBT.TOTAL", Decimal("100000000000")),
        _f("BS.ASSETS.CASH_AND_EQUIVALENTS", Decimal("13000000000000")),
        _f("IS.SHARES.OUTSTANDING", Decimal("1328800000")),
    ]

    vea_report = ValuationEngine.evaluate(
        symbol="VEA",
        facts=facts,
        current_market_price=Decimal("42000"),
        shares_outstanding=Decimal("1328800000"),
        fiscal_year=2023,
        fundamentals={"sector": "Doanh nghiệp niêm yết"},
    )
    assert vea_report.valuation_model == "SOTP"
    assert vea_report.archetype_profile["archetype"] == "HOLDING_COMPANY"
    assert vea_report.sotp_breakdown is not None
    assert len(vea_report.sotp_breakdown["components"]) == 4
    assert any("Honda" in c["component_name"] for c in vea_report.sotp_breakdown["components"])
    assert any("Toyota" in c["component_name"] for c in vea_report.sotp_breakdown["components"])
    assert any("Ford" in c["component_name"] for c in vea_report.sotp_breakdown["components"])
    assert vea_report.base_iv > Decimal("0")
    # P1 Holding specifics: generic EPV and Reverse DCF suppressed
    assert vea_report.epv_result is None
    assert vea_report.reverse_dcf_result is None
    assert vea_report.sotp_sensitivity_matrix is not None
    assert vea_report.holding_cash_quality is not None
    assert vea_report.holding_cash_quality["cash_conversion_rate_pct"] == 97.2
    # P0 Traceability: source facts and formula trace on all components
    for comp in vea_report.sotp_breakdown["components"]:
        assert comp["source_fact_ids"] is not None and len(comp["source_fact_ids"]) > 0
        assert comp["formula_trace"] is not None and len(comp["formula_trace"]) > 0
        assert comp["ownership_pct"] is not None


def test_dividend_quconciliation_quarantine_above_200_pct():
    from portfolio.dividend_reconciliation import normalize_observation

    # Normal 15% stock dividend
    n1 = normalize_observation({
        "symbol": "MBB",
        "dividend_type": "STOCK_DIVIDEND",
        "stock_ratio": 15.0,
        "ex_date": "2023-05-01",
    }, provider="tcbs")
    assert n1["stock_ratio"] == 0.15
    assert n1["status"] == "NORMALIZED"

    # Extreme stock dividend > 200% (e.g. 9237% parser artifact from raw shares)
    n2 = normalize_observation({
        "symbol": "MBB",
        "dividend_type": "STOCK_DIVIDEND",
        "stock_ratio": 9237.0,
        "ex_date": "2021-01-06",
    }, provider="tcbs")
    assert n2["status"] == "REJECTED"
    assert n2["stock_ratio"] is None