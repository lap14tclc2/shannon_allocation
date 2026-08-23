from __future__ import annotations

from dataclasses import replace

from .domain import EventType, LedgerEvent

CASH_DIVIDEND_WITHHOLDING_RATE = 0.05
STOCK_DIVIDEND_SALE_TAX_RATE = 0.05
VIETNAM_PAR_VALUE_VND = 10_000.0


def _stock_dividend_taxable_pool(events: list[LedgerEvent], *, symbol: str, event_date: str) -> float:
    """Return remaining stock-dividend shares that still carry deferred 5% tax.

    QPort uses a transparent pool convention consistent with the tax rule for
    transfers of same-type shares: a later SELL consumes the outstanding taxable
    stock-dividend quantity until the dividend-share pool has been exhausted.
    """
    pool = 0.0
    for event in sorted(events, key=lambda e: (e.event_date, int(e.id or 0))):
        if event.event_date > event_date or str(event.symbol or "").upper() != symbol.upper():
            continue
        if event.event_type == EventType.STOCK_DIVIDEND:
            pool += float(event.quantity or 0)
        elif event.event_type == EventType.SELL and pool > 0:
            metadata = event.metadata or {}
            consumed = metadata.get("stock_dividend_taxable_quantity")
            if consumed is None:
                consumed = min(pool, float(event.quantity or 0))
            pool = max(0.0, pool - float(consumed or 0))
    return pool


def apply_dividend_tax_policy(event: LedgerEvent, prior_events: list[LedgerEvent]) -> LedgerEvent:
    """Attach deterministic dividend-related taxes to a ledger event.

    * Cash dividend: 5% withholding on gross dividend amount.
    * Stock dividend: no investment-income PIT when shares are received. When
      taxable dividend shares are sold, 5% is applied to par value per share;
      if the transfer price is below par, the lower transfer/market price is the
      investment-income tax basis for that sale.

    User-entered SELL tax remains additive (for example ordinary securities
    transfer tax). Existing automatic tax metadata is removed before a corrected
    event is recalculated, preventing double taxation on edits.
    """
    metadata = dict(event.metadata or {})

    previous_cash_auto = float(metadata.get("cash_dividend_withholding_tax") or 0)
    previous_stock_auto = float(metadata.get("stock_dividend_sale_tax") or 0)
    manual_tax = max(0.0, float(event.tax or 0) - previous_cash_auto - previous_stock_auto)

    for key in (
        "cash_dividend_withholding_rate",
        "cash_dividend_withholding_tax",
        "cash_dividend_gross_amount",
        "cash_dividend_net_amount",
        "stock_dividend_sale_tax_rate",
        "stock_dividend_sale_tax",
        "stock_dividend_taxable_quantity",
        "stock_dividend_tax_par_value",
        "stock_dividend_tax_basis_per_share",
        "stock_dividend_tax_basis_source",
    ):
        metadata.pop(key, None)

    tax = manual_tax
    if event.event_type == EventType.CASH_DIVIDEND:
        gross = float(event.amount or 0)
        withholding = gross * CASH_DIVIDEND_WITHHOLDING_RATE
        tax += withholding
        metadata.update({
            "cash_dividend_withholding_rate": CASH_DIVIDEND_WITHHOLDING_RATE,
            "cash_dividend_withholding_tax": withholding,
            "cash_dividend_gross_amount": gross,
            "cash_dividend_net_amount": max(0.0, gross - tax),
        })

    elif event.event_type == EventType.SELL and event.symbol:
        pool = _stock_dividend_taxable_pool(
            prior_events,
            symbol=event.symbol,
            event_date=event.event_date,
        )
        taxable_quantity = min(float(event.quantity or 0), pool)
        sale_price = float(event.price or 0)
        basis_per_share = min(VIETNAM_PAR_VALUE_VND, sale_price) if sale_price > 0 else VIETNAM_PAR_VALUE_VND
        basis_source = "TRANSFER_PRICE_BELOW_PAR" if 0 < sale_price < VIETNAM_PAR_VALUE_VND else "PAR_VALUE"
        deferred_tax = taxable_quantity * basis_per_share * STOCK_DIVIDEND_SALE_TAX_RATE
        tax += deferred_tax
        metadata.update({
            "stock_dividend_sale_tax_rate": STOCK_DIVIDEND_SALE_TAX_RATE,
            "stock_dividend_sale_tax": deferred_tax,
            "stock_dividend_taxable_quantity": taxable_quantity,
            "stock_dividend_tax_par_value": VIETNAM_PAR_VALUE_VND,
            "stock_dividend_tax_basis_per_share": basis_per_share,
            "stock_dividend_tax_basis_source": basis_source,
        })

    return replace(event, tax=tax, metadata=metadata)
