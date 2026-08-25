from decimal import Decimal
import pytest

from portfolio.financial_data import (
    CanonicalFact,
    ConsolidationScope,
    EntityType,
    FactIdentityKey,
    PeriodType,
    ProviderFact,
    QualityStatus,
    StatementType,
    get_taxonomy_for_entity,
    reconcile_facts,
)


def _sample_identity():
    return FactIdentityKey(
        security_id="sec-fpt-001",
        statement_type=StatementType.INCOME_STATEMENT,
        period_end="2026-03-31",
        period_type=PeriodType.QUARTER,
        fiscal_year=2026,
        fiscal_quarter=1,
        consolidation_scope=ConsolidationScope.CONSOLIDATED,
        line_item_code="IS.REVENUE.NET",
        currency="VND",
    )


def test_fact_identity_key_equality():
    id1 = _sample_identity()
    id2 = _sample_identity()
    assert id1 == id2
    assert hash(id1) == hash(id2)


def test_taxonomy_for_entities():
    normal = get_taxonomy_for_entity(EntityType.NORMAL_ENTERPRISE)
    assert "IS.REVENUE.NET" in normal
    assert "IS.BANK.NII" not in normal

    bank = get_taxonomy_for_entity(EntityType.BANK)
    assert "IS.BANK.NII" in bank
    assert "BS.BANK.LOANS_CUSTOMER" in bank

    sec = get_taxonomy_for_entity(EntityType.SECURITIES)
    assert "IS.SEC.BROKERAGE_REV" in sec


def test_reconciliation_single_source():
    identity = _sample_identity()
    f1 = ProviderFact(
        security_id="sec-fpt-001",
        symbol_observed="FPT",
        statement_type=StatementType.INCOME_STATEMENT,
        line_item_code="IS.REVENUE.NET",
        label_observed="Doanh thu thuần",
        value_raw="15,758,123",
        value_normalized=Decimal("15758123000000"),
        currency="VND",
        scale_observed=Decimal("1000000"),
        period_start="2026-01-01",
        period_end="2026-03-31",
        period_type=PeriodType.QUARTER,
        fiscal_year=2026,
        fiscal_quarter=1,
        consolidation_scope=ConsolidationScope.CONSOLIDATED,
        provider_id="vnstock_api",
        source_document_id="doc-vnstock-1",
        observed_at="2026-04-30T03:00:00Z",
        parser_version="vnstock@1.0.0",
    )
    result = reconcile_facts(identity, [f1])
    assert result.quality_status == QualityStatus.SINGLE_SOURCE
    assert result.value == Decimal("15758123000000")
    assert result.winning_candidate_id == "doc-vnstock-1"


def test_reconciliation_cross_source_verified():
    identity = _sample_identity()
    f1 = ProviderFact(
        security_id="sec-fpt-001",
        symbol_observed="FPT",
        statement_type=StatementType.INCOME_STATEMENT,
        line_item_code="IS.REVENUE.NET",
        label_observed="Doanh thu thuần",
        value_raw="15,758,123",
        value_normalized=Decimal("15758123000000"),
        currency="VND",
        scale_observed=Decimal("1000000"),
        period_start="2026-01-01",
        period_end="2026-03-31",
        period_type=PeriodType.QUARTER,
        fiscal_year=2026,
        fiscal_quarter=1,
        consolidation_scope=ConsolidationScope.CONSOLIDATED,
        provider_id="vnstock_api",
        source_document_id="doc-vnstock-1",
        observed_at="2026-04-30T03:00:00Z",
        parser_version="vnstock@1.0.0",
    )
    f2 = ProviderFact(
        security_id="sec-fpt-001",
        symbol_observed="FPT",
        statement_type=StatementType.INCOME_STATEMENT,
        line_item_code="IS.REVENUE.NET",
        label_observed="Doanh thu thuần",
        value_raw="15758123",
        value_normalized=Decimal("15758123000000"),
        currency="VND",
        scale_observed=Decimal("1000000"),
        period_start="2026-01-01",
        period_end="2026-03-31",
        period_type=PeriodType.QUARTER,
        fiscal_year=2026,
        fiscal_quarter=1,
        consolidation_scope=ConsolidationScope.CONSOLIDATED,
        provider_id="cafef_html",
        source_document_id="doc-cafef-1",
        observed_at="2026-04-30T03:10:00Z",
        parser_version="cafef@1.0.0",
    )
    result = reconcile_facts(identity, [f1, f2])
    assert result.quality_status == QualityStatus.CROSS_SOURCE_VERIFIED
    assert result.value == Decimal("15758123000000")


def test_reconciliation_conflict_on_material_discrepancy():
    identity = _sample_identity()
    f1 = ProviderFact(
        security_id="sec-fpt-001",
        symbol_observed="FPT",
        statement_type=StatementType.INCOME_STATEMENT,
        line_item_code="IS.REVENUE.NET",
        label_observed="Doanh thu thuần",
        value_raw="15,758,123",
        value_normalized=Decimal("15758123000000"),
        currency="VND",
        scale_observed=Decimal("1000000"),
        period_start="2026-01-01",
        period_end="2026-03-31",
        period_type=PeriodType.QUARTER,
        fiscal_year=2026,
        fiscal_quarter=1,
        consolidation_scope=ConsolidationScope.CONSOLIDATED,
        provider_id="vnstock_api",
        source_document_id="doc-vnstock-1",
        observed_at="2026-04-30T03:00:00Z",
        parser_version="vnstock@1.0.0",
    )
    f2 = ProviderFact(
        security_id="sec-fpt-001",
        symbol_observed="FPT",
        statement_type=StatementType.INCOME_STATEMENT,
        line_item_code="IS.REVENUE.NET",
        label_observed="Doanh thu thuần",
        value_raw="16,000,000",
        value_normalized=Decimal("16000000000000"),
        currency="VND",
        scale_observed=Decimal("1000000"),
        period_start="2026-01-01",
        period_end="2026-03-31",
        period_type=PeriodType.QUARTER,
        fiscal_year=2026,
        fiscal_quarter=1,
        consolidation_scope=ConsolidationScope.CONSOLIDATED,
        provider_id="cafef_html",
        source_document_id="doc-cafef-1",
        observed_at="2026-04-30T03:10:00Z",
        parser_version="cafef@1.0.0",
    )
    result = reconcile_facts(identity, [f1, f2])
    assert result.quality_status == QualityStatus.CONFLICT
    assert result.winning_candidate_id is None
