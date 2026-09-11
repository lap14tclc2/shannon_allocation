"""Comprehensive Unit and Integration Tests for Task 132C: SSI Canonical Semantics Repair."""

import os
import pytest
from portfolio.financial_data.ssi_ingestion import (
    map_ssi_line_item,
    normalize_string,
    parse_ssi_filename,
    classify_payload_relationship,
    derive_total_debt_facts,
    SSIBulkImporter,
)
from portfolio.financial_data.reconciler import reconcile_symbol_accounting
from portfolio.finance_catalog import valuation_readiness_audit


def test_exact_alias_matching_no_unsafe_fuzzy_substrings():
    """Verify exact line item matching prevents false-positive fuzzy mapping."""
    # Must NOT map child brokerage revenue to total revenue
    code, status = map_ssi_line_item("Doanh thu hoạt động môi giới chứng khoán", "INCOME_STATEMENT")
    assert status == "UNMAPPED"
    assert code != "IS.REVENUE.TOTAL"

    # Must NOT map specific customer receivable to total receivables
    code, status = map_ssi_line_item("Phải thu khách hàng", "BALANCE_SHEET")
    assert status == "UNMAPPED"
    assert code != "BS.ASSETS.RECEIVABLES"

    # Must NOT map specific bank borrowing to short term borrowings
    code, status = map_ssi_line_item("Vay ngắn hạn ngân hàng ABC", "BALANCE_SHEET")
    assert status == "UNMAPPED"
    assert code != "BS.LIABILITIES.SHORT_TERM_BORROWINGS"

    # Must NOT map current tax expense to net income
    code, status = map_ssi_line_item("Chi phí thuế TNDN hiện hành", "INCOME_STATEMENT")
    assert status == "UNMAPPED"
    assert code != "IS.PROFIT.NET"


def test_canonical_exact_aliases_mapped_correctly():
    """Verify genuine canonical line item names map correctly with exact matching."""
    # Income statement
    code, status = map_ssi_line_item("Doanh thu thuần về bán hàng và cung cấp dịch vụ", "INCOME_STATEMENT")
    assert status == "MAPPED"
    assert code == "IS.REVENUE.TOTAL"

    code, status = map_ssi_line_item("Lợi nhuận sau thuế TNDN", "INCOME_STATEMENT")
    assert status == "MAPPED"
    assert code == "IS.PROFIT.NET"

    # Balance sheet
    code, status = map_ssi_line_item("Tổng cộng tài sản", "BALANCE_SHEET")
    assert status == "MAPPED"
    assert code == "BS.ASSETS.TOTAL"

    code, status = map_ssi_line_item("Vốn chủ sở hữu", "BALANCE_SHEET")
    assert status == "MAPPED"
    assert code == "BS.EQUITY.TOTAL"

    # Cash flow
    code, status = map_ssi_line_item("Lưu chuyển tiền thuần từ hoạt động kinh doanh", "CASH_FLOW")
    assert status == "MAPPED"
    assert code == "CF.OPERATING.NET"


def test_derived_total_debt_archetype_boundaries():
    """Verify derived BS.DEBT.TOTAL is computed for normal enterprise and omitted for Bank/Securities."""
    batch_fpt = [
        ("FPT", "BALANCE_SHEET", "BS.LIABILITIES.SHORT_TERM_BORROWINGS", 1000.0, 2025, "2025-12-31", "2026-09-11"),
        ("FPT", "BALANCE_SHEET", "BS.LIABILITIES.LONG_TERM_BORROWINGS", 500.0, 2025, "2025-12-31", "2026-09-11"),
    ]
    derived_fpt = derive_total_debt_facts(batch_fpt, "FPT")
    assert len(derived_fpt) == 1
    assert derived_fpt[0][2] == "BS.DEBT.TOTAL"
    assert derived_fpt[0][3] == 1500.0

    # Bank (ACB) - Total debt derivation must be omitted
    batch_acb = [
        ("ACB", "BALANCE_SHEET", "BS.LIABILITIES.SHORT_TERM_BORROWINGS", 1000.0, 2025, "2025-12-31", "2026-09-11"),
        ("ACB", "BALANCE_SHEET", "BS.LIABILITIES.LONG_TERM_BORROWINGS", 500.0, 2025, "2025-12-31", "2026-09-11"),
    ]
    derived_acb = derive_total_debt_facts(batch_acb, "ACB")
    assert len(derived_acb) == 0

    # Securities (VIX) - Total debt derivation must be omitted
    batch_vix = [
        ("VIX", "BALANCE_SHEET", "BS.LIABILITIES.SHORT_TERM_BORROWINGS", 1000.0, 2025, "2025-12-31", "2026-09-11"),
        ("VIX", "BALANCE_SHEET", "BS.LIABILITIES.LONG_TERM_BORROWINGS", 500.0, 2025, "2025-12-31", "2026-09-11"),
    ]
    derived_vix = derive_total_debt_facts(batch_vix, "VIX")
    assert len(derived_vix) == 0


def test_derived_total_debt_requires_both_short_and_long_term():
    """Verify total debt derivation requires both inputs and does not convert missing to zero."""
    batch_missing_long = [
        ("DGC", "BALANCE_SHEET", "BS.LIABILITIES.SHORT_TERM_BORROWINGS", 1000.0, 2025, "2025-12-31", "2026-09-11"),
    ]
    derived = derive_total_debt_facts(batch_missing_long, "DGC")
    assert len(derived) == 0


@pytest.mark.skipif(not os.environ.get("DATABASE_URL"), reason="Requires PostgreSQL database connection")
def test_real_db_golden_symbols_canonical_semantics():
    """Verify real PostgreSQL facts for golden symbols (ACB, DGC, FPT, VIX)."""
    for sym in ["ACB", "DGC", "FPT", "VIX"]:
        audit = valuation_readiness_audit(sym, market_price=50000.0)
        assert audit["status"] == "READY", f"Valuation readiness failed for {sym}"
        assert audit["selected_facts"]["IS.PROFIT.NET"]["provider"] == "ssi", f"Primary SSI provider not selected for {sym}"
        assert audit["selected_facts"]["BS.EQUITY.TOTAL"]["provider"] == "ssi", f"Primary SSI provider not selected for {sym}"
        assert len(audit.get("conflicts", [])) == 0




@pytest.mark.skipif(not os.environ.get("DATABASE_URL"), reason="Requires PostgreSQL database connection")
def test_real_db_accounting_reconciliation_sample_symbols():
    """Verify accounting reconciliation results on real PostgreSQL database."""
    from portfolio.finance_catalog import _schema_connection, FINANCE_SCHEMA
    with _schema_connection(FINANCE_SCHEMA) as conn:
        res_aaa = reconcile_symbol_accounting("AAA", conn)
        assert res_aaa["bs_balance_pass"] is True
        assert res_aaa["cf_cash_pass"] is True

        res_aah = reconcile_symbol_accounting("AAH", conn)
        assert res_aah["history_years"] >= 1

        res_vix = reconcile_symbol_accounting("VIX", conn)
        assert "CASH_CONTINUITY_VARIANCE" in res_vix["anomalies"]
        assert "AGGREGATE_COMPONENT_INCONSISTENCY" in res_vix["anomalies"]
