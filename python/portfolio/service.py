from __future__ import annotations

from dataclasses import asdict
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

from .accounting import AccountingError, apply_event, derive_state, external_flow, state_as_dict
from .analytics import period_returns, xirr
from .domain import DataQuality, EventType, LedgerEvent
from .market_data import AutoMarketData, frame_to_price_rows
from .risk import portfolio_risk
from .storage import PortfolioStore
from .validation import normalize_event_payload, validate_cash_reserve, validate_reference_weights

VN_TZ = ZoneInfo("Asia/Ho_Chi_Minh")


class PortfolioService:
    """Buy & Hold portfolio application service.

    Market data, risk calculations and recommendation information are read-only
    with respect to holdings. Only explicit, validated ledger events change
    shares or cash.
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
        clean = normalize_event_payload(payload, today=self.today_vn())
        event_type = clean["event_type"]
        event = LedgerEvent(
            id=None,
            event_type=event_type,
            event_date=clean["event_date"],
            symbol=clean["symbol"],
            quantity=clean["quantity"],
            price=clean["price"],
            fee=clean["fee"],
            tax=clean["tax"],
            amount=clean["amount"],
            ratio=clean["ratio"],
            note=clean["note"],
            created_by=str(payload.get("created_by") or created_by or "local")[:100],
            metadata=clean["metadata"],
        )
        state = self.current_state()
        apply_event(state, event)
        if event_type in {EventType.BUY, EventType.CASH_WITHDRAW, EventType.FEE} and state.cash < -1e-6:
            raise AccountingError("Event would make cash negative. Record/import the funding first.")
        eid = self.store.append_event(event)
        return {"ok": True, "event_id": eid, "event": self._serialize_event(event)}

    def set_reference_weights(self, weights: dict[str, float]) -> dict:
        holdings = set(self.current_state().positions)
        normalized = validate_reference_weights(weights, holdings=holdings)
        self.store.set_reference_weights(normalized)
        return {"ok": True, "reference_weights": normalized}

    def set_cash_reserve(self, amount) -> dict:
        reserve = validate_cash_reserve(amount)
        self.store.set_meta("cash_reserve_vnd", str(reserve))
        return {"ok": True, "cash_reserve": reserve}

    def preferences(self) -> dict:
        raw_reserve = self.store.get_meta("cash_reserve_vnd")
        return {
            "cash_reserve_configured": raw_reserve is not None,
            "cash_reserve": float(raw_reserve) if raw_reserve is not None else None,
            "reference_weights": self.store.get_reference_weights(),
        }

    @staticmethod
    def _position_status(weight: float, reference: float | None) -> str:
        if reference is None or reference <= 0:
            return "MONITOR"
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
            rows.append({
                "symbol": symbol,
                "shares": position.shares,
                "average_cost": position.average_cost,
                "price": price if quote else None,
                "price_date": quote.get("trading_date") if quote else None,
                "price_source": quote.get("source") if quote else None,
                "cost_value": cost_value,
                "market_value": value,
                "unrealized_pnl": value - cost_value if quote else None,
                "unrealized_return": (value / cost_value - 1.0 if quote and cost_value > 0 else None),
            })
        nav = equity + state.cash
        refs = self.store.get_reference_weights()
        risk_contrib = (risk or {}).get("risk_contributions") or {}
        erc_ref = (risk or {}).get("erc_reference_weights") or {}
        for row in rows:
            row["weight"] = row["market_value"] / nav if nav > 0 else 0.0
            row["equity_weight"] = row["market_value"] / equity if equity > 0 else 0.0
            row["reference_weight"] = refs.get(row["symbol"])
            row["risk_contribution"] = risk_contrib.get(row["symbol"])
            row["erc_reference_weight"] = erc_ref.get(row["symbol"])
            row["status"] = self._position_status(row["weight"], refs.get(row["symbol"]))
        rows.sort(key=lambda p: p["market_value"], reverse=True)
        return rows, equity

    def _histories(self, symbols: list[str], end: str | None = None, limit: int = 10000) -> dict[str, list[dict]]:
        histories = self.store.price_histories(symbols, limit=limit, end=end) if symbols else {}
        if not symbols:
            return histories
        try:
            placeholders = ",".join("?" for _ in symbols)
            sql = f"""
                SELECT symbol, action_type, ex_date, cash_per_share, stock_ratio
                FROM corporate_actions
                WHERE verification_status = 'VERIFIED'
                  AND ex_date IS NOT NULL
                  AND symbol IN ({placeholders})
            """
            args: list[object] = [symbol.upper() for symbol in symbols]
            if end:
                sql += " AND ex_date <= ?"
                args.append(end)
            with self.store.connect() as db:
                actions = db.execute(sql, args).fetchall()
        except Exception:
            actions = []

        adjustments: dict[tuple[str, str], dict] = {}
        for action in actions:
            key = (str(action["symbol"]).upper(), str(action["ex_date"]))
            item = adjustments.setdefault(key, {"cash_distribution": 0.0, "share_factor": 1.0, "sources": []})
            action_type = str(action["action_type"] or "").upper()
            if action_type == "CASH_DIVIDEND" and action["cash_per_share"] is not None:
                item["cash_distribution"] += float(action["cash_per_share"])
                item["sources"].append("VERIFIED_CASH_DIVIDEND")
            elif action_type == "STOCK_DIVIDEND" and action["stock_ratio"] is not None:
                item["share_factor"] *= 1.0 + float(action["stock_ratio"])
                item["sources"].append("VERIFIED_STOCK_DIVIDEND")

        for symbol, rows in histories.items():
            for row in rows:
                adjustment = adjustments.get((symbol.upper(), str(row.get("trading_date") or "")))
                if adjustment and adjustment["sources"]:
                    row["analytics_cash_distribution"] = adjustment["cash_distribution"]
                    row["analytics_share_factor"] = adjustment["share_factor"]
                    row["analytics_adjustment_sources"] = adjustment["sources"]
        # A user-recorded SPLIT is itself an explicit trusted ledger event. It
        # changes shares in accounting and removes the mechanical price jump
        # from analytics on the first stored market date at/after the event.
        for event in self.store.list_events():
            if event.event_type != EventType.SPLIT or not event.symbol or event.symbol.upper() not in histories:
                continue
            effective_row = next((
                row for row in histories[event.symbol.upper()]
                if str(row.get("trading_date") or "") >= event.event_date
            ), None)
            if effective_row is None:
                continue
            effective_row["analytics_share_factor"] = float(effective_row.get("analytics_share_factor") or 1) * float(event.ratio)
            sources = list(effective_row.get("analytics_adjustment_sources") or [])
            sources.append("EXPLICIT_SPLIT_LEDGER")
            effective_row["analytics_adjustment_sources"] = sources
        return histories

    @staticmethod
    def _live_accounting(state, positions: list[dict], nav: float) -> dict:
        cost_value = sum(float(p.get("cost_value") or 0) for p in positions)
        valuation_complete = all(p.get("price") is not None for p in positions)
        unrealized = (
            sum(float(p.get("unrealized_pnl") or 0) for p in positions)
            if valuation_complete
            else None
        )
        contributions = float(state.net_external_contributions)
        total_pnl = float(nav) - contributions if valuation_complete else None
        accounting_return = (
            total_pnl / contributions
            if total_pnl is not None and contributions > 0
            else None
        )
        return {
            "cost_value": cost_value,
            "unrealized_pnl": unrealized,
            "realized_pnl": float(state.realized_pnl),
            "dividend_income": float(state.dividend_income),
            "fees_and_taxes": float(state.fees_and_taxes),
            "net_external_contributions": contributions,
            "total_pnl": total_pnl,
            "accounting_return": accounting_return,
            "total_return": accounting_return,
        }

    def risk(self, as_of: str | None = None) -> dict:
        state = self.current_state()
        symbols = sorted(state.positions)
        prices = self.store.latest_prices(symbols, on_or_before=as_of)
        base_rows, _ = self._mark_to_market(state, prices)

        valuation_signals = {}
        try:
            from .screener import compute_all_screener_scores
            scored = compute_all_screener_scores()
            valuation_signals = {item["symbol"].upper(): item for item in scored if item.get("symbol")}
        except Exception:
            valuation_signals = {}

        result = portfolio_risk(base_rows, self._histories(symbols, end=as_of), valuation_signals=valuation_signals)
        return {
            **result,
            "as_of": as_of or max((p.get("trading_date") for p in prices.values()), default=None),
            "policy": "INFORMATION_ONLY",
            "methodology": {
                "return_type": "log_return",
                "annualization": 252,
                "covariance": "pairwise_40_observations_with_10pct_diagonal_shrinkage",
                "corporate_actions": "verified cash/stock dividends are total-return adjusted on ex-date; unverified actions leave raw returns unchanged",
                "var": "historical_5pct_quantile",
                "concentration_basis": "equity_normalized",
                "erc": "diagnostic_reference_only",
                "permanent_loss_model": "buffett_munger_deterministic_business_risk",
            },
        }

    def _health(self, risk: dict, performance: dict, portfolio: dict, market_status: str) -> dict:
        flags = []
        if market_status != DataQuality.VALID.value:
            flags.append({"level": "WARNING", "code": "MARKET_DATA", "message": "Market data is not aligned for all current holdings."})

        effective_ratio = risk.get("effective_position_ratio")
        if effective_ratio is not None and float(effective_ratio) < 0.75:
            flags.append({
                "level": "WARNING", "code": "CAPITAL_CONCENTRATION",
                "message": "Effective equity positions are below 75% of the actual holding count.",
            })

        equal_risk = risk.get("equal_risk_contribution")
        largest_rc = risk.get("largest_risk_contribution")
        risk_limit = max(0.45, 1.5 * float(equal_risk)) if equal_risk else 0.45
        if largest_rc is not None and float(largest_rc) > risk_limit:
            flags.append({
                "level": "WARNING", "code": "RISK_CONCENTRATION",
                "message": f"{risk.get('largest_risk_symbol') or 'One holding'} contributes {float(largest_rc) * 100:.1f}% of portfolio risk.",
            })

        if risk.get("average_correlation") is not None and float(risk["average_correlation"]) >= 0.60:
            flags.append({"level": "WARNING", "code": "CORRELATION", "message": "Holdings have high average correlation."})
        if performance.get("current_drawdown") is not None and float(performance["current_drawdown"]) <= -0.20:
            flags.append({"level": "WARNING", "code": "DRAWDOWN", "message": "Current tracked drawdown is at least 20%."})
        if risk.get("volatility_252") is not None and float(risk["volatility_252"]) >= 0.35:
            flags.append({"level": "WARNING", "code": "VOLATILITY", "message": "252D annualized volatility is high."})
        coverage = float((risk.get("quality") or {}).get("coverage_weight") or 0)
        if portfolio.get("positions") and coverage < 0.90:
            flags.append({"level": "WARNING", "code": "RISK_COVERAGE", "message": "Risk history coverage is below 90%."})
        if performance.get("history_status") in {"NO_HISTORY", "STARTING", "SHORT_HISTORY"}:
            flags.append({
                "level": "INFO", "code": "PERFORMANCE_HISTORY",
                "message": "Performance history is not yet long enough for strong drawdown/performance conclusions.",
            })

        warnings = [f for f in flags if f["level"] == "WARNING"]
        return {
            "status": "ATTENTION" if warnings else "HEALTHY",
            "flags": flags,
            "snapshot_count": performance.get("snapshot_count", 0),
            "official_snapshot_count": performance.get("official_snapshot_count", 0),
            "performance_history_status": performance.get("history_status"),
            "current_drawdown": performance.get("current_drawdown"),
            "max_drawdown": performance.get("max_drawdown"),
            "accounting_return": performance.get("accounting_return"),
            "total_return": performance.get("accounting_return"),
            "cash_weight": (float(portfolio.get("cash") or 0) / float(portfolio.get("nav") or 1)) if float(portfolio.get("nav") or 0) > 0 else 0.0,
            "effective_positions": risk.get("effective_positions"),
            "effective_position_ratio": risk.get("effective_position_ratio"),
            "equity_hhi": risk.get("equity_hhi"),
            "max_equity_weight": risk.get("max_equity_weight"),
            "average_correlation": risk.get("average_correlation"),
            "max_correlation": risk.get("max_correlation"),
            "diversification_ratio": risk.get("diversification_ratio"),
            "largest_risk_symbol": risk.get("largest_risk_symbol"),
            "largest_risk_contribution": largest_rc,
            "risk_concentration_ratio": risk.get("risk_concentration_ratio"),
            "risk_coverage": coverage,
            "daily_var_95": risk.get("daily_var_95"),
            "daily_cvar_95": risk.get("daily_cvar_95"),
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

    def _market_history_status(self, symbols: list[str]) -> dict:
        required_bars = 260
        rows = []
        for symbol in symbols:
            count = int(self.store.market_price_count(symbol) or 0)
            latest = self.store.latest_price(symbol)
            rows.append({
                "symbol": symbol,
                "bars": count,
                "required_bars": required_bars,
                "risk_ready": count >= required_bars,
                "latest": latest.get("trading_date") if latest else None,
                "source": latest.get("source") if latest else None,
            })
        ready = sum(1 for row in rows if row["risk_ready"])
        total = len(rows)
        return {
            "state": "NO_HOLDINGS" if total == 0 else ("READY" if ready == total else "BUILDING"),
            "required_bars": required_bars,
            "ready_symbols": ready,
            "total_symbols": total,
            "symbols": rows,
        }

    def _market_metadata(self, symbols: list[str], prices: dict[str, dict]) -> dict:
        status, market_date, stale_symbols = self._price_quality(symbols, prices)
        age = None
        if market_date:
            age = max(0, (date.fromisoformat(self.today_vn()) - date.fromisoformat(market_date)).days)
        return {
            "provider": self.market.health(),
            "latest_prices": prices,
            "status": status,
            "market_date": market_date,
            "aligned": status == DataQuality.VALID.value,
            "stale_or_missing_symbols": stale_symbols,
            "calendar_age_days": age,
            "history": self._market_history_status(symbols),
            "freshness_semantics": "VALID means all current holdings are aligned on the same latest stored trading date; calendar age alone does not imply exchange-session staleness.",
        }

    @staticmethod
    def _data_lineage() -> dict:
        return {
            "valuation": {
                "series": "stored provider close",
                "unit": "full VND per share",
                "purpose": "current market value and NAV",
            },
            "analytics": {
                "series": "stored D1 provider close",
                "corporate_action_adjusted": "verified cash and stock dividends are applied on ex-date; raw close is retained",
                "status": "EXPLICIT_VERIFIED_ACTIONS_ONLY",
                "purpose": "return/covariance/volatility diagnostics",
            },
            "warning": "Unverified corporate actions never alter analytics silently. Verify them in Operations before QPort applies an ex-date total-return adjustment.",
        }

    def dashboard(self) -> dict:
        state = self.current_state()
        symbols = sorted(state.positions)
        prices = self.store.latest_prices(symbols)
        base_positions, _ = self._mark_to_market(state, prices)
        risk = self.risk()
        positions, equity = self._mark_to_market(state, prices, risk=risk)
        nav = equity + state.cash
        accounting = self._live_accounting(state, positions, nav)
        latest_snapshot = self.store.latest_snapshot()
        official_snapshot = self.store.latest_snapshot(official_only=True)
        refs = self.store.get_reference_weights()
        perf = self.performance()
        market = self._market_metadata(symbols, prices)
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
            "preferences": self.preferences(),
            "latest_snapshot": latest_snapshot,
            "latest_official_snapshot": official_snapshot,
            "performance_summary": perf,
            "risk": risk,
            "health": self._health(risk, perf, portfolio, market["status"]),
            "market_data": market,
            "data_lineage": self._data_lineage(),
            "contribution_suggestions": self.contribution_suggestions(),
            "invariants": [
                "price movement never changes shares",
                "risk information never changes shares",
                "time/year-end never changes shares",
                "only explicit ledger events change holdings or cash",
            ],
        }

    def _sync_symbol(self, symbol: str, today: date) -> dict:
        latest = self.store.latest_price(symbol)
        count_before = int(self.store.market_price_count(symbol) or 0)
        symbol_events = [e for e in self.store.list_events() if e.symbol and e.symbol.upper() == symbol.upper()]
        earliest_event = min((date.fromisoformat(e.event_date) for e in symbol_events), default=None)
        if latest and count_before >= 260:
            start_date = date.fromisoformat(latest["trading_date"]) - timedelta(days=10)
        else:
            risk_lookback_start = today - timedelta(days=550)
            event_start = (earliest_event - timedelta(days=10)) if earliest_event else risk_lookback_start
            start_date = min(risk_lookback_start, event_start)
        df, source = self.market.daily_history_with_source(symbol, start_date.isoformat(), today.isoformat())
        rows = frame_to_price_rows(symbol, df, source=source)
        self.store.upsert_market_prices(rows)
        count_after = int(self.store.market_price_count(symbol) or 0)
        return {
            "symbol": symbol,
            "source": source,
            "bars": len(rows),
            "stored_bars": count_after,
            "required_bars": 260,
            "latest": rows[-1]["trading_date"] if rows else (latest.get("trading_date") if latest else None),
            "history_start": rows[0]["trading_date"] if rows else None,
            "risk_ready": count_after >= 260,
        }

    def _rebuild_snapshot_history(self) -> dict:
        events = self.store.list_events()
        if not events:
            return {"snapshots": 0, "official": 0, "tracking_start": None}
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
            return {"snapshots": 0, "official": 0, "tracking_start": None}

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

            equity_weights = [float(p.get("market_value") or 0) / equity for p in positions] if equity > 0 else []
            hhi = sum(w * w for w in equity_weights)
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

        snapshots = self.store.list_snapshots(limit=10000)
        official_rows = [s for s in snapshots if s.get("official")]
        return {
            "snapshots": len(snapshots),
            "official": n_official,
            "tracking_start": official_rows[-1]["snapshot_date"] if official_rows else None,
        }

    def sync_daily(self) -> dict:
        from concurrent.futures import ThreadPoolExecutor, as_completed

        state = self.current_state()
        current_symbols = sorted(state.positions)
        ledger_symbols = sorted({e.symbol.upper() for e in self.store.list_events() if e.symbol})
        today = datetime.now(VN_TZ).date()
        sync_rows = []
        errors = []

        all_to_sync = list(ledger_symbols)
        if "VNINDEX" not in all_to_sync:
            all_to_sync.append("VNINDEX")

        def _do_sync(sym: str):
            return sym, self._sync_symbol(sym, today)

        benchmark_sync = None
        benchmark_error = None

        with ThreadPoolExecutor(max_workers=min(8, max(1, len(all_to_sync)))) as executor:
            futures = {executor.submit(_do_sync, sym): sym for sym in all_to_sync}
            for fut in as_completed(futures):
                sym = futures[fut]
                try:
                    _, res = fut.result()
                    if sym == "VNINDEX":
                        benchmark_sync = res
                    else:
                        sync_rows.append(res)
                except Exception as exc:
                    if sym == "VNINDEX":
                        benchmark_error = str(exc)
                    else:
                        errors.append({"symbol": sym, "error": str(exc)})

        rebuilt = self._rebuild_snapshot_history()
        prices = self.store.latest_prices(current_symbols)
        quality, snapshot_date, stale_symbols = self._price_quality(current_symbols, prices)
        latest = self.store.latest_snapshot()
        history_status = self._market_history_status(current_symbols)
        return {
            "ok": not errors,
            "snapshot": latest,
            "history": rebuilt,
            "history_status": history_status,
            "sync": sync_rows,
            "errors": errors,
            "benchmark": benchmark_sync,
            "benchmark_error": benchmark_error,
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

        n_official = len(snapshots)
        if n_official == 0:
            history_status = "NO_HISTORY"
        elif n_official == 1:
            history_status = "STARTING"
        elif n_official < 20:
            history_status = "SHORT_HISTORY"
        else:
            history_status = "SUFFICIENT"

        latest_market_date = max((p.get("trading_date") for p in prices.values() if p.get("trading_date")), default=None)
        events = self.store.list_events()
        has_opening_import = any(e.event_type == EventType.POSITION_IMPORT for e in events)
        cashflow_quality = "OPENING_BALANCE_ONLY" if has_opening_import else "COMPLETE"
        irr = None
        irr_status = "UNAVAILABLE_OPENING_BALANCE" if has_opening_import else "INSUFFICIENT_CASHFLOWS"
        # P0 audit (2026-08-29): NO_HISTORY means there are no official NAV
        # snapshots, so a terminal NAV cannot be anchored to a real portfolio
        # date. Computing XIRR against a synthetic terminal cashflow produced a
        # spurious -99.97% artifact; the correct contract is xirr = null.
        if history_status == "NO_HISTORY" and not has_opening_import:
            irr = None
            irr_status = "NO_HISTORY"
        elif not has_opening_import:
            cashflows = []
            for e in events:
                d = date.fromisoformat(e.event_date)
                if e.event_type == EventType.CASH_DEPOSIT:
                    cashflows.append((d, -float(e.amount or 0)))
                elif e.event_type == EventType.CASH_WITHDRAW:
                    cashflows.append((d, float(e.amount or 0)))
            terminal_date = snapshots[-1]["snapshot_date"] if snapshots else None
            if nav > 0 and terminal_date:
                cashflows.append((date.fromisoformat(terminal_date), nav))
            if len(cashflows) >= 2:
                irr = xirr(cashflows)
                irr_status = "AVAILABLE" if irr is not None else "INSUFFICIENT_CASHFLOWS"

        daily_values = [float(s["daily_return"]) for s in snapshots if s.get("daily_return") is not None]
        current_drawdown = float(snapshots[-1].get("current_drawdown") or 0.0) if n_official >= 2 else None
        max_drawdown = min((float(s.get("current_drawdown") or 0.0) for s in snapshots), default=0.0) if n_official >= 2 else None
        first_date = snapshots[0]["snapshot_date"] if snapshots else None
        last_date = snapshots[-1]["snapshot_date"] if snapshots else None
        annualized_twr = None
        if first_date and last_date and returns.get("since_inception") is not None:
            days = max(0, (date.fromisoformat(last_date) - date.fromisoformat(first_date)).days)
            factor = 1.0 + float(returns["since_inception"])
            if days >= 30 and factor > 0:
                annualized_twr = factor ** (365.25 / days) - 1.0

        benchmark_rows = self.store.price_history("VNINDEX", limit=10000, end=last_date)
        if first_date:
            benchmark_rows = [row for row in benchmark_rows if row.get("trading_date") and row["trading_date"] >= first_date]
        benchmark_base = float(benchmark_rows[0]["close"]) if benchmark_rows and float(benchmark_rows[0].get("close") or 0) > 0 else None
        benchmark_series = [
            {
                "date": row["trading_date"],
                "index": float(row["close"]) / benchmark_base,
                "close": float(row["close"]),
            }
            for row in benchmark_rows
            if benchmark_base and row.get("close") is not None
        ]

        return {
            "returns": returns,
            "annualized_twr": annualized_twr,
            "xirr": irr,
            "xirr_status": irr_status,
            "cashflow_history_quality": cashflow_quality,
            "history_status": history_status,
            **accounting,
            "cash": state.cash,
            "equity_value": equity,
            "nav": nav,
            "current_drawdown": current_drawdown,
            "max_drawdown": max_drawdown,
            "snapshot_count": len(all_snapshots),
            "official_snapshot_count": n_official,
            "first_date": first_date,
            "latest_date": last_date,
            "best_day": max(daily_values) if daily_values else None,
            "worst_day": min(daily_values) if daily_values else None,
            "positive_day_ratio": (sum(1 for r in daily_values if r > 0) / len(daily_values)) if daily_values else None,
            "benchmark": {
                "symbol": "VNINDEX",
                "status": "AVAILABLE" if len(benchmark_series) >= 2 else "UNAVAILABLE",
                "series": benchmark_series,
                "method": "provider_raw_close_normalized_to_first_overlapping_observation",
                "warning": None if len(benchmark_series) >= 2 else "VN-Index history is not stored yet; run a normal market sync to fetch it.",
            },
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
        refs = self.store.get_reference_weights()
        prefs = self.preferences()
        available_cash = max(0.0, state.cash)

        if not symbols or available_cash <= 0:
            return {
                "available_cash": available_cash,
                "strategic_cash_reserve": prefs["cash_reserve"],
                "deployable_cash": 0.0 if prefs["cash_reserve_configured"] else None,
                "suggestions": [],
                "policy": "NO_CASH_OR_POSITIONS",
            }
        if not refs or set(refs) != set(symbols):
            return {
                "available_cash": available_cash,
                "strategic_cash_reserve": prefs["cash_reserve"],
                "deployable_cash": None,
                "suggestions": [],
                "policy": "NO_ALLOCATION_POLICY",
                "reason": "Configure explicit strategic reference weights before QPort labels cash as deployable.",
            }
        if not prefs["cash_reserve_configured"]:
            return {
                "available_cash": available_cash,
                "strategic_cash_reserve": None,
                "deployable_cash": None,
                "suggestions": [],
                "policy": "NO_CASH_RESERVE_POLICY",
                "reason": "Configure a strategic cash reserve (zero is allowed explicitly) before QPort labels cash as deployable.",
            }

        reserve = float(prefs["cash_reserve"] or 0)
        cash_above_reserve = max(0.0, available_cash - reserve)
        prices = self.store.latest_prices(symbols)
        positions, equity = self._mark_to_market(state, prices)
        nav = equity + state.cash
        current = {p["symbol"]: p["market_value"] for p in positions}
        deficits = {s: max(0.0, refs[s] * nav - current.get(s, 0.0)) for s in symbols}
        total_deficit = sum(deficits.values())
        deployable = min(cash_above_reserve, total_deficit)
        suggestions = []
        if total_deficit > 0 and deployable > 0:
            for s in symbols:
                amount = deployable * deficits[s] / total_deficit
                if amount <= 0:
                    continue
                suggestions.append({
                    "symbol": s,
                    "amount": amount,
                    "target_weight": refs[s],
                    "current_weight": current.get(s, 0.0) / nav if nav > 0 else 0.0,
                    "action": "ADD_CANDIDATE",
                })
        suggestions.sort(key=lambda x: x["amount"], reverse=True)
        return {
            "available_cash": available_cash,
            "strategic_cash_reserve": reserve,
            "cash_above_reserve": cash_above_reserve,
            "deployable_cash": deployable,
            "policy": "EXPLICIT_REFERENCE_WEIGHT_DEFICITS",
            "suggestions": suggestions,
            "disclaimer": "Information only. Portfolio/risk/quality gates are still required before an ADD candidate becomes a recommendation; no BUY event is created automatically.",
        }
