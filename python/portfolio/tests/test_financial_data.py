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
    get_required_period_type,
    get_taxonomy_for_entity,
    reconcile_facts,
)


def _sample_identity(statement_type=StatementType.INCOME_STATEMENT, line_item="IS.REVENUE.NET"):
    p_type = get_required_period_type(statement_type, PeriodType.QUARTER)
    return FactIdentityKey(
        security_id="sec-fpt-001",
        statement_type=statement_type,
        period_end="2026-03-31",
        period_type=p_type,
        fiscal_year=2026,
        fiscal_quarter=1,
        consolidation_scope=ConsolidationScope.CONSOLIDATED,
        line_item_code=line_item,
        currency="VND",
    )


def test_fact_identity_key_and_balance_sheet_period_invariants():
    # 1. Income statement can be QUARTER
    id_is = _sample_identity(StatementType.INCOME_STATEMENT)
    assert id_is.period_type == PeriodType.QUARTER

    # 2. Balance Sheet MUST strictly be INSTANT (QFD-240)
    id_bs = _sample_identity(StatementType.BALANCE_SHEET, "BS.ASSETS.TOTAL")
    assert id_bs.period_type == PeriodType.INSTANT


def test_taxonomy_includes_insurance_and_all_entities():
    normal = get_taxonomy_for_entity(EntityType.NORMAL_ENTERPRISE)
    assert "IS.REVENUE.NET" in normal
    assert "IS.BANK.NII" not in normal

    bank = get_taxonomy_for_entity(EntityType.BANK)
    assert "IS.BANK.NII" in bank
    assert "BS.BANK.LOANS_CUSTOMER" in bank

    sec = get_taxonomy_for_entity(EntityType.SECURITIES)
    assert "IS.SEC.BROKERAGE_REV" in sec

    ins = get_taxonomy_for_entity(EntityType.INSURANCE)
    assert "IS.INS.PREMIUM_NET" in ins
    assert "BS.INS.TECHNICAL_RESERVES" in ins


def test_reconciliation_is_strictly_deterministic():
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
    # Run twice
    res1, dec1 = reconcile_facts(identity, [f1])
    res2, dec2 = reconcile_facts(identity, [f1])

    # Deterministic ID matching (No uuid4 randomness)
    assert res1.canonical_fact_id == res2.canonical_fact_id
    assert dec1.decision_id == dec2.decision_id
    assert res1.quality_status == QualityStatus.SINGLE_SOURCE
    assert res1.value == Decimal("15758123000000")


def test_missing_fact_has_none_value_not_zero():
    identity = _sample_identity()
    # No candidates provided
    canonical, decision = reconcile_facts(identity, [])
    assert canonical.quality_status == QualityStatus.MISSING
    assert canonical.value is None  # Strict null != 0 (QFD-250)
    assert decision.chosen_value is None


def test_same_provider_duplicates_do_not_get_cross_source_verified():
    identity = _sample_identity()
    # Two facts from SAME provider (vnstock_api)
    f1 = ProviderFact(
        security_id="sec-fpt-001",
        symbol_observed="FPT",
        statement_type=StatementType.INCOME_STATEMENT,
        line_item_code="IS.REVENUE.NET",
        label_observed="Doanh thu thuần 1",
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
        provider_id="vnstock_api",
        source_document_id="doc-vnstock-1",
        observed_at="2026-04-30T03:00:00Z",
        parser_version="vnstock@1.0.0",
        revision_no=0,
    )
    f2 = ProviderFact(
        security_id="sec-fpt-001",
        symbol_observed="FPT",
        statement_type=StatementType.INCOME_STATEMENT,
        line_item_code="IS.REVENUE.NET",
        label_observed="Doanh thu thuần 2",
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
        provider_id="vnstock_api",
        source_document_id="doc-vnstock-2",
        observed_at="2026-04-30T03:05:00Z",
        parser_version="vnstock@1.0.0",
        revision_no=1,
    )
    canonical, decision = reconcile_facts(identity, [f1, f2])
    # Must remain SINGLE_SOURCE because both originate from vnstock_api
    assert canonical.quality_status == QualityStatus.SINGLE_SOURCE
    assert canonical.value == Decimal("15758123000000")


def test_evidence_tiering_structured_api_beats_html():
    identity = _sample_identity()
    # Official beats API, API beats HTML
    f_cafef = ProviderFact(
        security_id="sec-fpt-001",
        symbol_observed="FPT",
        statement_type=StatementType.INCOME_STATEMENT,
        line_item_code="IS.REVENUE.NET",
        label_observed="Doanh thu CafeF",
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
        source_document_id="doc-cafef",
        observed_at="2026-04-30T03:00:00Z",
        parser_version="cafef@1.0.0",
    )
    f_vnstock = ProviderFact(
        security_id="sec-fpt-001",
        symbol_observed="FPT",
        statement_type=StatementType.INCOME_STATEMENT,
        line_item_code="IS.REVENUE.NET",
        label_observed="Doanh thu Vnstock",
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
        provider_id="vnstock_api",
        source_document_id="doc-vnstock",
        observed_at="2026-04-30T03:00:00Z",
        parser_version="vnstock@1.0.0",
    )
    canonical, decision = reconcile_facts(identity, [f_cafef, f_vnstock])
    assert canonical.quality_status == QualityStatus.CROSS_SOURCE_VERIFIED
    # Winner must be vnstock (tier 70 > tier 50)
    assert canonical.winning_candidate_id == f_vnstock.provider_fact_id
