from __future__ import annotations

from dataclasses import asdict
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

from .accounting import AccountingError, apply_event, derive_state, external_flow, state_as_dict
from .analytics import period_returns, xirr
from .domain import DataQuality, EventType, LedgerEvent
from .market_data import AutoMarketData, MarketDataError, frame_to_price_rows
from .risk import portfolio_risk
from .storage import PortfolioStore

VN_TZ = ZoneInfo("Asia/Ho_Chi_Minh")


class PortfolioService:
    """Application service for the Buy & Hold portfolio information system.

    Market prices, risk calculations and time never create transactions. Only an
    explicit ledger event requested by the user may change shares or cash.
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
        state = self.current_state()
        apply_event(state, event)
        if event_type in {EventType.BUY, EventType.CASH_WITHDRAW, EventType.FEE} and state.cash < -1e-6:
            raise AccountingError("Event would make cash negative. Record/import the funding first.")
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
            cost_value = float(position.cost_basis)
            equity += value
            rows.append(
                {
                    "symbol": symbol,
                    "shares": position.shares,
                    "average_cost": position.average_cost,
                    "price": price if quote else None,
                    "price_date": quote.get("trading_date") if quote else None,
                    "price_source": quote.get("source") if quote else None,
                    "cost_value": cost_value,
                    "market_value": value,
                    "unrealized_pnl": value - cost_value if quote else 0.0,
                    "unrealized_return": (value / cost_value - 1.0 if quote and cost_value > 0 else None),
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

    def _histories(self, symbols: list[str], end: str | None = None, limit: int = 10000) -> dict[str, list[dict]]:
        return {s: self.store.price_history(s, limit=limit, end=end) for s in symbols}

    @staticmethod
    def _live_accounting(state, positions: list[dict], nav: float) -> dict:
        cost_value = sum(float(p.get("cost_value") or 0) for p in positions)
        unrealized = sum(float(p.get("unrealized_pnl") or 0) for p in positions)
        contributions = float(state.net_external_contributions)
        total_pnl = float(nav) - contributions
        return {
            "cost_value": cost_value,
            "unrealized_pnl": unrealized,
            "realized_pnl": float(state.realized_pnl),
            "dividend_income": float(state.dividend_income),
            "fees_and_taxes": float(state.fees_and_taxes),
            "net_external_contributions": contributions,
            "total_pnl": total_pnl,
            "total_return": (total_pnl / contributions) if contributions > 0 else None,
        }

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

    def _health(self, risk: dict, performance: dict, portfolio: dict, market_status: str) -> dict:
        flags = []
        if market_status != DataQuality.VALID.value:
            flags.append({"level": "WARNING", "code": "MARKET_DATA", "message": "Market data is not fully fresh."})
        if float(risk.get("max_position_weight") or 0) >= 0.40:
            flags.append({"level": "WARNING", "code": "CONCENTRATION", "message": "Largest position is at least 40% of NAV."})
        if float(risk.get("hhi") or 0) >= 0.25:
            flags.append({"level": "WARNING", "code": "HHI", "message": "Portfolio concentration is high (HHI >= 0.25)."})
        if risk.get("average_correlation") is not None and float(risk["average_correlation"]) >= 0.60:
            flags.append({"level": "WARNING", "code": "CORRELATION", "message": "Holdings have high average correlation."})
        if float(performance.get("current_drawdown") or 0) <= -0.20:
            flags.append({"level": "WARNING", "code": "DRAWDOWN", "message": "Current drawdown is at least 20%."})
        if risk.get("volatility_252") is not None and float(risk["volatility_252"]) >= 0.35:
            flags.append({"level": "WARNING", "code": "VOLATILITY", "message": "252D annualized volatility is high."})
        coverage = float((risk.get("quality") or {}).get("coverage_weight") or 0)
        if portfolio.get("positions") and coverage < 0.90:
            flags.append({"level": "WARNING", "code": "RISK_COVERAGE", "message": "Risk history coverage is below 90%."})
        return {
            "status": "ATTENTION" if flags else "HEALTHY",
            "flags": flags,
            "snapshot_count": performance.get("snapshot_count", 0),
            "official_snapshot_count": performance.get("official_snapshot_count", 0),
            "current_drawdown": performance.get("current_drawdown"),
            "max_drawdown": performance.get("max_drawdown"),
            "total_return": performance.get("total_return"),
            "cash_weight": (float(portfolio.get("cash") or 0) / float(portfolio.get("nav") or 1)) if float(portfolio.get("nav") or 0) > 0 else 0.0,
            "effective_positions": risk.get("effective_positions"),
            "average_correlation": risk.get("average_correlation"),
            "max_correlation": risk.get("max_correlation"),
            "diversification_ratio": risk.get("diversification_ratio"),
            "largest_risk_symbol": risk.get("largest_risk_symbol"),
            "largest_risk_contribution": risk.get("largest_risk_contribution"),
            "risk_coverage": coverage,
            "daily_var_95": risk.get("daily_var_95"),
            "daily_cvar_95": risk.get("daily_cvar_95"),
        }

    def dashboard(self) -> dict:
        state = self.current_state()
        symbols = sorted(state.positions)
        prices = self.store.latest_prices(symbols)
        base_positions, _ = self._mark_to_market(state, prices)
        risk = portfolio_risk(base_positions, self._histories(symbols))
        positions, equity = self._mark_to_market(state, prices, risk=risk)
        nav = equity + state.cash
        accounting = self._live_accounting(state, positions, nav)
        latest_snapshot = self.store.latest_snapshot()
        official_snapshot = self.store.latest_snapshot(official_only=True)
        refs = self.store.get_reference_weights()
        market_status = self._price_quality(symbols, prices)[0]
        perf = self.performance()
        portfolio = {
            **state_as_dict(state),
            **accounting,
            "equity_value": equity,
            "nav": nav,
            "positions": positions,
            "reference_weights": refs,
        }
        return {
            "philosophy": "BUY_AND_HOLD_INFORMATION_SYSTEM",
            "today": self.today_vn(),
            "portfolio": portfolio,
            "latest_snapshot": latest_snapshot,
            "latest_official_snapshot": official_snapshot,
            "performance_summary": perf,
            "risk": risk,
            "health": self._health(risk, perf, portfolio, market_status),
            "market_data": {
                "provider": self.market.health(),
                "latest_prices": prices,
                "status": market_status,
            },
            "contribution_suggestions": self.contribution_suggestions(),
            "invariants": [
                "price movement never changes shares",
                "risk information never changes shares",
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
        symbol_events = [e for e in self.store.list_events() if e.symbol and e.symbol.upper() == symbol.upper()]
        earliest_event = min((date.fromisoformat(e.event_date) for e in symbol_events), default=None)
        if latest and self.store.market_price_count(symbol) >= 260:
            start_date = date.fromisoformat(latest["trading_date"]) - timedelta(days=10)
        elif earliest_event:
            start_date = earliest_event - timedelta(days=10)
        else:
            start_date = today - timedelta(days=550)
        df, source = self.market.daily_history_with_source(symbol, start_date.isoformat(), today.isoformat())
        rows = frame_to_price_rows(symbol, df, source=source)
        self.store.upsert_market_prices(rows)
        return {
            "symbol": symbol,
            "source": source,
            "bars": len(rows),
            "latest": rows[-1]["trading_date"] if rows else None,
        }

    def _rebuild_snapshot_history(self) -> dict:
        events = self.store.list_events()
        if not events:
            return {"snapshots": 0, "official": 0}
        all_symbols = sorted({e.symbol.upper() for e in events if e.symbol})
        histories = self._histories(all_symbols, limit=10000)
        earliest_event = min(e.event_date for e in events)
        market_dates = sorted({
            row["trading_date"]
            for rows in histories.values()
            for row in rows
            if row.get("trading_date") and row["trading_date"] >= earliest_event
        })
        if not market_dates:
            return {"snapshots": 0, "official": 0}

        with self.store.connect() as db:
            db.execute("DELETE FROM snapshot_positions")
            db.execute("DELETE FROM portfolio_snapshots")

        price_maps = {
            s: {r["trading_date"]: r for r in rows if r.get("trading_date")}
            for s, rows in histories.items()
        }
        last_seen: dict[str, dict] = {}
        previous_date = None
        previous_nav = None
        twr_index = 1.0
        peak_twr = 1.0
        max_drawdown = 0.0
        n_official = 0

        for idx, snapshot_date in enumerate(market_dates):
            for symbol, by_date in price_maps.items():
                if snapshot_date in by_date:
                    last_seen[symbol] = by_date[snapshot_date]

            state = derive_state([e for e in events if e.event_date <= snapshot_date])
            active = sorted(state.positions)
            if active and any(s not in last_seen for s in active):
                continue
            prices = {s: last_seen[s] for s in active if s in last_seen}
            exact = all(prices.get(s, {}).get("trading_date") == snapshot_date for s in active)
            positions, equity = self._mark_to_market(state, prices)
            nav = equity + state.cash
            if nav <= 0 and not active:
                continue

            flow = external_flow([
                e for e in events
                if e.event_date <= snapshot_date and (previous_date is None or e.event_date > previous_date)
            ])
            daily_pnl = None
            daily_return = None
            if previous_nav is not None and previous_nav > 0:
                daily_pnl = nav - previous_nav - flow
                daily_return = daily_pnl / previous_nav
                twr_index *= 1.0 + daily_return
            peak_twr = max(peak_twr, twr_index)
            current_drawdown = twr_index / peak_twr - 1.0 if peak_twr > 0 else 0.0
            max_drawdown = min(max_drawdown, current_drawdown)

            is_latest = idx == len(market_dates) - 1
            risk = portfolio_risk(positions, self._histories(active, end=snapshot_date)) if is_latest and active else {}
            if risk:
                positions, equity = self._mark_to_market(state, prices, risk=risk)
                nav = equity + state.cash

            hhi = sum(float(p.get("weight") or 0) ** 2 for p in positions)
            max_weight = max((float(p.get("weight") or 0) for p in positions), default=0.0)
            quality = DataQuality.VALID.value if exact else DataQuality.STALE.value
            official = exact
            if official:
                n_official += 1
            snapshot = {
                "snapshot_date": snapshot_date,
                "cash": state.cash,
                "equity_value": equity,
                "nav": nav,
                "external_flow": flow,
                "daily_pnl": daily_pnl,
                "daily_return": daily_return,
                "twr_index": twr_index,
                "total_pnl": nav - state.net_external_contributions,
                "current_drawdown": current_drawdown,
                "max_drawdown": max_drawdown,
                "volatility_63": risk.get("volatility_63"),
                "volatility_252": risk.get("volatility_252"),
                "hhi": hhi,
                "max_position_weight": max_weight,
                "data_quality": quality,
                "official": official,
            }
            self.store.save_snapshot(snapshot, positions)
            previous_date = snapshot_date
            previous_nav = nav

        return {"snapshots": len(self.store.list_snapshots(limit=10000)), "official": n_official}

    def sync_daily(self) -> dict:
        state = self.current_state()
        current_symbols = sorted(state.positions)
        ledger_symbols = sorted({e.symbol.upper() for e in self.store.list_events() if e.symbol})
        today = datetime.now(VN_TZ).date()
        sync_rows = []
        errors = []
        for symbol in ledger_symbols:
            try:
                sync_rows.append(self._sync_symbol(symbol, today))
            except Exception as exc:
                errors.append({"symbol": symbol, "error": str(exc)})

        rebuilt = self._rebuild_snapshot_history()
        prices = self.store.latest_prices(current_symbols)
        quality, snapshot_date, stale_symbols = self._price_quality(current_symbols, prices)
        latest = self.store.latest_snapshot()
        return {
            "ok": not errors,
            "snapshot": latest,
            "history": rebuilt,
            "sync": sync_rows,
            "errors": errors,
            "stale_symbols": stale_symbols,
            "market_quality": quality,
            "snapshot_date": snapshot_date,
            "message": (
                f"Market data synced and {rebuilt['official']} official daily snapshots rebuilt."
                if not errors else
                "Sync completed with provider errors; stale/missing data is shown explicitly."
            ),
        }

    def performance(self) -> dict:
        all_snapshots = list(reversed(self.store.list_snapshots(limit=10000)))
        snapshots = [s for s in all_snapshots if s.get("official")]
        returns = period_returns(snapshots)
        state = self.current_state()
        symbols = sorted(state.positions)
        prices = self.store.latest_prices(symbols)
        positions, equity = self._mark_to_market(state, prices)
        nav = equity + state.cash
        accounting = self._live_accounting(state, positions, nav)

        latest_date = max((p.get("trading_date") for p in prices.values() if p.get("trading_date")), default=self.today_vn())
        cashflows = []
        for e in self.store.list_events():
            d = date.fromisoformat(e.event_date)
            if e.event_type == EventType.CASH_DEPOSIT:
                cashflows.append((d, -float(e.amount or 0)))
            elif e.event_type == EventType.CASH_WITHDRAW:
                cashflows.append((d, float(e.amount or 0)))
            elif e.event_type == EventType.POSITION_IMPORT:
                cashflows.append((d, -float(e.quantity or 0) * float(e.price or 0)))
        if nav > 0:
            cashflows.append((date.fromisoformat(latest_date), nav))
        irr = xirr(cashflows) if cashflows else None

        daily_values = [float(s["daily_return"]) for s in snapshots if s.get("daily_return") is not None]
        current_drawdown = float(snapshots[-1].get("current_drawdown") or 0.0) if snapshots else 0.0
        max_drawdown = min((float(s.get("current_drawdown") or 0.0) for s in snapshots), default=0.0)
        first_date = snapshots[0]["snapshot_date"] if snapshots else None
        last_date = snapshots[-1]["snapshot_date"] if snapshots else None
        annualized_twr = None
        if first_date and last_date and returns.get("since_inception") is not None:
            days = max(0, (date.fromisoformat(last_date) - date.fromisoformat(first_date)).days)
            factor = 1.0 + float(returns["since_inception"])
            if days >= 30 and factor > 0:
                annualized_twr = factor ** (365.25 / days) - 1.0

        return {
            "returns": returns,
            "annualized_twr": annualized_twr,
            "xirr": irr,
            **accounting,
            "cash": state.cash,
            "equity_value": equity,
            "nav": nav,
            "current_drawdown": current_drawdown,
            "max_drawdown": max_drawdown,
            "snapshot_count": len(all_snapshots),
            "official_snapshot_count": len(snapshots),
            "first_date": first_date,
            "latest_date": last_date,
            "best_day": max(daily_values) if daily_values else None,
            "worst_day": min(daily_values) if daily_values else None,
            "positive_day_ratio": (sum(1 for r in daily_values if r > 0) / len(daily_values)) if daily_values else None,
            "latest": snapshots[-1] if snapshots else None,
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
                suggestions.append({
                    "symbol": s,
                    "amount": amount,
                    "target_weight": targets[s],
                    "current_weight": current.get(s, 0.0) / nav if nav > 0 else 0.0,
                    "action": "ADD",
                })
        suggestions.sort(key=lambda x: x["amount"], reverse=True)
        return {
            "available_cash": max(0.0, state.cash),
            "deployable_cash": deployable,
            "policy": policy,
            "suggestions": suggestions,
            "disclaimer": "Information only. No BUY event is created automatically.",
        }
