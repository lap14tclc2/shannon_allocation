from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_finance_catalog_search_is_parameterized_and_composes_with_filters():
    source = (ROOT / "python" / "portfolio" / "finance_catalog.py").read_text(encoding="utf-8")
    api = (ROOT / "frontend" / "src" / "lib" / "api.js").read_text(encoding="utf-8")
    ui = (ROOT / "frontend" / "src" / "pages" / "FinanceDataPage.jsx").read_text(encoding="utf-8")

    assert "q: str | None = None" in source
    assert "UPPER(s.symbol) LIKE ? OR UPPER(COALESCE(s.company_name, '')) LIKE ?" in source
    assert 'needle = f"%{search_value.upper()}%"' in source
    assert "if (params.q) query.set('q', String(params.q));" in api
    assert "Tìm mã / tên công ty" in ui


def test_worker_only_claims_hose_then_hnx_without_touching_upcom():
    source = (ROOT / "python" / "portfolio" / "finance_catalog.py").read_text(encoding="utf-8")
    claim = source[source.index("def claim_next_crawl_job"):source.index("def finish_crawl_job")]
    enqueue = source[source.index("def enqueue_crawl_all"):source.index("def _validate_crawl_runtime")]

    assert 'WORKER_CRAWL_EXCHANGES = ("HOSE", "HNX")' in source
    assert "JOIN securities AS s ON s.symbol=q.symbol" in claim
    assert "s.exchange IN ('HOSE','HNX')" in claim
    assert "CASE s.exchange WHEN 'HOSE' THEN 0 WHEN 'HNX' THEN 1" in claim
    assert "CRAWL_EXCHANGE_UNSUPPORTED" in enqueue
    assert "exchange IN ('HOSE','HNX')" in enqueue


def test_worker_uses_cafef_only_and_preserves_tcbs_support_for_later_reenable():
    source = (ROOT / "python" / "portfolio" / "finance_catalog.py").read_text(encoding="utf-8")
    worker = (ROOT / "scripts" / "finance_worker.py").read_text(encoding="utf-8")

    assert 'PROVIDERS = ("tcbs", "cafef")' in source
    assert 'WORKER_PROVIDERS = ("cafef",)' in source
    assert "for provider in WORKER_PROVIDERS" in source
    assert "providers=cafef" in worker
    assert "TCBS_BEARER_TOKEN" not in worker


def test_active_catalog_ignores_legacy_tcbs_rows():
    source = (ROOT / "python" / "portfolio" / "finance_catalog.py").read_text(encoding="utf-8")

    assert "worker_provider_sql" in source
    assert "WHERE provider IN ({worker_provider_sql})" in source
    assert "FROM documents WHERE provider IN ({worker_provider_sql})" in source


def test_cafef_dividend_uses_one_current_history_document_and_hides_legacy_years():
    source = (ROOT / "python" / "portfolio" / "finance_catalog.py").read_text(encoding="utf-8")

    assert "latest_fy = max((item[1] for item in periods if item[0] == 'FY')" in source
    assert "document_type == " + '"DIVIDEND" and (period_type != "FY" or year != latest_fy)' in source
    assert "document_type <> 'DIVIDEND'" in source
    assert "provider IN ({worker_provider_sql})" in source


def test_retry_targets_one_document_and_returns_updated_row():
    source = (ROOT / "python" / "portfolio" / "finance_catalog.py").read_text(encoding="utf-8")
    api = (ROOT / "app" / "main.py").read_text(encoding="utf-8")
    ui = (ROOT / "frontend" / "src" / "pages" / "FinanceDataPage.jsx").read_text(encoding="utf-8")

    assert "document_filter: dict[str, Any] | None = None" in source
    assert "current_key != target" in source
    assert '"item": updated_item' in source
    assert "DOCUMENT_TARGET_REQUIRED" in api
    assert "retryDocument(item.symbol, doc)" in ui
    assert "await refresh();" not in ui[ui.index("async function crawl"):ui.index("return (", ui.index("async function crawl"))]
