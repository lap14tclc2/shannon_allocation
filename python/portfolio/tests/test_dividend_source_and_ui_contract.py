from pathlib import Path

REPO_DIR = Path(__file__).resolve().parents[3]
PYTHON_DIR = REPO_DIR / "python"
PORTFOLIO_DIR = PYTHON_DIR / "portfolio"
FRONTEND_SRC = REPO_DIR / "frontend" / "src"


def test_transaction_form_hides_manual_dividends_but_keeps_paid_share_purchases():
    source = (FRONTEND_SRC / "pages" / "TransactionsPage.jsx").read_text(encoding="utf-8")
    assert "const TYPE_VALUES = ['POSITION_IMPORT','CASH_DEPOSIT','BUY','SELL','CASH_WITHDRAW','SPLIT','FEE'];" in source
    assert "paid rights/new-issue subscription" in source
    assert "phát hành thêm/quyền mua có trả tiền" in source
    assert "const DIVIDEND_TYPES = new Set(['CASH_DIVIDEND', 'STOCK_DIVIDEND']);" in source
    assert "AUTO · read only" in source
    assert "if (DIVIDEND_TYPES.has(row.event_type)) return;" in source


def test_holding_expand_surfaces_broker_dividend_receipts_and_uppercase_symbol():
    source = (FRONTEND_SRC / "pages" / "PortfolioDashboardPage.jsx").read_text(encoding="utf-8")
    assert "brokerDividendReceipts" in source
    assert "operations?.dividend_receipts_by_broker" in source
    assert "stock_dividend_shares_received" in source
    assert "cash_dividend_net" in source
    assert "Stock dividends received" in source
    assert "Net cash dividends" in source
    assert "String(p.symbol || '').toUpperCase()" in source
    assert 'className="holding-info-button"' in source
    assert "Fundamental-analysis overlay is reserved for a future update." in source


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
    assert "detected events never auto-post" not in source
    assert "auto-post idempotent ledger events on payment date" in source


def test_final_typography_layer_increases_readability_and_uppercases_scan_labels():
    css = (FRONTEND_SRC / "ui-polish.css").read_text(encoding="utf-8")
    entry = (FRONTEND_SRC / "entry-client.jsx").read_text(encoding="utf-8")
    assert "body {\n  font-size: 14px;" in css
    assert ".app-nav-links a" in css
    assert "text-transform: uppercase" in css
    assert ".ranking th" in css
    assert ".holding-info-button" in css
    assert ".holding-source-table" in css and "min-width: 1180px" in css
    assert "import './ui-polish.css';" in entry
    assert entry.rfind("import './ui-polish.css';") > entry.rfind("import './auth.css';")
