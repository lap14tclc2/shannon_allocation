from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_finance_catalog_derives_status_before_sql_pagination():
    source = (ROOT / "python" / "portfolio" / "finance_catalog.py").read_text(encoding="utf-8")
    assert "status: str | None = None" in source
    assert "document_success" in source
    assert "document_failed" in source
    assert "document_pending" in source
    assert "AS crawl_status" in source
    assert "SELECT COUNT(*) AS count FROM ({base_query}) AS filtered_securities" in source
    assert "ORDER BY s.symbol LIMIT ? OFFSET ?" in source
    for status in ("SUCCESS", "PARTIAL", "FAILED", "PENDING", "NOT_CRAWLED"):
        assert f'"{status}"' in source


def test_admin_finance_data_route_threads_status_filter():
    source = (ROOT / "app" / "main.py").read_text(encoding="utf-8")
    route = source[source.index('@app.get("/api/admin/finance-data")'):source.index('@app.post("/api/admin/finance-data/universe")')]
    assert "status: str | None = Query(default=None)" in route
    assert "list_securities(offset, limit, exchange, status)" in route


def test_finance_data_ui_has_status_filter_and_document_group_statuses():
    source = (ROOT / "frontend" / "src" / "pages" / "FinanceDataPage.jsx").read_text(encoding="utf-8")
    api_source = (ROOT / "frontend" / "src" / "lib" / "api.js").read_text(encoding="utf-8")
    assert "CRAWL_STATUS_OPTIONS" in source
    assert "value={crawlStatus}" in source
    assert "status: crawlStatus" in source
    assert "summarizeDocuments" in source
    assert "STATUS_META[doc.status]" in source
    assert "Đang chờ" in source
    assert "params.status" in api_source
