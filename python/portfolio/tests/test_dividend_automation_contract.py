from pathlib import Path

REPO_DIR = Path(__file__).resolve().parents[3]
PYTHON_DIR = REPO_DIR / "python"
FRONTEND_SRC = REPO_DIR / "frontend" / "src"


def test_primary_server_uses_automated_portfolio_service():
    source = (PYTHON_DIR / "serve.py").read_text(encoding="utf-8")
    assert "AutomatedPortfolioService" in source
    assert "buyhold_server.CorrectablePortfolioService = AutomatedPortfolioService" in source


def test_dividend_automation_is_payment_date_driven_and_idempotent():
    source = (PYTHON_DIR / "portfolio" / "automated_service.py").read_text(encoding="utf-8")
    assert "payment_date > today" in source
    assert "corporate_action_postings" in source
    assert "if (action_id, posting_type) in posted" in source
    assert '"posting_policy": "AUTOMATIC_ON_PAYMENT_DATE_IDEMPOTENT"' in source
    assert "_previous_day(ex_date)" in source


def test_cash_and_stock_dividends_become_ledger_transactions():
    source = (PYTHON_DIR / "portfolio" / "automated_service.py").read_text(encoding="utf-8")
    assert '"event_type": "CASH_DIVIDEND"' in source
    assert '"event_type": "STOCK_DIVIDEND"' in source
    assert '"auto_generated": True' in source
    assert '"entitlement_shares": entitled_shares' in source
    assert "entitled_shares * cash_per_share" in source
    assert "entitled_shares * ratio" in source


def test_cash_percentage_fallback_supports_vietnamese_percent_announcements():
    source = (PYTHON_DIR / "portfolio" / "automated_service.py").read_text(encoding="utf-8")
    assert "VIETNAM_PAR_VALUE_VND = 10_000.0" in source
    assert "cash_rate_percent" in source
    assert "tiền mặt|cash" in source


def test_received_dividend_ui_and_transaction_sources_are_visible():
    received = (FRONTEND_SRC / "components" / "ReceivedDividendsPanel.jsx").read_text(encoding="utf-8")
    transactions = (FRONTEND_SRC / "pages" / "TransactionsPage.jsx").read_text(encoding="utf-8")
    entry = (FRONTEND_SRC / "entry-client.jsx").read_text(encoding="utf-8")
    assert "Dividends received" in received
    assert "CASH_DIVIDEND" in received and "STOCK_DIVIDEND" in received
    assert "AUTO corporate action" in received
    assert "Broker" in received and "Account" in received
    assert "<th>Broker</th>" in transactions
    assert "row.metadata?.broker_code" in transactions
    assert "row.metadata?.account_id" in transactions
    assert "PortfolioPage" in entry
