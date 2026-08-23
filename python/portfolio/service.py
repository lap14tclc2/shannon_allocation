from __future__ import annotations

from dataclasses import asdict
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

from .accounting import AccountingError, apply_event, derive_state, external_flow, state_as_dict
from .analytics import drawdown_from_twr_indices, period_returns, xirr
from .domain import DataQuality, EventType, LedgerEvent
from .market_data import AutoMarketData, MarketDataError, frame_to_price_rows
from .risk import portfolio_risk
from .storage import PortfolioStore

VN_TZ = ZoneInfo("Asia/Ho_Chi_Minh")


class PortfolioService:
    """Application service for the buy-and-hold information system.

    This service never creates a BUY/SELL event by itself. Only explicit user
    requests append ledger events; market/risk calculations are informational.
    """

    def __init__(self, store: PortfolioStore | None = None, market=None) -> None:
        self.store = store or PortfolioStore()
        self.market = market or AutoMarketData()

    @staticmethod
    def today_vn() -> str:
        return datetime.now(VN_TZ).date().isoformat()

    def current_state(self):
        return derive_state(self.store.list_events())

    def _serialize_event(self, e: LedgerEvent) -> dict:
        row = asdict(e)
        row["event_type"] = e.event_type.value
        return row

    def transactions(self) -> list[dict]:
        return [self._serialize_event(e) for e in reversed(self.store.list_events())]

    def append_event(self, payload: dict, created_by: str = "local") -> dict:
        try:
            event_type = EventType(str(payload.get("event_type") or "").upper())
        except ValueError as exc:
            raise ValueError(f"Unknown event_type: {payload.get('event_type')}") from exc

        event_date = str(payload.get("event_date") or self.today_vn())
        try:
            date.fromisoformat(event_date)
        except ValueError as exc:
            raise ValueError("event_date must be YYYY-MM-DD") from exc

        symbol = str(payload.get("symbol") or "").strip().upper() or None
        event = LedgerEvent(
            id=None,
            event_type=event_type,
            event_date=event_date,
            symbol=symbol,
            quantity=float(payload.get("quantity") or 0),
            price=float(payload.get("price") or 0),
            fee=float(payload.get("fee") or 0),
            tax=float(payload.get("tax") or 0),
            amount=float(payload.get("amount") or 0),
            ratio=float(payload.get("ratio") or 0),
            note=str(payload.get("note") or ""),
            created_by=str(payload.get("created_by") or created_by or "local"),
            metadata=dict(payload.get("metadata") or {}),
        )

        # Validate against current ledger before persisting. Ledger history stays
        # immutable; invalid sells/cash operations fail rather than being patched.
        state = self.current_state()
        apply_event(state, event)
        if event_type in {EventType.BUY, EventType.CASH_WITHDRAW, EventType.FEE} and state.cash < -1e-6:
            raise AccountingError(
                "Event would make cash negative. Record/import the funding first."
            )
        eid = self.store.append_event(event)
        return {"ok": True, "event_id": eid, "event": self._serialize_event(event)}

    def set_reference_weights(self, weights: dict[str, float]) -> dict:
        normalized = {str(s).upper(): float(w) for s, w in (weights or {}).items() if float(w) > 0}
        self.store.set_reference_weights(normalized)
        return {"ok": True, "reference_weights": normalized}

    @staticmethod
    def _position_status(weight: float, reference: float | None) -> str:
        if reference is None or reference <= 0:
            return "HOLD"
        if weight < reference * 0.80:
            return "ADD"
        if weight > reference * 1.20:
            return "REVIEW"
        return "HOLD"

    def _mark_to_market(self, state, prices: dict[str, dict], risk: dict | None = None) -> tuple[list[dict], float]:
        rows = []
        equity = 0.0
        for symbol, position in sorted(state.positions.items()):
            quote = prices.get(symbol)
            price = float(quote["close"]) if quote and quote.get("close") is not None else 0.0
            value = position.shares * price
            equity += value
            rows.append(
                {
                    "symbol": symbol,
                    "shares": position.shares,
                    "average_cost": position.average_cost,
                    "price": price if quote else None,
                    "price_date": quote.get("trading_date") if quote else None,
                    "price_source": quote.get("source") if quote else None,
                    "market_value": value,
                    "unrealized_pnl": value - position.cost_basis if quote else 0.0,
                    "unrealized_return": (
                        value / position.cost_basis - 1.0
                        if quote and position.cost_basis > 0 else None
                    ),
                }
            )
        nav = equity + state.cash
        refs = self.store.get_reference_weights()
        risk_contrib = (risk or {}).get("risk_contributions") or {}
        erc_ref = (risk or {}).get("erc_reference_weights") or {}
        for row in rows:
            row["weight"] = row["market_value"] / nav if nav > 0 else 0.0
            row["reference_weight"] = refs.get(row["symbol"])
            row["risk_contribution"] = risk_contrib.get(row["symbol"])
            row["erc_reference_weight"] = erc_ref.get(row["symbol"])
            row["status"] = self._position_status(row["weight"], refs.get(row["symbol"]))
        rows.sort(key=lambda p: p["market_value"], reverse=True)
        return rows, equity

    def _histories(self, symbols: list[str], end: str | None = None, limit: int = 320) -> dict[str, list[dict]]:
        return {s: self.store.price_history(s, limit=limit, end=end) for s in symbols}

    def risk(self, as_of: str | None = None) -> dict:
        state = self.current_state()
        symbols = sorted(state.positions)
        prices = self.store.latest_prices(symbols, on_or_before=as_of)
        base_rows, _ = self._mark_to_market(state, prices)
        result = portfolio_risk(base_rows, self._histories(symbols, end=as_of))
        return {
            **result,
            "as_of": as_of or max((p.get("trading_date") for p in prices.values()), default=None),
            "policy": "INFORMATION_ONLY",
        }

    def dashboard(self) -> dict:
        state = self.current_state()
        symbols = sorted(state.positions)
        prices = self.store.latest_prices(symbols)
        risk = portfolio_risk(
            self._mark_to_market(state, prices)[0],
            self._histories(symbols),
        )
        positions, equity = self._mark_to_market(state, prices, risk=risk)
        nav = equity + state.cash
        latest_snapshot = self.store.latest_snapshot()
        official_snapshot = self.store.latest_snapshot(official_only=True)
        refs = self.store.get_reference_weights()
        return {
            "philosophy": "BUY_AND_HOLD_INFORMATION_SYSTEM",
            "portfolio": {
                **state_as_dict(state),
                "equity_value": equity,
                "nav": nav,
                "positions": positions,
                "reference_weights": refs,
            },
            "latest_snapshot": latest_snapshot,
            "latest_official_snapshot": official_snapshot,
            "risk": risk,
            "market_data": {
                "provider": self.market.health(),
                "latest_prices": prices,
                "status": self._price_quality(symbols, prices)[0],
            },
            "contribution_suggestions": self.contribution_suggestions(),
            "invariants": [
                "price movement never changes shares",
                "model output never changes shares",
                "time/year-end never changes shares",
                "only explicit ledger events change holdings or cash",
            ],
        }

    @staticmethod
    def _price_quality(symbols: list[str], prices: dict[str, dict]) -> tuple[str, str | None, list[str]]:
        if not symbols:
            return DataQuality.VALID.value, None, []
        missing = [s for s in symbols if s not in prices]
        if missing:
            dates = [p.get("trading_date") for p in prices.values() if p.get("trading_date")]
            return DataQuality.MISSING.value, max(dates) if dates else None, missing
        dates = {p.get("trading_date") for p in prices.values()}
        target = max(dates) if dates else None
        stale = [s for s in symbols if prices[s].get("trading_date") != target]
        return (DataQuality.STALE.value if stale else DataQuality.VALID.value), target, stale

    def _sync_symbol(self, symbol: str, today: date) -> dict:
        latest = self.store.latest_price(symbol)
        if latest and self.store.market_price_count(symbol) >= 260:
            start_date = date.fromisoformat(latest["trading_date"]) - timedelta(days=10)
        else:
            start_date = today - timedelta(days=550)
        start = start_date.isoformat()
        end = today.isoformat()
        df, source = self.market.daily_history_with_source(symbol, start, end)
        rows = frame_to_price_rows(symbol, df, source=source)
        self.store.upsert_market_prices(rows)
        return {
            "symbol": symbol,
            "source": source,
            "bars": len(rows),
            "latest": rows[-1]["trading_date"] if rows else None,
        }

    def sync_daily(self) -> dict:
        state = self.current_state()
        symbols = sorted(state.positions)
        today = datetime.now(VN_TZ).date()
        sync_rows = []
        errors = []
        for symbol in symbols:
            try:
                sync_rows.append(self._sync_symbol(symbol, today))
            except (MarketDataError, Exception) as exc:
                errors.append({"symbol": symbol, "error": str(exc)})

        prices = self.store.latest_prices(symbols)
        quality, snapshot_date, stale_symbols = self._price_quality(symbols, prices)
        if not snapshot_date:
            # Cash-only portfolios can still produce a valid daily snapshot.
            snapshot_date = today.isoformat()
            quality = DataQuality.VALID.value if not symbols else DataQuality.MISSING.value

        risk = portfolio_risk(
            self._mark_to_market(state, prices)[0],
            self._histories(symbols, end=snapshot_date),
        )
        positions, equity = self._mark_to_market(state, prices, risk=risk)
        nav = equity + state.cash

        prior_rows = [
            s for s in self.store.list_snapshots(limit=2000)
            if s["snapshot_date"] < snapshot_date
        ]
        prior = max(prior_rows, key=lambda s: s["snapshot_date"]) if prior_rows else None
        flows = self.store.events_after(prior["snapshot_date"] if prior else None, snapshot_date)
        flow = external_flow(flows)
        daily_return = None
        daily_pnl = None
        twr_index = 1.0
        if prior and float(prior.get("nav") or 0) > 0:
            prev_nav = float(prior["nav"])
            daily_pnl = nav - prev_nav - flow
            daily_return = daily_pnl / prev_nav
            twr_index = float(prior.get("twr_index") or 1.0) * (1.0 + daily_return)

        prior_indices = [
            float(s.get("twr_index") or 1.0)
            for s in sorted(prior_rows, key=lambda s: s["snapshot_date"])
        ]
        current_dd, max_dd = drawdown_from_twr_indices([*prior_indices, twr_index])
        total_pnl = nav - state.net_external_contributions
        official = quality == DataQuality.VALID.value and not errors

        snapshot = {
            "snapshot_date": snapshot_date,
            "cash": state.cash,
            "equity_value": equity,
            "nav": nav,
            "external_flow": flow,
            "daily_pnl": daily_pnl,
            "daily_return": daily_return,
            "twr_index": twr_index,
            "total_pnl": total_pnl,
            "current_drawdown": current_dd,
            "max_drawdown": max_dd,
            "volatility_63": risk.get("volatility_63"),
            "volatility_252": risk.get("volatility_252"),
            "hhi": risk.get("hhi"),
            "max_position_weight": risk.get("max_position_weight"),
            "data_quality": quality,
            "official": official,
        }
        self.store.save_snapshot(snapshot, positions)
        return {
            "ok": True,
            "snapshot": self.store.latest_snapshot(),
            "sync": sync_rows,
            "errors": errors,
            "stale_symbols": stale_symbols,
            "message": (
                "Official daily snapshot created."
                if official else
                "Snapshot is estimated/stale; holdings were not changed."
            ),
        }

    def performance(self) -> dict:
        snapshots = list(reversed(self.store.list_snapshots(limit=5000, official_only=True)))
        returns = period_returns(snapshots)
        state = self.current_state()
        terminal = snapshots[-1] if snapshots else None
        cashflows = []
        for e in self.store.list_events():
            d = date.fromisoformat(e.event_date)
            if e.event_type == EventType.CASH_DEPOSIT:
                cashflows.append((d, -float(e.amount or 0)))
            elif e.event_type == EventType.CASH_WITHDRAW:
                cashflows.append((d, float(e.amount or 0)))
            elif e.event_type == EventType.POSITION_IMPORT:
                cashflows.append((d, -float(e.quantity or 0) * float(e.price or 0)))
        if terminal and float(terminal.get("nav") or 0) > 0:
            cashflows.append((date.fromisoformat(terminal["snapshot_date"]), float(terminal["nav"])))
        irr = xirr(cashflows) if cashflows else None
        return {
            "returns": returns,
            "xirr": irr,
            "realized_pnl": state.realized_pnl,
            "dividend_income": state.dividend_income,
            "fees_and_taxes": state.fees_and_taxes,
            "net_external_contributions": state.net_external_contributions,
            "latest": terminal,
            "series": [
                {
                    "date": s["snapshot_date"],
                    "nav": s["nav"],
                    "twr_index": s["twr_index"],
                    "daily_return": s["daily_return"],
                    "drawdown": s["current_drawdown"],
                }
                for s in snapshots
            ],
        }

    def snapshots(self, limit: int = 365) -> list[dict]:
        return self.store.list_snapshots(limit=limit)

    def contribution_suggestions(self) -> dict:
        """BUY-only information for deploying existing cash toward underweights."""
        state = self.current_state()
        symbols = sorted(state.positions)
        if not symbols or state.cash <= 0:
            return {"available_cash": max(0.0, state.cash), "suggestions": [], "policy": "BUY_ONLY"}
        prices = self.store.latest_prices(symbols)
        positions, equity = self._mark_to_market(state, prices)
        nav = equity + state.cash
        refs = self.store.get_reference_weights()
        if refs and set(symbols).issubset(refs):
            targets = {s: refs[s] for s in symbols}
            policy = "REFERENCE_WEIGHT_DEFICITS"
        else:
            equal = 1.0 / len(symbols)
            targets = {s: equal for s in symbols}
            policy = "EQUAL_WEIGHT_DEFICITS"
        current = {p["symbol"]: p["market_value"] for p in positions}
        deficits = {s: max(0.0, targets[s] * nav - current.get(s, 0.0)) for s in symbols}
        total_deficit = sum(deficits.values())
        deployable = min(max(0.0, state.cash), total_deficit)
        suggestions = []
        if total_deficit > 0 and deployable > 0:
            for s in symbols:
                amount = deployable * deficits[s] / total_deficit
                if amount <= 0:
                    continue
                suggestions.append(
                    {
                        "symbol": s,
                        "amount": amount,
                        "target_weight": targets[s],
                        "current_weight": current.get(s, 0.0) / nav if nav > 0 else 0.0,
                        "action": "ADD",
                    }
                )
        suggestions.sort(key=lambda x: x["amount"], reverse=True)
        return {
            "available_cash": max(0.0, state.cash),
            "deployable_cash": deployable,
            "policy": policy,
            "suggestions": suggestions,
            "disclaimer": "Information only. No BUY event is created automatically.",
        }
