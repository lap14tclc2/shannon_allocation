import json
from decimal import Decimal
from pathlib import Path
import pytest

from portfolio.financial_data import (
    CanonicalFact,
    ConsolidationScope,
    FactIdentityKey,
    FinancialDataStore,
    PeriodType,
    ProviderFact,
    QualityStatus,
    StatementType,
)
from portfolio.value_engine import (
    ConfidenceLevel,
    DCFValuationModel,
    EPVValuationModel,
    OwnerEarningsCalculator,
    ReverseDCFModel,
    ScenarioType,
    SensitivityAnalyzer,
    ValuationEngine,
)

FIXTURES_DIR = Path(__file__).resolve().parents[3] / "docs" / "tasks" / "qport-financial-data" / "references" / "fixtures"


def test_owner_earnings_calculator_bridge():
    facts = [
        CanonicalFact(
            canonical_fact_id="cf-1",
            identity=FactIdentityKey(
                security_id="sec-fpt",
                statement_type=StatementType.INCOME_STATEMENT,
                period_end="2026-06-30",
                period_type=PeriodType.QUARTER,
                fiscal_year=2026,
                fiscal_quarter=2,
                consolidation_scope=ConsolidationScope.CONSOLIDATED,
                line_item_code="IS.PROFIT.NET",
            ),
            value=Decimal("2200000000000"),  # 2,200 tỷ VND
            quality_status=QualityStatus.CROSS_SOURCE_VERIFIED,
            decision_id="dec-1",
            winning_candidate_id="vnstock-1",
            candidate_ids=["vnstock-1", "cafef-1"],
            observed_at="2026-08-25T00:00:00Z",
        ),
        CanonicalFact(
            canonical_fact_id="cf-2",
            identity=FactIdentityKey(
                security_id="sec-fpt",
                statement_type=StatementType.CASH_FLOW,
                period_end="2026-06-30",
                period_type=PeriodType.QUARTER,
                fiscal_year=2026,
                fiscal_quarter=2,
                consolidation_scope=ConsolidationScope.CONSOLIDATED,
                line_item_code="CF.CAPEX",
            ),
            value=Decimal("800000000000"),  # 800 tỷ VND
            quality_status=QualityStatus.CROSS_SOURCE_VERIFIED,
            decision_id="dec-2",
            winning_candidate_id="vnstock-2",
            candidate_ids=["vnstock-2"],
            observed_at="2026-08-25T00:00:00Z",
        ),
        CanonicalFact(
            canonical_fact_id="cf-da",
            identity=FactIdentityKey(
                security_id="sec-fpt",
                statement_type=StatementType.CASH_FLOW,
                period_end="2026-06-30",
                period_type=PeriodType.QUARTER,
                fiscal_year=2026,
                fiscal_quarter=2,
                consolidation_scope=ConsolidationScope.CONSOLIDATED,
                line_item_code="CF.OPERATING.DEPRECIATION",
            ),
            value=Decimal("600000000000"),
            quality_status=QualityStatus.CROSS_SOURCE_VERIFIED,
            decision_id="dec-da",
            winning_candidate_id="vnstock-da",
            candidate_ids=["vnstock-da"],
            observed_at="2026-08-25T00:00:00Z",
        ),
        CanonicalFact(
            canonical_fact_id="cf-3",
            identity=FactIdentityKey(
                security_id="sec-fpt",
                statement_type=StatementType.CASH_FLOW,
                period_end="2026-06-30",
                period_type=PeriodType.QUARTER,
                fiscal_year=2026,
                fiscal_quarter=2,
                consolidation_scope=ConsolidationScope.CONSOLIDATED,
                line_item_code="CF.OPERATING.NET",
            ),
            value=Decimal("2500000000000"),  # 2,500 tỷ VND
            quality_status=QualityStatus.CROSS_SOURCE_VERIFIED,
            decision_id="dec-3",
            winning_candidate_id="vnstock-3",
            candidate_ids=["vnstock-3"],
            observed_at="2026-08-25T00:00:00Z",
        ),
    ]

    bridge = OwnerEarningsCalculator.calculate(facts, fiscal_year=2026, fiscal_quarter=2)
    assert bridge.net_income == Decimal("2200000000000")
    assert bridge.owner_earnings > Decimal("0")
    assert len(bridge.source_fact_ids) == 4


