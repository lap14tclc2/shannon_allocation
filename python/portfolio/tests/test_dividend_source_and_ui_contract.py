from pathlib import Path

REPO_DIR = Path(__file__).resolve().parents[3]
PYTHON_DIR = REPO_DIR / "python"
PORTFOLIO_DIR = PYTHON_DIR / "portfolio"
FRONTEND_SRC = REPO_DIR / "frontend" / "src"


def test_transaction_form_keeps_dividends_readonly_and_has_broker_specific_sell_flow():
    source = (FRONTEND_SRC / "pages" / "TransactionsPage.jsx").read_text(encoding="utf-8")
    assert "const DIVIDEND_TYPES = new Set(['CASH_DIVIDEND', 'STOCK_DIVIDEND']);" in source
    assert "const EDITABLE_TYPES = new Set(['POSITION_IMPORT', 'BUY', 'SELL']);" in source
    assert "Giao dịch đã ghi không thể xóa" in source
    assert "Nguồn cổ phiếu cần bán" in source
    assert "CTCK đang lưu ký" in source
    assert "Tổng tiền bán trước phí/thuế" in source
    assert "Giá bán bình quân" in source
    assert "Cổ phiếu ở CTCK khác không được dùng để bù" in source
    assert "deletePortfolioTransaction" not in source


def test_current_dashboard_surfaces_custody_broker_tree_and_source_specific_sell_action():
    dashboard = (FRONTEND_SRC / "pages" / "VietnamesePortfolioDashboard.jsx").read_text(encoding="utf-8")
    tree = (FRONTEND_SRC / "components" / "HoldingSourceTree.jsx").read_text(encoding="utf-8")
    books = (FRONTEND_SRC / "lib" / "holdingBooks.js").read_text(encoding="utf-8")
    assert "<HoldingSourceTree" in dashboard
    assert "listPortfolioTransactions" in dashboard
    assert "deriveHoldingBooks" in dashboard
    assert "CTCK đang lưu ký" in tree
    assert "Bán từ" in tree
    assert "action: 'sell'" in tree
    assert "broker: book.broker_code" in tree
    assert "account: book.account_id" in tree
    assert "Cần gán CTCK trước khi bán" in tree
    assert "eligibleLots" in books
    assert "allocateStockDividend" in books


def test_dividend_tree_groups_provider_source_and_expands_to_events():
    source = (FRONTEND_SRC / "components" / "DividendTree.jsx").read_text(encoding="utf-8")
    assert "function SourceGroups" in source
    assert "Nguồn dữ liệu:" in source
    assert 'className="dividend-tree-node dividend-tree-source" open' in source
    assert "<EventLeaf" in source
    assert "Nguồn dữ liệu" in source
    # The source node is open when its parent year is expanded, so the event
    # leaves are immediately visible rather than requiring an extra hidden load.
    assert "sourceEvents.map" in source


def test_auto_dividend_ledger_records_entitlement_date_broker_allocations():
    source = (PORTFOLIO_DIR / "automated_service.py").read_text(encoding="utf-8")
    assert "def _broker_account_entitlements" in source
    assert '"broker_account_allocations"' in source
    assert 'overview["dividend_receipts_by_broker"]' in source
    assert '"broker_allocation_basis": "ENTITLEMENT_DATE_OPEN_LOTS"' in source
    assert "cash_dividend_net" in source
    assert "stock_dividend_shares_received" in source


def test_dividend_history_uses_one_canonical_runtime_source_and_dedupes_old_cache():
    source = (PORTFOLIO_DIR / "dividend_store.py").read_text(encoding="utf-8")
    assert "self.stop_on_first_data = True if using_defaults" in source
    assert "SINGLE_CANONICAL_SOURCE_PLUS_ECONOMIC_EVENT_DEDUPE" in source
    assert "def _same_economic_event" in source
    assert 'db.execute("DELETE FROM dividend_events WHERE symbol = ?", (symbol,))' in source
    assert '"canonical_source": canonical_source' in source
    assert '"sqlite_cached_canonical_dividend"' in source


def test_ai_export_contains_full_audit_categories_without_client_side_truncation():
    source = (FRONTEND_SRC / "lib" / "aiExport.js").read_text(encoding="utf-8")
    assert "qport-ai-export-v5" in source
    assert "getLatestDividend" in source
    assert "dividend_history_by_symbol" in source
    assert "Dividend receipts by broker/account" in source
    assert "Canonical dividend provider history" in source
    assert "broker_account_allocations" in source
    assert "Client-side export does not truncate API responses." in source
    assert "MAX_SNAPSHOTS" not in source
    assert "MAX_ACTIVITY" not in source


def test_investor_typography_layer_keeps_finance_numbers_readable():
    css = (FRONTEND_SRC / "ui-polish.css").read_text(encoding="utf-8")
    entry = (FRONTEND_SRC / "entry-vercel.jsx").read_text(encoding="utf-8")
    assert "font-variant-numeric: tabular-nums" in css
    assert ".holding-source-tree" in css
    assert ".transaction-sell-form" in css
    assert ".sell-readonly-grid input[readonly]" in css
    assert "import './ui-polish.css';" in entry
