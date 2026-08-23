from __future__ import annotations

from dataclasses import asdict

from .domain import EventType, LedgerEvent, PortfolioState, PositionState, TaxLot


class AccountingError(ValueError):
    pass


def _position(state: PortfolioState, symbol: str) -> PositionState:
    symbol = symbol.upper()
    if symbol not in state.positions:
        state.positions[symbol] = PositionState(symbol=symbol)
    return state.positions[symbol]


def _positive(value: float, field: str) -> float:
    value = float(value or 0)
    if value <= 0:
        raise AccountingError(f"{field} must be > 0")
    return value


def _add_lot(position: PositionState, event: LedgerEvent, quantity: float, cost_basis: float) -> None:
    lot_id = f"{position.symbol}:{event.id if event.id is not None else 'pending'}"
    position.lots.append(
        TaxLot(
            lot_id=lot_id,
            symbol=position.symbol,
            acquisition_date=event.trade_date,
            source_event_id=event.id,
            original_quantity=quantity,
            remaining_quantity=quantity,
            cost_basis=cost_basis,
            broker_code=event.broker_code,
            account_id=event.account_id,
        )
    )
    position.shares += quantity
    position.cost_basis += cost_basis


def _consume_fifo(position: PositionState, quantity: float, *, broker_code: str, account_id: str) -> float:
    """Consume FIFO lots inside one broker/account book and return disposed cost basis.

    Legacy UNASSIGNED events may consume across the consolidated book. Once a
    broker is explicitly assigned, a SELL must not silently dispose lots held at
    another broker/account.
    """
    remaining = quantity
    disposed_cost = 0.0
    broker_code = str(broker_code or "UNASSIGNED").upper()
    account_id = str(account_id or "PRIMARY").upper()
    lots = sorted(position.lots, key=lambda x: (x.acquisition_date, x.source_event_id or 0, x.lot_id))
    if broker_code != "UNASSIGNED":
        lots = [lot for lot in lots if lot.broker_code == broker_code and lot.account_id == account_id]
        available = sum(lot.remaining_quantity for lot in lots)
        if quantity > available + 1e-9:
            raise AccountingError(
                f"SELL {quantity} {position.symbol} exceeds shares {available} at {broker_code}/{account_id}"
            )

    for lot in lots:
        if remaining <= 1e-9:
            break
        if lot.remaining_quantity <= 1e-9:
            continue
        take = min(remaining, lot.remaining_quantity)
        unit_cost = lot.cost_basis / lot.remaining_quantity if lot.remaining_quantity > 0 else 0.0
        cost = take * unit_cost
        lot.remaining_quantity -= take
        lot.cost_basis = max(0.0, lot.cost_basis - cost)
        disposed_cost += cost
        remaining -= take
    if remaining > 1e-7:
        raise AccountingError(f"FIFO lot book is short by {remaining} shares for {position.symbol}")
    position.lots = [lot for lot in position.lots if lot.remaining_quantity > 1e-9]
    position.shares = max(0.0, position.shares - quantity)
    position.cost_basis = max(0.0, position.cost_basis - disposed_cost)
    if position.shares <= 1e-9:
        position.shares = 0.0
        position.cost_basis = 0.0
        position.lots = []
    return disposed_cost


def _allocate_stock_quantity(position: PositionState, added_quantity: float, *, broker_code: str, account_id: str) -> None:
    """Allocate stock dividends pro-rata across matching open lots without changing cost basis."""
    if position.shares <= 0 or not position.lots:
        raise AccountingError("Cannot allocate stock quantity to an empty lot book")
    matching = [lot for lot in position.lots if lot.remaining_quantity > 1e-9]
    broker_code = str(broker_code or "UNASSIGNED").upper()
    account_id = str(account_id or "PRIMARY").upper()
    if broker_code != "UNASSIGNED":
        matching = [lot for lot in matching if lot.broker_code == broker_code and lot.account_id == account_id]
        if not matching:
            raise AccountingError(f"No open lots for {position.symbol} at {broker_code}/{account_id}")
    before = sum(lot.remaining_quantity for lot in matching)
    if before <= 0:
        raise AccountingError("Cannot allocate stock quantity to an empty lot book")
    allocated = 0.0
    for index, lot in enumerate(matching):
        if index == len(matching) - 1:
            add = added_quantity - allocated
        else:
            add = added_quantity * (lot.remaining_quantity / before)
            allocated += add
        lot.remaining_quantity += add
    position.shares += added_quantity