def test_dcf_valuation_scenarios_and_margin_of_safety():
    # REVIEW(P0): this test only asserts that the result is positive; it does not catch
    # debt double-counting. Add an invariant test where NI-based Owner Earnings produces
    # the same equity value regardless of a net_debt argument (or remove net_debt from the
    # equity-basis API), plus a separate FCFF test that explicitly subtracts net debt once.
    base_oe = Decimal("8000000000000")  # 8,000 tỷ VND annual
    shares = Decimal("1460000000")  # 1.46 tỷ cổ phiếu
    net_debt = Decimal("5000000000000")  # 5,000 tỷ VND
    market_price = Decimal("125000")  # 125,000 VND / cp

    # Base scenario: 11% hurdle, 14% growth, 3.5% terminal
    scen = DCFValuationModel.calculate_scenario(
        base_owner_earnings=base_oe,
        shares_outstanding=shares,
        net_debt=net_debt,
        scenario_type=ScenarioType.BASE,
        discount_rate=Decimal("0.11"),
        growth_rate=Decimal("0.14"),
        growth_years=5,
        terminal_growth=Decimal("0.035"),
        current_market_price=market_price,
    )

    assert scen.intrinsic_value_per_share > Decimal("0")
    assert scen.margin_of_safety_pct is not None
    assert len(scen.projected_cash_flows) == 5


def test_epv_model_zero_growth():
    ebit = Decimal("10000000000000")  # 10,000 tỷ
    tax_rate = Decimal("0.20")
    wacc = Decimal("0.11")
    net_debt = Decimal("2000000000000")
    shares = Decimal("1460000000")

    epv = EPVValuationModel.calculate(
        normalized_operating_earnings=ebit,
        tax_rate=tax_rate,
        cost_of_capital=wacc,
        net_debt=net_debt,
        shares_outstanding=shares,
        current_market_price=Decimal("50000"),
    )

    # NOPAT = 8,000 tỷ. EPV EV = 8000 / 0.11 = 72,727 tỷ. Equity = 70,727 tỷ.
    # Per share = ~48,443 VND
    assert epv.nopat == Decimal("8000000000000")
    assert round(epv.epv_per_share, 0) == Decimal("48443")


def test_reverse_dcf_solves_implied_growth():
    base_oe = Decimal("8000000000000")
    shares = Decimal("1460000000")
    net_debt = Decimal("5000000000000")
    market_price = Decimal("130000")

    rev = ReverseDCFModel.solve_implied_growth(
        base_owner_earnings=base_oe,
        shares_outstanding=shares,
        net_debt=net_debt,
        current_market_price=market_price,
        discount_rate=Decimal("0.11"),
        terminal_growth=Decimal("0.035"),
    )

    assert rev.implied_stage1_growth_rate > Decimal("-0.50")
    assert "Thị trường" in rev.verdict


def test_sensitivity_matrix_dimensions():
    base_oe = Decimal("8000000000000")
    shares = Decimal("1460000000")
    net_debt = Decimal("5000000000000")

    discount_rates = [Decimal("0.10"), Decimal("0.11"), Decimal("0.12")]
    terminal_rates = [Decimal("0.03"), Decimal("0.035")]

    matrix = SensitivityAnalyzer.build_matrix(
        base_owner_earnings=base_oe,
        shares_outstanding=shares,
        net_debt=net_debt,
        base_growth_rate=Decimal("0.14"),
        discount_rates=discount_rates,
        terminal_growth_rates=terminal_rates,
    )

    assert len(matrix.grid_values_per_share) == 2  # 2 rows
    assert len(matrix.grid_values_per_share[0]) == 3  # 3 cols


