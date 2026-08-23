from pathlib import Path

import pytest

from portfolio.accounting import derive_state
from portfolio.domain import EventType, LedgerEvent
from portfolio.tax_policy import apply_dividend_tax_policy

REPO_DIR = Path(__file__).resolve().parents[3]
FRONTEND_SRC = REPO_DIR / "frontend" / "src"
PORTFOLIO_DIR = REPO_DIR / "python" / "portfolio"


def event(kind: str, **kwargs) -> LedgerEvent:
    return LedgerEvent(
        id=kwargs.pop("id", None),
        event_type=EventType(kind),
        event_date=kwargs.pop("event_date", "2026-08-23"),
        **kwargs,
    )


def test_cash_dividend_policy_withholds_five_percent_and_accounts_net_cash():
    gross = 7_000_000
    raw = event("CASH_DIVIDEND", symbol="ACB", amount=gross)
    taxed = apply_dividend_tax_policy(raw, [])

    assert taxed.tax == pytest.approx(350_000)
    assert taxed.metadata["cash_dividend_withholding_rate"] == pytest.approx(0.05)
    assert taxed.metadata["cash_dividend_net_amount"] == pytest.approx(6_650_000)

    state = derive_state([taxed])
    assert state.dividend_income == pytest.approx(gross)
    assert state.fees_and_taxes == pytest.approx(350_000)
    assert state.cash == pytest.approx(6_650_000)


def test_stock_dividend_tax_is_deferred_until_sell_and_uses_par_value_pool():
    prior = [
        event("POSITION_IMPORT", id=1, event_date="2026-01-01", symbol="ACB", quantity=10_000, price=20_000),
        event("STOCK_DIVIDEND", id=2, event_date="2026-08-01", symbol="ACB", quantity=1_300),
    ]
    sell = event("SELL", id=3, event_date="2026-09-01", symbol="ACB", quantity=500, price=25_000)
    taxed = apply_dividend_tax_policy(sell, prior)

    assert taxed.metadata["stock_dividend_taxable_quantity"] == pytest.approx(500)
    assert taxed.metadata["stock_dividend_tax_par_value"] == pytest.approx(10_000)
    assert taxed.metadata["stock_dividend_sale_tax_rate"] == pytest.approx(0.05)
    assert taxed.metadata["stock_dividend_sale_tax"] == pytest.approx(250_000)
    assert taxed.tax == pytest.approx(250_000)


def test_prior_sell_reduces_remaining_stock_dividend_taxable_pool():
    stock = event("STOCK_DIVIDEND", id=1, event_date="2026-08-01", symbol="ACB", quantity=1_300)
    first_sell = apply_dividend_tax_policy(
        event("SELL", id=2, event_date="2026-08-10", symbol="ACB", quantity=1_000, price=25_000),
        [stock],
    )
    second_sell = apply_dividend_tax_policy(
        event("SELL", id=3, event_date="2026-08-20", symbol="ACB", quantity=500, price=26_000),
        [stock, first_sell],
    )
    assert second_sell.metadata["stock_dividend_taxable_quantity"] == pytest.approx(300)
    assert second_sell.metadata["stock_dividend_sale_tax"] == pytest.approx(150_000)


def test_automated_service_backfills_risk_history_and_refreshes_derived_history():
    source = (PORTFOLIO_DIR / "automated_service.py").read_text(encoding="utf-8")
    assert "today - timedelta(days=550)" in source
    assert '"risk_ready": self.store.market_price_count(symbol) >= 260' in source
    assert '"portfolio_sync"] = "LEDGER_DERIVED_IMMEDIATE"' in source
    assert "self._refresh_derived_history()" in source


def test_desktop_tables_fill_card_width_and_mobile_scroll_contract_remains():
    alignment = (FRONTEND_SRC / "table-alignment.css").read_text(encoding="utf-8")
    responsive = (FRONTEND_SRC / "responsive.css").read_text(encoding="utf-8")
    entry = (FRONTEND_SRC / "entry-client.jsx").read_text(encoding="utf-8")
    assert "@media (min-width: 720px)" in alignment
    assert "width: 100% !important" in alignment
    assert ".holding-source-table" in alignment
    assert "width: max-content" in responsive
    assert "import './table-alignment.css';" in entry


def test_risk_and_performance_pages_surface_interpretation_and_tax_impact():
    risk = (FRONTEND_SRC / "pages" / "RiskPage.jsx").read_text(encoding="utf-8")
    performance = (FRONTEND_SRC / "pages" / "PerformancePage.jsx").read_text(encoding="utf-8")
    assert "Risk interpretation" in risk
    assert "Correlation regime" in risk
    assert "Volatility regime" in risk
    assert "Risk coverage" in risk
    assert "Income after dividend tax" in performance
    assert "cash_dividend_tax" in performance
    assert "stock_dividend_sale_tax" in performance
    assert "History readiness" in performance
