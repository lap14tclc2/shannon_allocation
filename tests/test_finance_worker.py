from __future__ import annotations

import inspect
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "python"))

from portfolio import finance_catalog  # noqa: E402


def test_worker_queue_claim_and_finish_api_exists():
    assert callable(finance_catalog.claim_next_crawl_job)
    assert callable(finance_catalog.finish_crawl_job)
    assert "RUNNING" in inspect.getsource(finance_catalog.claim_next_crawl_job)
    assert "SECURITY_NOT_CRAWLABLE" in inspect.getsource(
        finance_catalog.claim_next_crawl_job
    )


def test_worker_script_is_local_and_processes_claimed_jobs():
    script = (ROOT / "scripts" / "finance_worker.py").read_text(encoding="utf-8")
    assert "claim_next_crawl_job" in script
    assert "crawl_symbol" in script
    assert "finish_crawl_job" in script
    assert "Vercel runtime is database-read-only" in script
    assert "providers=cafef" not in script
    assert "providers=tcbs" in script


def test_worker_reports_symbol_outcomes_and_final_summary():
    script = (ROOT / "scripts" / "finance_worker.py").read_text(encoding="utf-8")
    assert "SUCCESS symbol=" in script
    assert "FAILED symbol=" in script
    assert "success_symbols=" in script
    assert "failed_symbols=" in script
    assert "summary processed=" in script


def test_tcbs_document_headers_require_token_without_logging_it(monkeypatch):
    monkeypatch.delenv("TCBS_BEARER_TOKEN", raising=False)
    try:
        finance_catalog._tcbs_document_headers(require_token=True)
    except RuntimeError as exc:
        assert "TCBS_BEARER_TOKEN" in str(exc)
    else:
        raise AssertionError("worker must require an authenticated TCBS token")


def test_tcbs_document_headers_normalize_bearer_prefix(monkeypatch):
    monkeypatch.setenv("TCBS_BEARER_TOKEN", "eyJ-test")
    assert finance_catalog._tcbs_document_headers()["Authorization"] == "Bearer eyJ-test"
    monkeypatch.setenv("TCBS_BEARER_TOKEN", "Bearer eyJ-test")
    assert finance_catalog._tcbs_document_headers()["Authorization"] == "Bearer eyJ-test"


def test_worker_scope_is_tcbs_statements_only():
    assert finance_catalog.WORKER_PROVIDERS == ("tcbs",)
    assert finance_catalog.WORKER_DOCUMENT_TYPES == (
        "FINANCIAL_STATEMENTS",
        "CASH_FLOW",
        "INCOME_STATEMENT",
    )


def test_tcbs_history_parser_selects_exact_periods_from_fixture():
    fixture = json.loads(
        (ROOT / "docs" / "crawled" / "tcbs_FPT_financial_data.json").read_text(
            encoding="utf-8"
        )
    )
    income_year = json.dumps(
        {"data": fixture["data"]["incomestatement_year"]}
    )
    income_quarter = json.dumps(
        {"data": fixture["data"]["incomestatement_quarter"]}
    )
    balance_year = json.dumps(
        {"data": fixture["data"]["balancesheet_year"]}
    )
    cashflow_year = json.dumps(
        {"data": fixture["data"]["cashflow_year"]}
    )
    combined = json.dumps(fixture)

    assert finance_catalog._tcbs_select_record(
        combined,
        symbol="FPT",
        document_type="INCOME_STATEMENT",
        period_type="FY",
        year=2025,
        quarter=None,
    )["postTaxProfit"] == 11232
    assert finance_catalog._tcbs_select_record(
        combined,
        symbol="FPT",
        document_type="FINANCIAL_STATEMENTS",
        period_type="FY",
        year=2025,
        quarter=None,
    )["cash"] == 10522
    assert finance_catalog._tcbs_select_record(
        combined,
        symbol="FPT",
        document_type="CASH_FLOW",
        period_type="FY",
        year=2025,
        quarter=None,
    )["investCost"] == -5098

    assert finance_catalog._tcbs_select_record(
        income_year, symbol="FPT", period_type="FY", year=2025, quarter=None
    )["postTaxProfit"] == 11232
    assert finance_catalog._tcbs_select_record(
        income_quarter, symbol="FPT", period_type="QUARTER",
        year=2026, quarter=2
    )["operationProfit"] == 1848
    assert finance_catalog._tcbs_select_record(
        balance_year, symbol="FPT", period_type="FY", year=2025, quarter=None
    )["cash"] == 10522
    assert finance_catalog._tcbs_select_record(
        cashflow_year, symbol="FPT", period_type="FY", year=2025, quarter=None
    )["investCost"] == -5098


def test_tcbs_value_engine_aliases_match_fixture_fields():
    row = {
        "postTaxProfit": 11232,
        "operationProfit": 10989,
        "debt": 44394,
        "cash": 10522,
        "investCost": -5098,
    }
    assert finance_catalog._value(row, "postTaxProfit") == 11232
    assert finance_catalog._value(row, "operationProfit") == 10989
    assert finance_catalog._value(row, "debt") == 44394
    assert finance_catalog._value(row, "cash") == 10522
    assert finance_catalog._value(row, "investCost") == -5098
    assert finance_catalog._value(row, "operating_cash_flow") is None


def test_tcbs_parser_keeps_missing_value_engine_facts_missing():
    source = inspect.getsource(finance_catalog._canonicalize_document)
    assert "capital or shareHolderIncome" in source
    assert "CF.OPERATING.NET" in source
    assert "IS.SHARES.OUTSTANDING" in source


def test_tcbs_urls_use_history_endpoint_once_per_statement_type():
    source = inspect.getsource(finance_catalog.crawl_symbol)
    assert "_fetch_tcbs_history" in source
    assert "endpoint_requests=" in source
    assert "cafef" not in source.lower()


def test_finance_db_exposes_cafef_cleanup_without_touching_worker_scope():
    script = (ROOT / "scripts" / "finance_db.py").read_text(encoding="utf-8")
    assert '"clear-cafef"' in script
    assert "clear_provider_finance_data" in script


def test_prepared_tcbs_directory_loader_is_incremental_and_file_only():
    source = inspect.getsource(finance_catalog.import_tcbs_crawled_directory)
    assert 'directory: str = "docs/crawled"' in source
    assert "_tcbs_select_record" in source
    assert "_save_document" in source
    assert "retry_failed_only" in source
    assert "_fetch_tcbs_history" not in source


def test_prepared_tcbs_import_script_uses_docs_crawled():
    script = (ROOT / "scripts" / "finance_import.py").read_text(encoding="utf-8")
    assert 'default="docs/crawled"' in script
    assert "import_tcbs_crawled_directory" in script
    assert "TCBS_BEARER_TOKEN" not in script
