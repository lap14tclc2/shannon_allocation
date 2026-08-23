from __future__ import annotations

from dataclasses import asdict

from .domain import EventType, LedgerEvent, PortfolioState, PositionState


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


def apply_event(state: PortfolioState, event: LedgerEvent) -> None:
    et = event.event_type
    fee_tax = float(event.fee or 0) + float(event.tax or 0)

    if et == EventType.POSITION_IMPORT:
        if not event.symbol:
            raise AccountingError("POSITION_IMPORT requires symbol")
        qty = _positive(event.quantity, "quantity")
        price = _positive(event.price, "price")
        p = _position(state, event.symbol)
        p.cost_basis += qty * price
        p.shares += qty
        state.external_contributions += qty * price
        return

    if et == EventType.BUY:
        if not event.symbol:
            raise AccountingError("BUY requires symbol")
        qty = _positive(event.quantity, "quantity")
        price = _positive(event.price, "price")
        p = _position(state, event.symbol)
        gross = qty * price
        p.cost_basis += gross + float(event.fee or 0)
        p.shares += qty
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
            raise AccountingError(
                f"SELL {qty} {p.symbol} exceeds owned shares {p.shares}"
            )
        avg = p.average_cost
        gross = qty * price
        pnl = qty * (price - avg) - fee_tax
        p.realized_pnl += pnl
        state.realized_pnl += pnl
        p.shares -= qty
        p.cost_basis = max(0.0, p.cost_basis - qty * avg)
        if p.shares <= 1e-9:
            p.shares = 0.0
            p.cost_basis = 0.0
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
        amount = _positive(event.amount, "amount")
        state.cash += amount
        state.dividend_income += amount
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
        p.shares += qty
        # Cost basis is unchanged; average cost falls mechanically.
        return

    if et == EventType.SPLIT:
        if not event.symbol:
            raise AccountingError("SPLIT requires symbol")
        ratio = _positive(event.ratio, "ratio")
        p = _position(state, event.symbol)
        if p.shares <= 0:
            raise AccountingError("Cannot split an empty position")
        p.shares *= ratio
        # Cost basis is unchanged; average cost changes inversely with ratio.
        return

    raise AccountingError(f"Unsupported event type: {et}")


def derive_state(events: list[LedgerEvent]) -> PortfolioState:
    state = PortfolioState()
    for event in events:
        apply_event(state, event)
    state.positions = {
        symbol: p for symbol, p in state.positions.items()
        if p.shares > 1e-9
    }
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
        "positions": {
            s: {
                **asdict(p),
                "average_cost": p.average_cost,
            }
            for s, p in sorted(state.positions.items())
        },
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
