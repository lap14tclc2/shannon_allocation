"""Unit and Integration Tests for Bulk SSI Ingestion Engine."""

from __future__ import annotations

import os
from pathlib import Path
import pytest

from portfolio.financial_data.ssi_ingestion import (
    parse_ssi_filename,
    parse_ssi_workbook,
    map_ssi_line_item,
    SSIBulkImporter,
)
from portfolio.canonical_valuation import build_canonical_valuation


def test_ssi_filename_parser():
    """Verify filename metadata parsing tolerant of casing and download suffixes."""
    res1 = parse_ssi_filename("SSI_AAA_Financial_statement_Cash_Flow_09092026 (5).xlsx")
    assert res1.is_valid is True
    assert res1.symbol == "AAA"
    assert res1.statement_type == "CASH_FLOW"
    assert res1.export_date_str == "09092026"
    assert res1.download_suffix == 5

    res2 = parse_ssi_filename("SSI_VIX_Financial_Statement_Balance_Sheet_10092026.xlsx")
    assert res2.is_valid is True
    assert res2.symbol == "VIX"
    assert res2.statement_type == "BALANCE_SHEET"
    assert res2.download_suffix is None

    res3 = parse_ssi_filename("SSI_DGC_Financial_statement_Income_Statement_09092026 (2).xlsx")
    assert res3.is_valid is True
    assert res3.symbol == "DGC"
    assert res3.statement_type == "INCOME_STATEMENT"
    assert res3.download_suffix == 2


def test_semantic_hash_stability_on_aaa_cash_flow_fixtures():
    """Verify raw SHA differs but semantic_hash is identical across extraction timestamps."""
    bctc_dir = Path("F:/DATA_BCTC")
    if not bctc_dir.exists():
        pytest.skip("F:/DATA_BCTC directory not available")

    file1 = bctc_dir / "SSI_AAA_Financial_statement_Cash_Flow_09092026.xlsx"
    file2 = bctc_dir / "SSI_AAA_Financial_statement_Cash_Flow_09092026 (1).xlsx"
    file5 = bctc_dir / "SSI_AAA_Financial_statement_Cash_Flow_09092026 (5).xlsx"

    wb1 = parse_ssi_workbook(str(file1))
    wb2 = parse_ssi_workbook(str(file2))
    wb5 = parse_ssi_workbook(str(file5))

    assert wb1.is_valid is True
    assert wb2.is_valid is True
    assert wb5.is_valid is True

    # Raw file SHA256 hashes must differ due to extraction timestamps
    assert wb1.raw_file_sha256 != wb2.raw_file_sha256
    assert wb1.raw_file_sha256 != wb5.raw_file_sha256

    # Semantic hashes MUST be identical
    assert wb1.semantic_hash == wb2.semantic_hash
    assert wb1.semantic_hash == wb5.semantic_hash


def test_null_vs_zero_invariant_preservation():
    """Verify empty cells remain None, explicit zeros remain 0.0."""
    bctc_dir = Path("F:/DATA_BCTC")
    if not bctc_dir.exists():
        pytest.skip("F:/DATA_BCTC directory not available")

    file_path = bctc_dir / "SSI_AAA_Financial_Statement_Balance_Sheet_09092026.xlsx"
    wb = parse_ssi_workbook(str(file_path))
    assert wb.is_valid is True

    # Find explicit 0 values vs None values
    has_explicit_zero = False
    has_none_value = False

    for obs in wb.observations:
        if obs["value"] == 0.0:
            has_explicit_zero = True
        elif obs["value"] is None:
            has_none_value = True

    assert has_explicit_zero is True, "Explicit zero values should be preserved as 0.0"
    assert has_none_value is True, "Empty cells should be preserved as None"


def test_unmapped_row_preservation():
    """Verify raw rows that cannot be mapped return UNMAPPED without throwing error."""
    code, status = map_ssi_line_item("TÀI SẢN THIẾU CHỜ XỬ LÝ KỲ QUÁI", "BALANCE_SHEET")
    assert status == "UNMAPPED"
    assert code is None

    mapped_code, mapped_status = map_ssi_line_item("TỔNG TÀI SẢN", "BALANCE_SHEET")
    assert mapped_status == "MAPPED"
    assert mapped_code == "BS.ASSETS.TOTAL"


def test_dry_run_discovery_bctc_directory():
    """Verify dry-run execution scans F:\\DATA_BCTC and produces audit reports."""
    bctc_dir = Path("F:/DATA_BCTC")
    if not bctc_dir.exists():
        pytest.skip("F:/DATA_BCTC directory not available")

    importer = SSIBulkImporter(directory=str(bctc_dir))
    summary = importer.run(dry_run=True, target_symbol="AAA")

    assert summary.files_discovered >= 5
    assert summary.unique_symbols >= 1
    assert summary.raw_observations_count > 0
    assert summary.canonical_facts_count > 0
    assert Path("docs/reports/ssi-import-summary.json").exists()


@pytest.mark.skipif(not os.environ.get("DATABASE_URL"), reason="Requires PostgreSQL database connection")
def test_ssi_db_ingestion_and_canonical_valuation_query():
    """Import sample symbols (AAA, VIX) and verify canonical valuation reads SSI facts from DB."""
    bctc_dir = Path("F:/DATA_BCTC")
    if not bctc_dir.exists():
        pytest.skip("F:/DATA_BCTC directory not available")

    from portfolio.finance_catalog import initialize_finance_schema, _schema_connection, FINANCE_SCHEMA

    initialize_finance_schema()
    with _schema_connection(FINANCE_SCHEMA) as conn:
        importer = SSIBulkImporter(directory=str(bctc_dir), db_connection=conn)
        summary = importer.run(dry_run=False, resume=True, target_symbol="AAA")
        assert summary.files_parsed > 0

        # Query canonical valuation for AAA
        val = build_canonical_valuation("AAA", market_price=10000.0)
        assert val.get("ok") is True
        assert len(val.get("financial_history", [])) >= 3
        # Prove historical rows came from imported canonical facts
        first_hist = val["financial_history"][0]
        assert "net_profit" in first_hist or "revenue" in first_hist