def test_valuation_engine_end_to_end_report_with_real_fixture():
    # Load actual real fixture facts or use self-contained fallbacks
    cafef_fixture = FIXTURES_DIR / "standardized_cafef_FPT_facts.json"
    vnstock_fixture = FIXTURES_DIR / "standardized_vnstock_FPT_facts.json"

    if cafef_fixture.exists() and vnstock_fixture.exists():
        with open(cafef_fixture, "r", encoding="utf-8") as f:
            c_facts = json.load(f)["facts"]
        with open(vnstock_fixture, "r", encoding="utf-8") as f:
            v_facts = json.load(f)["facts"]
        raw_items = c_facts + v_facts
    else:
        raw_items = [
            {
                "security_id": "sec-fpt", "symbol_observed": "FPT", "statement_type": "INCOME_STATEMENT",
                "line_item_code": "IS.PROFIT.NET", "label_observed": "LNST", "value_raw": "2500",
                "value_normalized": "2500000000000", "currency": "VND", "scale_observed": "1000000000",
                "period_start": "2026-04-01", "period_end": "2026-06-30", "period_type": "QUARTER",
                "fiscal_year": 2026, "fiscal_quarter": 2, "consolidation_scope": "CONSOLIDATED",
                "provider_id": "vnstock_api", "source_document_id": "doc-v1", "observed_at": "2026-08-25T00:00:00Z",
                "parser_version": "1.0",
            },
            {
                "security_id": "sec-fpt", "symbol_observed": "FPT", "statement_type": "CASH_FLOW",
                "line_item_code": "CF.CAPEX", "label_observed": "CapEx", "value_raw": "-500",
                "value_normalized": "-500000000000", "currency": "VND", "scale_observed": "1000000000",
                "period_start": "2026-04-01", "period_end": "2026-06-30", "period_type": "QUARTER",
                "fiscal_year": 2026, "fiscal_quarter": 2, "consolidation_scope": "CONSOLIDATED",
                "provider_id": "vnstock_api", "source_document_id": "doc-v1", "observed_at": "2026-08-25T00:00:00Z",
                "parser_version": "1.0",
            }
        ]

    store = FinancialDataStore()
    
    # Store all facts
    store.save_provider_facts([
        ProviderFact(
            security_id=item["security_id"],
            symbol_observed=item["symbol_observed"],
            statement_type=StatementType(item["statement_type"]),
            line_item_code=item["line_item_code"],
            label_observed=item["label_observed"],
            value_raw=item["value_raw"],
            value_normalized=Decimal(str(item["value_normalized"])),
            currency=item["currency"],
            scale_observed=Decimal(str(item["scale_observed"])),
            period_start=item["period_start"],
            period_end=item["period_end"],
            period_type=PeriodType(item["period_type"]),
            fiscal_year=item["fiscal_year"],
            fiscal_quarter=item["fiscal_quarter"],
            consolidation_scope=ConsolidationScope(item["consolidation_scope"]),
            provider_id=item["provider_id"],
            source_document_id=item["source_document_id"],
            observed_at=item["observed_at"],
            parser_version=item["parser_version"],
        )
        for item in raw_items
    ])

    # Reconcile key facts for 2026 Q2
    for code in ["IS.REVENUE.GROSS", "IS.PROFIT.NET", "IS.PROFIT.OPERATING", "BS.DEBT.TOTAL", "CF.CAPEX", "CF.OPERATING.NET"]:
        key = FactIdentityKey(
            security_id="sec-fpt",
            statement_type=StatementType.INCOME_STATEMENT if code.startswith("IS.") else (StatementType.BALANCE_SHEET if code.startswith("BS.") else StatementType.CASH_FLOW),
            period_end="2026-06-30",
            period_type=PeriodType.INSTANT if code.startswith("BS.") else PeriodType.QUARTER,
            fiscal_year=2026,
            fiscal_quarter=2,
            consolidation_scope=ConsolidationScope.CONSOLIDATED,
            line_item_code=code,
        )
        store.reconcile_and_store(key)

    facts = store.get_canonical_facts("sec-fpt")
    
    # The engine refuses a quarterly period unless a deliberate audited TTM
    # bridge has been provided; it must not annualise by multiplying by four.
    with pytest.raises(ValueError, match="TTM_REQUIRED"):
        ValuationEngine.evaluate(
        symbol="FPT",
        facts=facts,
        current_market_price=Decimal("132000"),
        shares_outstanding=Decimal("1460485900"),
        diluted_shares_estimate=Decimal("1480000000"),
        fiscal_year=2026,
        fiscal_quarter=2,
    )

