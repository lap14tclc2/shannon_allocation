from __future__ import annotations

import inspect
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "python"))

from portfolio import finance_catalog  # noqa: E402


def test_worker_queue_claim_and_finish_api_exists():
    assert callable(finance_catalog.claim_next_crawl_job)
    assert callable(finance_catalog.finish_crawl_job)
    assert "RUNNING" in inspect.getsource(finance_catalog.claim_next_crawl_job)
    assert "SECURITY_NOT_CRAWLABLE" in inspect.getsource(finance_catalog.claim_next_crawl_job)


def test_worker_script_is_local_and_processes_claimed_jobs():
    script = (ROOT / "scripts" / "finance_worker.py").read_text(encoding="utf-8")
    assert "claim_next_crawl_job" in script
    assert "crawl_symbol" in script
    assert "finish_crawl_job" in script
    assert "Vercel runtime is database-read-only" in script


def test_tcbs_document_headers_use_optional_local_bearer_token(monkeypatch):
    monkeypatch.setenv("TCBS_BEARER_TOKEN", "eyJ-test")
    headers = finance_catalog._tcbs_document_headers()
    assert headers["Authorization"] == "Bearer eyJ-test"


def test_tcbs_document_headers_do_not_duplicate_bearer_prefix(monkeypatch):
    monkeypatch.setenv("TCBS_BEARER_TOKEN", "Bearer eyJ-test")
    headers = finance_catalog._tcbs_document_headers()
    assert headers["Authorization"] == "Bearer eyJ-test"


def test_cafef_html_rows_extract_latest_numeric_period():
    html = """
    <table><tr><th>Mã</th><th>Quý 1</th><th>Quý 2</th></tr>
    <tr><td>1. Doanh thu bán hàng</td><td>1,234</td><td>2,345</td></tr></table>
    """
    rows = finance_catalog._payload_rows(html)
    assert rows == [{
        "label": "1. Doanh thu bán hàng",
        "value": "2,345",
        "period_values": ["1,234", "2,345"],
    }]


def test_cafef_financial_urls_use_current_data_route():
    source = inspect.getsource(finance_catalog._fetch_provider)
    assert "cafef.vn/du-lieu/bao-cao-tai-chinh" in source
    assert "s.cafef.vn/bao-cao-tai-chinh" not in source


def test_cafef_placeholder_urls_use_current_data_route():
    source = inspect.getsource(finance_catalog.ensure_required_documents)
    assert "cafef.vn/du-lieu/bao-cao-tai-chinh" in source
    assert "s.cafef.vn/bao-cao-tai-chinh" not in source
