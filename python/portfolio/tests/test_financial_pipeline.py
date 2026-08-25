from decimal import Decimal
import pytest

from portfolio.financial_data import (
    CafeFHtmlAdapter,
    CanonicalFact,
    ConsolidationScope,
    EntityType,
    FactIdentityKey,
    FinancialDataStore,
    PeriodType,
    ProviderFact,
    QualityStatus,
    StatementType,
    VnstockApiAdapter,
    compute_metrics,
)


def test_dual_ingestion_and_point_in_time_reconciliation():
    store = FinancialDataStore()
    api_adapter = VnstockApiAdapter()
    html_adapter = CafeFHtmlAdapter()

    # 1. Ingest via System A (Vnstock API)
    api_envelope = api_adapter.create_envelope(
        symbol="FPT",
        statement_type=StatementType.INCOME_STATEMENT,
        period_type=PeriodType.QUARTER,
        year=2026,
        quarter=1,
        raw_dict={
            "items": [
                {
                    "line_item_code": "IS.REVENUE.NET",
                    "value": "15758123",
                    "scale": "1000000",
                    "statement_type": "INCOME_STATEMENT",
                    "label": "Doanh thu thuần",
                },
                {
                    "line_item_code": "IS.PROFIT.NET",
                    "value": "2500000",
                    "scale": "1000000",
                    "statement_type": "INCOME_STATEMENT",
                    "label": "Lợi nhuận sau thuế",
                },
            ]
        },
    )
    store.save_envelope(api_envelope)
    facts_a = api_adapter.parse_envelope(api_envelope)
    store.save_provider_facts(facts_a)

    # 2. Ingest via System B (CafeF HTML)
    html_envelope = html_adapter.create_envelope(
        symbol="FPT",
        statement_type=StatementType.INCOME_STATEMENT,
        year=2026,
        quarter=1,
        html_content="<html><table><tr><td>Doanh thu thuần</td><td>15,758,123</td></tr></table></html>",
    )
    store.save_envelope(html_envelope)
    facts_b = html_adapter.parse_envelope(
        html_envelope,
        parsed_items=[
            {
                "line_item_code": "IS.REVENUE.NET",
                "value": "15758123",
                "scale": "1000000",
                "statement_type": "INCOME_STATEMENT",
                "label": "Doanh thu thuần",
            },
            {
                "line_item_code": "IS.PROFIT.NET",
                "value": "2500000",
                "scale": "1000000",
                "statement_type": "INCOME_STATEMENT",
                "label": "Lợi nhuận sau thuế",
            },
        ],
    )
    store.save_provider_facts(facts_b)

    # 3. Reconcile both items
    rev_id = FactIdentityKey(
        security_id="sec-fpt",
        statement_type=StatementType.INCOME_STATEMENT,
        period_end="2026-03-31",
        period_type=PeriodType.QUARTER,
        fiscal_year=2026,
        fiscal_quarter=1,
        consolidation_scope=ConsolidationScope.CONSOLIDATED,
        line_item_code="IS.REVENUE.NET",
    )
    np_id = FactIdentityKey(
        security_id="sec-fpt",
        statement_type=StatementType.INCOME_STATEMENT,
        period_end="2026-03-31",
        period_type=PeriodType.QUARTER,
        fiscal_year=2026,
        fiscal_quarter=1,
        consolidation_scope=ConsolidationScope.CONSOLIDATED,
        line_item_code="IS.PROFIT.NET",
    )

    can_rev = store.reconcile_and_store(rev_id)
    can_np = store.reconcile_and_store(np_id)

    assert can_rev.quality_status == QualityStatus.CROSS_SOURCE_VERIFIED
    assert can_rev.value == Decimal("15758123000000")
    assert can_np.quality_status == QualityStatus.CROSS_SOURCE_VERIFIED
    assert can_np.value == Decimal("2500000000000")

    # 4. Point-in-Time Query Check (Look-ahead bias test)
    # Query with past timestamp before observation -> should return empty
    past_as_of = "2026-01-01T00:00:00Z"
    past_facts = store.get_canonical_facts("sec-fpt", as_of=past_as_of)
    assert len(past_facts) == 0

    # Query with future timestamp -> should return verified facts
    future_as_of = "2026-12-31T23:59:59Z"
    future_facts = store.get_canonical_facts("sec-fpt", as_of=future_as_of)
    assert len(future_facts) == 2


