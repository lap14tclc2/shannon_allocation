import json
from decimal import Decimal
from pathlib import Path
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

FIXTURES_DIR = Path(__file__).resolve().parents[3] / "docs" / "tasks" / "qport-financial-data" / "references" / "fixtures"


def test_real_crawled_fixtures_dual_ingestion_and_reconciliation():
    # Load actual standardized fixture files
    cafef_fixture = FIXTURES_DIR / "standardized_cafef_FPT_facts.json"
    vnstock_fixture = FIXTURES_DIR / "standardized_vnstock_FPT_facts.json"

    assert cafef_fixture.exists(), "CafeF fixture must exist"
    assert vnstock_fixture.exists(), "Vnstock fixture must exist"

    with open(cafef_fixture, "r", encoding="utf-8") as f:
        cafef_json = json.load(f)
    with open(vnstock_fixture, "r", encoding="utf-8") as f:
        vnstock_json = json.load(f)

    store = FinancialDataStore()
    
    # Ingest CafeF provider facts
    facts_cafef = [
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
        for item in cafef_json["facts"]
    ]
    store.save_provider_facts(facts_cafef)

    # Ingest Vnstock provider facts
    facts_vnstock = [
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
        for item in vnstock_json["facts"]
    ]
    store.save_provider_facts(facts_vnstock)

    # Reconcile Revenue Gross for 2026 Q2 (overlapping period between Vnstock & CafeF)
    key_2026_q2 = FactIdentityKey(
        security_id="sec-fpt",
        statement_type=StatementType.INCOME_STATEMENT,
        period_end="2026-06-30",
        period_type=PeriodType.QUARTER,
        fiscal_year=2026,
        fiscal_quarter=2,
        consolidation_scope=ConsolidationScope.CONSOLIDATED,
        line_item_code="IS.REVENUE.GROSS",
    )

    canonical = store.reconcile_and_store(key_2026_q2)
    assert canonical.quality_status == QualityStatus.CROSS_SOURCE_VERIFIED
    assert canonical.value == Decimal("13810340987151")

    # Verify decision audit trail
    decision = store.get_decision(canonical.decision_id)
    assert decision is not None
    assert decision.chosen_status == QualityStatus.CROSS_SOURCE_VERIFIED
    assert len(decision.candidate_fact_ids) == 2


def test_bitemporal_point_in_time_query_and_restatements():
    store = FinancialDataStore()
    
    key = FactIdentityKey(
        security_id="sec-fpt",
        statement_type=StatementType.INCOME_STATEMENT,
        period_end="2026-03-31",
        period_type=PeriodType.QUARTER,
        fiscal_year=2026,
        fiscal_quarter=1,
        consolidation_scope=ConsolidationScope.CONSOLIDATED,
        line_item_code="IS.REVENUE.NET",
    )

    # Version 1 observed at T1
    f_v1 = ProviderFact(
        security_id="sec-fpt",
        symbol_observed="FPT",
        statement_type=StatementType.INCOME_STATEMENT,
        line_item_code="IS.REVENUE.NET",
        label_observed="Doanh thu thuần V1",
        value_raw="15000000",
        value_normalized=Decimal("15000000000000"),
        currency="VND",
        scale_observed=Decimal("1000000"),
        period_start="2026-01-01",
        period_end="2026-03-31",
        period_type=PeriodType.QUARTER,
        fiscal_year=2026,
        fiscal_quarter=1,
        consolidation_scope=ConsolidationScope.CONSOLIDATED,
        provider_id="vnstock_api",
        source_document_id="doc-1",
        observed_at="2026-04-30T00:00:00Z",
        parser_version="1.0.0",
        revision_no=0,
    )
    store.save_provider_facts([f_v1])
    can_v1 = store.reconcile_and_store(key)

    # Query before T1 -> empty
    res_before = store.get_canonical_facts("sec-fpt", as_of="2026-04-01T00:00:00Z")
    assert len(res_before) == 0

    # Query at T1 -> returns V1
    res_at_t1 = store.get_canonical_facts("sec-fpt", as_of="2026-05-01T00:00:00Z")
    assert len(res_at_t1) == 1
    assert res_at_t1[0].value == Decimal("15000000000000")


def test_metrics_skips_conflicted_and_quarantined_facts():
    facts = [
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
            quality_status=QualityStatus.CONFLICT,  # CONFLICT
            decision_id="dec-1",
            winning_candidate_id=None,
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
    ]

    # Metrics calculator must NOT compute Net Margin using conflicted revenue
    metrics = compute_metrics(facts, symbol="FPT", year=2026, quarter=1, entity_type=EntityType.NORMAL_ENTERPRISE)
    assert "RATIO.MARGIN.NET" not in metrics
