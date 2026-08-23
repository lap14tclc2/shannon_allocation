from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class EventType(str, Enum):
    POSITION_IMPORT = "POSITION_IMPORT"
    BUY = "BUY"
    SELL = "SELL"
    CASH_DEPOSIT = "CASH_DEPOSIT"
    CASH_WITHDRAW = "CASH_WITHDRAW"
    CASH_DIVIDEND = "CASH_DIVIDEND"
    STOCK_DIVIDEND = "STOCK_DIVIDEND"
    SPLIT = "SPLIT"
    FEE = "FEE"


class DataQuality(str, Enum):
    VALID = "VALID"
    STALE = "STALE"
    PARTIAL = "PARTIAL"
    MISSING = "MISSING"


@dataclass(frozen=True)
class LedgerEvent:
    id: int | None
    event_type: EventType
    event_date: str
    symbol: str | None = None
    quantity: float = 0.0
    price: float = 0.0
    fee: float = 0.0
    tax: float = 0.0
    amount: float = 0.0
    ratio: float = 0.0
    note: str = ""
    created_by: str = "local"
    created_at: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def trade_date(self) -> str:
        return str((self.metadata or {}).get("trade_date") or self.event_date)

    @property
    def settlement_date(self) -> str | None:
        value = (self.metadata or {}).get("settlement_date")
        return str(value) if value else None

    @property
    def account_id(self) -> str:
        return str((self.metadata or {}).get("account_id") or "PRIMARY")


@dataclass
class TaxLot:
    lot_id: str
    symbol: str
    acquisition_date: str
    source_event_id: int | None
    original_quantity: float
    remaining_quantity: float
    cost_basis: float
    account_id: str = "PRIMARY"

    @property
    def unit_cost(self) -> float:
        return self.cost_basis / self.remaining_quantity if self.remaining_quantity > 0 else 0.0


@dataclass
class PositionState:
    symbol: str
    shares: float = 0.0
    cost_basis: float = 0.0
    realized_pnl: float = 0.0
    lots: list[TaxLot] = field(default_factory=list)

    @property
    def average_cost(self) -> float:
        return self.cost_basis / self.shares if self.shares > 0 else 0.0


@dataclass
class PortfolioState:
    cash: float = 0.0
    positions: dict[str, PositionState] = field(default_factory=dict)
    realized_pnl: float = 0.0
    dividend_income: float = 0.0
    external_contributions: float = 0.0
    external_withdrawals: float = 0.0
    fees_and_taxes: float = 0.0

    @property
    def net_external_contributions(self) -> float:
        return self.external_contributions - self.external_withdrawals