def test_internal_metrics_calculation_for_enterprise_and_bank():
    # Setup canonical facts for FPT
    facts_fpt = [
        CanonicalFact(
            canonical_fact_id="cf-1",
            identity=FactIdentityKey(
                security_id="sec-fpt",
                statement_type=StatementType.INCOME_STATEMENT,
                period_end="2026-03-31",
                period_type=PeriodType.QUARTER,
                fiscal_year=2026,
                fiscal_quarter=1,
                consolidation_scope=ConsolidationScope.CONSOLIDATED,
                line_item_code="IS.REVENUE.NET",
            ),
            value=Decimal("10000000000000"),
            quality_status=QualityStatus.CROSS_SOURCE_VERIFIED,
            decision_id="dec-1",
            winning_candidate_id="doc-1",
            candidate_ids=["doc-1", "doc-2"],
            observed_at="2026-04-30T00:00:00Z",
        ),
        CanonicalFact(
            canonical_fact_id="cf-2",
            identity=FactIdentityKey(
                security_id="sec-fpt",
                statement_type=StatementType.INCOME_STATEMENT,
                period_end="2026-03-31",
                period_type=PeriodType.QUARTER,
                fiscal_year=2026,
                fiscal_quarter=1,
                consolidation_scope=ConsolidationScope.CONSOLIDATED,
                line_item_code="IS.PROFIT.NET",
            ),
            value=Decimal("2000000000000"),
            quality_status=QualityStatus.CROSS_SOURCE_VERIFIED,
            decision_id="dec-2",
            winning_candidate_id="doc-1",
            candidate_ids=["doc-1", "doc-2"],
            observed_at="2026-04-30T00:00:00Z",
        ),
        CanonicalFact(
            canonical_fact_id="cf-3",
            identity=FactIdentityKey(
                security_id="sec-fpt",
                statement_type=StatementType.BALANCE_SHEET,
                period_end="2026-03-31",
                period_type=PeriodType.QUARTER,
                fiscal_year=2026,
                fiscal_quarter=1,
                consolidation_scope=ConsolidationScope.CONSOLIDATED,
                line_item_code="BS.EQUITY.TOTAL",
            ),
            value=Decimal("20000000000000"),
            quality_status=QualityStatus.CROSS_SOURCE_VERIFIED,
            decision_id="dec-3",
            winning_candidate_id="doc-1",
            candidate_ids=["doc-1", "doc-2"],
            observed_at="2026-04-30T00:00:00Z",
        ),
    ]

    metrics_fpt = compute_metrics(facts_fpt, symbol="FPT", year=2026, quarter=1, entity_type=EntityType.NORMAL_ENTERPRISE)
    # Net Margin = 2,000 / 10,000 = 20%
    assert metrics_fpt["RATIO.MARGIN.NET"].value == Decimal("20.00")
    # ROE = 2,000 / 20,000 = 10%
    assert metrics_fpt["RATIO.ROE"].value == Decimal("10.00")
    assert metrics_fpt["RATIO.ROE"].input_fact_ids == ["cf-2", "cf-3"]

    # Bank Metrics (ACB)
    facts_bank = [
        CanonicalFact(
            canonical_fact_id="cf-b1",
            identity=FactIdentityKey(
                security_id="sec-acb",
                statement_type=StatementType.BALANCE_SHEET,
                period_end="2026-03-31",
                period_type=PeriodType.QUARTER,
                fiscal_year=2026,
                fiscal_quarter=1,
                consolidation_scope=ConsolidationScope.CONSOLIDATED,
                line_item_code="BS.BANK.LOANS_CUSTOMER",
            ),
            value=Decimal("500000000000000"),  # 500,000 B
            quality_status=QualityStatus.CROSS_SOURCE_VERIFIED,
            decision_id="dec-b1",
            winning_candidate_id="doc-b1",
            candidate_ids=["doc-b1"],
            observed_at="2026-04-30T00:00:00Z",
        ),
        CanonicalFact(
            canonical_fact_id="cf-b2",
            identity=FactIdentityKey(
                security_id="sec-acb",
                statement_type=StatementType.BALANCE_SHEET,
                period_end="2026-03-31",
                period_type=PeriodType.QUARTER,
                fiscal_year=2026,
                fiscal_quarter=1,
                consolidation_scope=ConsolidationScope.CONSOLIDATED,
                line_item_code="BS.BANK.NPL",
            ),
            value=Decimal("6000000000000"),  # 6,000 B
            quality_status=QualityStatus.CROSS_SOURCE_VERIFIED,
            decision_id="dec-b2",
            winning_candidate_id="doc-b1",
            candidate_ids=["doc-b1"],
            observed_at="2026-04-30T00:00:00Z",
        ),
    ]

    metrics_bank = compute_metrics(facts_bank, symbol="ACB", year=2026, quarter=1, entity_type=EntityType.BANK)
    # NPL Ratio = (6,000 / 500,000) * 100 = 1.2%
    assert metrics_bank["RATIO.BANK.NPL_RATIO"].value == Decimal("1.2")