def apply_event(state: PortfolioState, event: LedgerEvent) -> None:
    et = event.event_type
    fee_tax = float(event.fee or 0) + float(event.tax or 0)

    if et == EventType.POSITION_IMPORT:
        if not event.symbol:
            raise AccountingError("POSITION_IMPORT requires symbol")
        qty = _positive(event.quantity, "quantity")
        price = _positive(event.price, "price")
        p = _position(state, event.symbol)
        cost = qty * price
        _add_lot(p, event, qty, cost)
        state.external_contributions += cost
        return

    if et == EventType.BUY:
        if not event.symbol:
            raise AccountingError("BUY requires symbol")
        qty = _positive(event.quantity, "quantity")
        price = _positive(event.price, "price")
        p = _position(state, event.symbol)
        gross = qty * price
        acquisition_cost = gross + float(event.fee or 0)
        _add_lot(p, event, qty, acquisition_cost)
        state.cash -= gross + fee_tax
        state.fees_and_taxes += fee_tax
        return

    if et == EventType.SELL:
        if not event.symbol:
            raise AccountingError("SELL requires symbol")
        qty = _positive(event.quantity, "quantity")
        price = _positive(event.price, "price")
        p = _position(state, event.symbol)
        if qty > p.shares + 1e-9:
            raise AccountingError(f"SELL {qty} {p.symbol} exceeds owned shares {p.shares}")
        gross = qty * price
        disposed_cost = _consume_fifo(p, qty, broker_code=event.broker_code, account_id=event.account_id)
        pnl = gross - disposed_cost - fee_tax
        p.realized_pnl += pnl
        state.realized_pnl += pnl
        state.cash += gross - fee_tax
        state.fees_and_taxes += fee_tax
        return

    if et == EventType.CASH_DEPOSIT:
        amount = _positive(event.amount, "amount")
        state.cash += amount
        state.external_contributions += amount
        return

    if et == EventType.CASH_WITHDRAW:
        amount = _positive(event.amount, "amount")
        state.cash -= amount
        state.external_withdrawals += amount
        return

    if et == EventType.CASH_DIVIDEND:
        gross = _positive(event.amount, "amount")
        withholding = float(event.tax or 0)
        if withholding < 0 or withholding > gross + 1e-9:
            raise AccountingError("CASH_DIVIDEND tax must be between 0 and gross dividend amount")
        state.cash += gross - withholding
        state.dividend_income += gross
        state.fees_and_taxes += withholding
        return

    if et == EventType.FEE:
        amount = _positive(event.amount, "amount")
        state.cash -= amount
        state.fees_and_taxes += amount
        return

    if et == EventType.STOCK_DIVIDEND:
        if not event.symbol:
            raise AccountingError("STOCK_DIVIDEND requires symbol")
        qty = _positive(event.quantity, "quantity")
        p = _position(state, event.symbol)
        if p.shares <= 0:
            raise AccountingError("Cannot apply stock dividend to an empty position")
        _allocate_stock_quantity(p, qty, broker_code=event.broker_code, account_id=event.account_id)
        return

    if et == EventType.SPLIT:
        if not event.symbol:
            raise AccountingError("SPLIT requires symbol")
        ratio = _positive(event.ratio, "ratio")
        p = _position(state, event.symbol)
        if p.shares <= 0:
            raise AccountingError("Cannot split an empty position")
        broker_code = event.broker_code
        matching = p.lots if broker_code == "UNASSIGNED" else [lot for lot in p.lots if lot.broker_code == broker_code and lot.account_id == event.account_id]
        if not matching:
            raise AccountingError(f"No open lots for {p.symbol} at {broker_code}/{event.account_id}")
        added = 0.0
        for lot in matching:
            before = lot.remaining_quantity
            lot.remaining_quantity *= ratio
            added += lot.remaining_quantity - before
        p.shares += added
        return

    raise AccountingError(f"Unsupported event type: {et}")


def derive_state(events: list[LedgerEvent]) -> PortfolioState:
    state = PortfolioState()
    for event in events:
        apply_event(state, event)
    state.positions = {symbol: p for symbol, p in state.positions.items() if p.shares > 1e-9}
    return state


def state_as_dict(state: PortfolioState) -> dict:
    return {
        "cash": state.cash,
        "realized_pnl": state.realized_pnl,
        "dividend_income": state.dividend_income,
        "external_contributions": state.external_contributions,
        "external_withdrawals": state.external_withdrawals,
        "net_external_contributions": state.net_external_contributions,
        "fees_and_taxes": state.fees_and_taxes,
        "positions": {s: {**asdict(p), "average_cost": p.average_cost} for s, p in sorted(state.positions.items())},
    }


def external_flow(events: list[LedgerEvent]) -> float:
    """Return investor cash/asset flow into the portfolio for TWR neutralization."""
    flow = 0.0
    for e in events:
        if e.event_type == EventType.CASH_DEPOSIT:
            flow += float(e.amount or 0)
        elif e.event_type == EventType.CASH_WITHDRAW:
            flow -= float(e.amount or 0)
        elif e.event_type == EventType.POSITION_IMPORT:
            flow += float(e.quantity or 0) * float(e.price or 0)
    return flow
