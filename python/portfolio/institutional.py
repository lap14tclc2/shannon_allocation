from __future__ import annotations

import json
from collections import defaultdict
from datetime import date, datetime, timedelta, timezone

from .accounting import apply_event, derive_state
from .corporate_actions import (
    CorporateAction,
    VnstockCorporateActionProvider,
    action_as_dict,
    default_window,
)
from .domain import EventType, LedgerEvent, PortfolioState


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _business_days_after(day: str, n: int = 2) -> str:
    current = date.fromisoformat(day)
    moved = 0
    while moved < n:
        current += timedelta(days=1)
        if current.weekday() < 5:
            moved += 1
    return current.isoformat()


def _trade_cash_effect(event: LedgerEvent) -> float:
    gross = float(event.quantity or 0) * float(event.price or 0)
    costs = float(event.fee or 0) + float(event.tax or 0)
    if event.event_type == EventType.BUY:
        return -(gross + costs)
    if event.event_type == EventType.SELL:
        return gross - costs
    return 0.0


class InstitutionalBook:
    """Institutional-lite controls layered on the immutable QPort event store.

    This is deliberately not a full fund administrator/GL. It adds the controls
    that are valuable for a single-portfolio Buy & Hold IBOR: security master,
    tax-lot visibility, settlement-aware cash, broker reconciliation, corporate
    actions, NAV locking/restatement and exception management.
    """

    def __init__(self, store, *, today_fn=None, corporate_action_provider=None) -> None:
        self.store = store
        self.today_fn = today_fn or (lambda: date.today().isoformat())
        self.ca_provider = corporate_action_provider or VnstockCorporateActionProvider()
        self.ensure_schema()

    def ensure_schema(self) -> None:
        with self.store.connect() as db:
            db.executescript(
                """
                CREATE TABLE IF NOT EXISTS security_master (
                    security_id TEXT PRIMARY KEY,
                    symbol TEXT NOT NULL UNIQUE,
                    exchange TEXT NOT NULL DEFAULT 'UNKNOWN',
                    asset_type TEXT NOT NULL DEFAULT 'EQUITY',
                    currency TEXT NOT NULL DEFAULT 'VND',
                    isin TEXT,
                    lot_size REAL,
                    active INTEGER NOT NULL DEFAULT 1,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS settlement_overrides (
                    event_id INTEGER PRIMARY KEY,
                    status TEXT NOT NULL,
                    note TEXT NOT NULL DEFAULT '',
                    confirmed_at TEXT,
                    updated_at TEXT NOT NULL,
                    FOREIGN KEY(event_id) REFERENCES ledger_events(id)
                );

                CREATE TABLE IF NOT EXISTS reconciliation_runs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    account_id TEXT NOT NULL DEFAULT 'PRIMARY',
                    as_of_date TEXT NOT NULL,
                    broker_cash REAL NOT NULL,
                    qport_cash REAL NOT NULL,
                    cash_difference REAL NOT NULL,
                    status TEXT NOT NULL,
                    source TEXT NOT NULL DEFAULT 'MANUAL',
                    note TEXT NOT NULL DEFAULT '',
                    created_by TEXT NOT NULL DEFAULT 'local',
                    created_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS reconciliation_items (
                    run_id INTEGER NOT NULL,
                    symbol TEXT NOT NULL,
                    qport_quantity REAL NOT NULL,
                    broker_quantity REAL NOT NULL,
                    difference REAL NOT NULL,
                    status TEXT NOT NULL,
                    PRIMARY KEY(run_id, symbol),
                    FOREIGN KEY(run_id) REFERENCES reconciliation_runs(id) ON DELETE CASCADE
                );

                CREATE TABLE IF NOT EXISTS corporate_actions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    external_key TEXT NOT NULL UNIQUE,
                    symbol TEXT NOT NULL,
                    action_type TEXT NOT NULL,
                    announcement_date TEXT,
                    ex_date TEXT,
                    record_date TEXT,
                    payment_date TEXT,
                    cash_per_share REAL,
                    stock_ratio REAL,
                    source TEXT NOT NULL,
                    source_url TEXT,
                    confidence TEXT NOT NULL DEFAULT 'PROVISIONAL',
                    verification_status TEXT NOT NULL DEFAULT 'UNVERIFIED',
                    raw_json TEXT NOT NULL DEFAULT '{}',
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );
                CREATE INDEX IF NOT EXISTS idx_corporate_actions_symbol_date
                    ON corporate_actions(symbol, record_date, payment_date);

                CREATE TABLE IF NOT EXISTS corporate_action_receipts (
                    action_id INTEGER PRIMARY KEY,
                    received_date TEXT NOT NULL,
                    actual_cash REAL NOT NULL DEFAULT 0,
                    actual_shares REAL NOT NULL DEFAULT 0,
                    note TEXT NOT NULL DEFAULT '',
                    created_by TEXT NOT NULL DEFAULT 'local',
                    created_at TEXT NOT NULL,
                    FOREIGN KEY(action_id) REFERENCES corporate_actions(id)
                );

                CREATE TABLE IF NOT EXISTS nav_controls (
                    snapshot_date TEXT PRIMARY KEY,
                    status TEXT NOT NULL,
                    reason TEXT NOT NULL DEFAULT '',
                    locked_at TEXT,
                    updated_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS nav_restatements (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    affected_from_date TEXT NOT NULL,
                    reason TEXT NOT NULL,
                    correction_event_id INTEGER,
                    status TEXT NOT NULL DEFAULT 'OPEN',
                    created_at TEXT NOT NULL,
                    resolved_at TEXT
                );
                """
            )

    # ------------------------------------------------------------------
    # Security master
    # ------------------------------------------------------------------
    def ensure_securities(self, symbols: list[str]) -> None:
        now = _now()
        rows = []
        for symbol in sorted({str(s).upper() for s in symbols if s}):
            rows.append((f"VN-EQ-{symbol}", symbol, now, now))
        if not rows:
            return
        with self.store.connect() as db:
            db.executemany(
                """
                INSERT INTO security_master(security_id, symbol, created_at, updated_at)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(symbol) DO NOTHING
                """,
                rows,
            )

    def securities(self) -> list[dict]:
        with self.store.connect() as db:
            rows = db.execute("SELECT * FROM security_master ORDER BY symbol").fetchall()
        return [{**dict(r), "active": bool(r["active"])} for r in rows]

    def update_security(self, symbol: str, payload: dict) -> dict:
        symbol = str(symbol).upper().strip()
        self.ensure_securities([symbol])
        exchange = str(payload.get("exchange") or "UNKNOWN").upper().strip()[:20]
        currency = str(payload.get("currency") or "VND").upper().strip()[:10]
        asset_type = str(payload.get("asset_type") or "EQUITY").upper().strip()[:30]
        isin = str(payload.get("isin") or "").upper().strip()[:32] or None
        lot_size = payload.get("lot_size")
        if lot_size not in (None, ""):
            lot_size = float(lot_size)
            if lot_size <= 0:
                raise ValueError("lot_size must be greater than 0")
        with self.store.connect() as db:
            db.execute(
                """
                UPDATE security_master
                SET exchange=?, currency=?, asset_type=?, isin=?, lot_size=?, updated_at=?
                WHERE symbol=?
                """,
                (exchange, currency, asset_type, isin, lot_size, _now(), symbol),
            )
        return next((s for s in self.securities() if s["symbol"] == symbol), {})

    # ------------------------------------------------------------------
    # Tax-lot / IBOR views
    # ------------------------------------------------------------------
    @staticmethod
    def tax_lots(state: PortfolioState) -> list[dict]:
        out = []
        for symbol, position in sorted(state.positions.items()):
            for lot in sorted(position.lots, key=lambda x: (x.acquisition_date, x.lot_id)):
                out.append({
                    "lot_id": lot.lot_id,
                    "symbol": symbol,
                    "acquisition_date": lot.acquisition_date,
                    "source_event_id": lot.source_event_id,
                    "original_quantity": lot.original_quantity,
                    "remaining_quantity": lot.remaining_quantity,
                    "unit_cost": lot.unit_cost,
                    "cost_basis": lot.cost_basis,
                    "account_id": lot.account_id,
                    "cost_method": "FIFO",
                })
        return out

    def settlement_view(self, events: list[LedgerEvent], projected_cash: float, reserve: float | None = None) -> dict:
        today = self.today_fn()
        with self.store.connect() as db:
            overrides = {
                int(r["event_id"]): dict(r)
                for r in db.execute("SELECT * FROM settlement_overrides").fetchall()
            }
        unsettled_net = 0.0
        receivable = 0.0
        payable = 0.0
        trades = []
        for event in events:
            if event.event_type not in {EventType.BUY, EventType.SELL}:
                continue
            trade_date = event.trade_date
            settlement_date = event.settlement_date or _business_days_after(trade_date, 2)
            override = overrides.get(int(event.id or 0))
            confirmed = bool(override and override.get("status") == "SETTLED")
            effect = _trade_cash_effect(event)
            if confirmed:
                status = "SETTLED"
            elif settlement_date > today:
                status = "EXPECTED"
            else:
                status = "DUE_UNCONFIRMED"
            if not confirmed:
                unsettled_net += effect
                if effect < 0:
                    payable += -effect
                else:
                    receivable += effect
            trades.append({
                "event_id": event.id,
                "symbol": event.symbol,
                "side": event.event_type.value,
                "trade_date": trade_date,
                "settlement_date": settlement_date,
                "settlement_date_source": "EXPLICIT" if event.settlement_date else "ESTIMATED_T2_WEEKDAYS",
                "status": status,
                "cash_effect": effect,
                "account_id": event.account_id,
                "note": (override or {}).get("note") or "",
            })
        settled_cash = float(projected_cash) - unsettled_net
        reserve_value = float(reserve or 0) if reserve is not None else None
        available = None if reserve_value is None else max(0.0, settled_cash - payable - reserve_value)
        return {
            "settled_cash": settled_cash,
            "projected_cash": float(projected_cash),
            "unsettled_receivable": receivable,
            "unsettled_payable": payable,
            "strategic_reserve": reserve_value,
            "available_to_invest": available,
            "trades": sorted(trades, key=lambda x: (x["settlement_date"], x["event_id"] or 0), reverse=True),
            "policy": "TRADE_DATE_POSITIONS_WITH_SETTLEMENT_AWARE_CASH",
        }

    def confirm_settlement(self, event_id: int, note: str = "") -> dict:
        with self.store.connect() as db:
            row = db.execute("SELECT event_type FROM ledger_events WHERE id=?", (int(event_id),)).fetchone()
            if not row or row["event_type"] not in {"BUY", "SELL"}:
                raise ValueError("Only BUY/SELL transactions can be settled.")
            db.execute(
                """
                INSERT INTO settlement_overrides(event_id,status,note,confirmed_at,updated_at)
                VALUES (?, 'SETTLED', ?, ?, ?)
                ON CONFLICT(event_id) DO UPDATE SET
                    status='SETTLED', note=excluded.note,
                    confirmed_at=excluded.confirmed_at, updated_at=excluded.updated_at
                """,
                (int(event_id), str(note or "")[:500], _now(), _now()),
            )
        return {"ok": True, "event_id": int(event_id), "status": "SETTLED"}

    # ------------------------------------------------------------------
    # Reconciliation
    # ------------------------------------------------------------------
    def reconcile(self, state: PortfolioState, payload: dict, created_by: str = "local") -> dict:
        positions = payload.get("positions") or {}
        if not isinstance(positions, dict):
            raise ValueError("positions must be an object of {symbol: quantity}")
        broker_cash = float(payload.get("cash") or 0)
        account_id = str(payload.get("account_id") or "PRIMARY")[:50]
        as_of = str(payload.get("as_of_date") or self.today_fn())
        source = str(payload.get("source") or "MANUAL")[:50]
        note = str(payload.get("note") or "")[:500]
        tolerance_qty = float(payload.get("quantity_tolerance") or 1e-6)
        tolerance_cash = float(payload.get("cash_tolerance") or 1.0)
        qport_positions = {s: p.shares for s, p in state.positions.items()}
        symbols = sorted(set(qport_positions) | {str(s).upper() for s in positions})
        items = []
        mismatches = 0
        for symbol in symbols:
            q_qty = float(qport_positions.get(symbol, 0))
            b_qty = float(positions.get(symbol, positions.get(symbol.lower(), 0)) or 0)
            diff = b_qty - q_qty
            status = "MATCH" if abs(diff) <= tolerance_qty else "MISMATCH"
            mismatches += status == "MISMATCH"
            items.append({"symbol": symbol, "qport_quantity": q_qty, "broker_quantity": b_qty, "difference": diff, "status": status})
        cash_diff = broker_cash - float(state.cash)
        cash_match = abs(cash_diff) <= tolerance_cash
        status = "MATCH" if mismatches == 0 and cash_match else "MISMATCH"
        with self.store.connect() as db:
            cur = db.execute(
                """
                INSERT INTO reconciliation_runs(
                    account_id,as_of_date,broker_cash,qport_cash,cash_difference,status,
                    source,note,created_by,created_at
                ) VALUES (?,?,?,?,?,?,?,?,?,?)
                """,
                (account_id, as_of, broker_cash, float(state.cash), cash_diff, status, source, note, str(created_by)[:100], _now()),
            )
            run_id = int(cur.lastrowid)
            db.executemany(
                """
                INSERT INTO reconciliation_items(run_id,symbol,qport_quantity,broker_quantity,difference,status)
                VALUES (?,?,?,?,?,?)
                """,
                [(run_id, i["symbol"], i["qport_quantity"], i["broker_quantity"], i["difference"], i["status"]) for i in items],
            )
        return {"ok": True, "run_id": run_id, "status": status, "cash_difference": cash_diff, "items": items}

    def reconciliations(self, limit: int = 20) -> list[dict]:
        with self.store.connect() as db:
            runs = db.execute("SELECT * FROM reconciliation_runs ORDER BY id DESC LIMIT ?", (int(limit),)).fetchall()
            out = []
            for run in runs:
                row = dict(run)
                row["items"] = [dict(x) for x in db.execute("SELECT * FROM reconciliation_items WHERE run_id=? ORDER BY symbol", (run["id"],)).fetchall()]
                out.append(row)
        return out

    # ------------------------------------------------------------------
    # Corporate actions
    # ------------------------------------------------------------------
    def upsert_corporate_action(self, action: CorporateAction) -> None:
        payload = action_as_dict(action)
        now = _now()
        with self.store.connect() as db:
            db.execute(
                """
                INSERT INTO corporate_actions(
                    external_key,symbol,action_type,announcement_date,ex_date,record_date,payment_date,
                    cash_per_share,stock_ratio,source,source_url,confidence,verification_status,
                    raw_json,created_at,updated_at
                ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
                ON CONFLICT(external_key) DO UPDATE SET
                    symbol=excluded.symbol,action_type=excluded.action_type,
                    announcement_date=excluded.announcement_date,ex_date=excluded.ex_date,
                    record_date=excluded.record_date,payment_date=excluded.payment_date,
                    cash_per_share=excluded.cash_per_share,stock_ratio=excluded.stock_ratio,
                    source=excluded.source,source_url=COALESCE(excluded.source_url,corporate_actions.source_url),
                    raw_json=excluded.raw_json,updated_at=excluded.updated_at
                """,
                (
                    action.external_key, action.symbol, action.action_type, action.announcement_date,
                    action.ex_date, action.record_date, action.payment_date, action.cash_per_share,
                    action.stock_ratio, action.source, action.source_url, action.confidence,
                    action.verification_status, json.dumps(payload.get("raw") or {}, ensure_ascii=False, default=str),
                    now, now,
                ),
            )

    def sync_corporate_actions(self, symbols: list[str], start: str | None = None, end: str | None = None) -> dict:
        if not symbols:
            return {"ok": True, "discovered": 0, "provider": self.ca_provider.health()}
        if not start or not end:
            default_start, default_end = default_window()
            start = start or default_start
            end = end or default_end
        actions = self.ca_provider.events(symbols, start, end)
        for action in actions:
            self.upsert_corporate_action(action)
        return {"ok": True, "discovered": len(actions), "provider": self.ca_provider.health(), "start": start, "end": end}

    def verify_corporate_action(self, action_id: int, source_url: str, verified_by: str = "local") -> dict:
        if not str(source_url or "").startswith(("http://", "https://")):
            raise ValueError("A source URL is required for verification.")
        with self.store.connect() as db:
            db.execute(
                """
                UPDATE corporate_actions
                SET verification_status='VERIFIED', confidence='VERIFIED', source_url=?, updated_at=?
                WHERE id=?
                """,
                (str(source_url), _now(), int(action_id)),
            )
        return {"ok": True, "action_id": int(action_id), "verification_status": "VERIFIED", "verified_by": verified_by}

    def record_corporate_action_receipt(self, action_id: int, payload: dict, created_by: str = "local") -> dict:
        received_date = str(payload.get("received_date") or self.today_fn())
        actual_cash = float(payload.get("actual_cash") or 0)
        actual_shares = float(payload.get("actual_shares") or 0)
        if actual_cash < 0 or actual_shares < 0:
            raise ValueError("Corporate-action receipt values cannot be negative.")
        with self.store.connect() as db:
            exists = db.execute("SELECT id FROM corporate_actions WHERE id=?", (int(action_id),)).fetchone()
            if not exists:
                raise ValueError("Corporate action not found.")
            db.execute(
                """
                INSERT INTO corporate_action_receipts(action_id,received_date,actual_cash,actual_shares,note,created_by,created_at)
                VALUES (?,?,?,?,?,?,?)
                ON CONFLICT(action_id) DO UPDATE SET
                    received_date=excluded.received_date,actual_cash=excluded.actual_cash,
                    actual_shares=excluded.actual_shares,note=excluded.note,
                    created_by=excluded.created_by,created_at=excluded.created_at
                """,
                (int(action_id), received_date, actual_cash, actual_shares, str(payload.get("note") or "")[:500], str(created_by)[:100], _now()),
            )
        return {"ok": True, "action_id": int(action_id)}

    def corporate_actions(self, events: list[LedgerEvent]) -> list[dict]:
        with self.store.connect() as db:
            rows = db.execute("SELECT * FROM corporate_actions ORDER BY COALESCE(record_date,payment_date,announcement_date) DESC, id DESC").fetchall()
            receipts = {int(r["action_id"]): dict(r) for r in db.execute("SELECT * FROM corporate_action_receipts").fetchall()}
        out = []
        for row in rows:
            item = dict(row)
            try:
                item["raw"] = json.loads(item.pop("raw_json") or "{}")
            except Exception:
                item["raw"] = {}
                item.pop("raw_json", None)
            record_date = item.get("record_date")
            held = None
            if record_date:
                state = derive_state([e for e in events if e.event_date <= record_date])
                position = state.positions.get(item["symbol"])
                held = float(position.shares) if position else 0.0
            expected_cash = held * float(item["cash_per_share"]) if held is not None and item.get("cash_per_share") is not None else None
            expected_shares = held * float(item["stock_ratio"]) if held is not None and item.get("stock_ratio") is not None else None
            receipt = receipts.get(int(item["id"]))
            status = "ANNOUNCED"
            differences = {}
            if held is not None:
                status = "ENTITLEMENT_READY"
            if receipt:
                status = "RECEIVED"
                if expected_cash is not None:
                    differences["cash"] = float(receipt["actual_cash"]) - expected_cash
                if expected_shares is not None:
                    differences["shares"] = float(receipt["actual_shares"]) - expected_shares
                if differences and all(abs(v) <= 1e-6 for v in differences.values()):
                    status = "RECONCILED"
            item.update({
                "held_on_record_date": held,
                "expected_cash": expected_cash,
                "expected_shares": expected_shares,
                "receipt": receipt,
                "differences": differences,
                "status": status,
            })
            out.append(item)
        return out

    # ------------------------------------------------------------------
    # NAV controls / restatement
    # ------------------------------------------------------------------
    def nav_status(self, snapshots: list[dict]) -> list[dict]:
        with self.store.connect() as db:
            controls = {r["snapshot_date"]: dict(r) for r in db.execute("SELECT * FROM nav_controls").fetchall()}
        out = []
        for snapshot in snapshots:
            date_key = snapshot["snapshot_date"]
            control = controls.get(date_key)
            default_status = "OFFICIAL" if snapshot.get("official") else "DRAFT"
            out.append({**snapshot, "nav_status": (control or {}).get("status") or default_status, "nav_control": control})
        return out

    def lock_nav(self, snapshot_date: str) -> dict:
        with self.store.connect() as db:
            exists = db.execute("SELECT 1 FROM portfolio_snapshots WHERE snapshot_date=? AND official=1", (snapshot_date,)).fetchone()
            if not exists:
                raise ValueError("Only an official snapshot can be locked.")
            db.execute(
                """
                INSERT INTO nav_controls(snapshot_date,status,reason,locked_at,updated_at)
                VALUES (?, 'LOCKED', '', ?, ?)
                ON CONFLICT(snapshot_date) DO UPDATE SET status='LOCKED',locked_at=excluded.locked_at,updated_at=excluded.updated_at
                """,
                (snapshot_date, _now(), _now()),
            )
        return {"ok": True, "snapshot_date": snapshot_date, "status": "LOCKED"}

    def mark_restatement(self, affected_from_date: str, reason: str, correction_event_id: int | None = None) -> int:
        reason = str(reason or "Historical ledger correction")[:500]
        with self.store.connect() as db:
            cur = db.execute(
                """
                INSERT INTO nav_restatements(affected_from_date,reason,correction_event_id,status,created_at)
                VALUES (?,?,?,'OPEN',?)
                """,
                (affected_from_date, reason, correction_event_id, _now()),
            )
            db.execute(
                """
                INSERT INTO nav_controls(snapshot_date,status,reason,updated_at)
                SELECT snapshot_date,'RESTATEMENT_REQUIRED',?,?
                FROM portfolio_snapshots WHERE snapshot_date >= ?
                ON CONFLICT(snapshot_date) DO UPDATE SET
                    status='RESTATEMENT_REQUIRED',reason=excluded.reason,updated_at=excluded.updated_at
                """,
                (reason, _now(), affected_from_date),
            )
            return int(cur.lastrowid)

    def restatements(self) -> list[dict]:
        with self.store.connect() as db:
            rows = db.execute("SELECT * FROM nav_restatements ORDER BY id DESC").fetchall()
        return [dict(r) for r in rows]

    def resolve_restatement(self, restatement_id: int) -> dict:
        with self.store.connect() as db:
            row = db.execute("SELECT * FROM nav_restatements WHERE id=?", (int(restatement_id),)).fetchone()
            if not row:
                raise ValueError("Restatement not found.")
            db.execute("UPDATE nav_restatements SET status='RESOLVED',resolved_at=? WHERE id=?", (_now(), int(restatement_id)))
            db.execute(
                "UPDATE nav_controls SET status='OFFICIAL',reason='',updated_at=? WHERE snapshot_date >= ? AND status='RESTATEMENT_REQUIRED'",
                (_now(), row["affected_from_date"]),
            )
        return {"ok": True, "restatement_id": int(restatement_id), "status": "RESOLVED"}

    # ------------------------------------------------------------------
    # Reporting / exceptions
    # ------------------------------------------------------------------
    @staticmethod
    def pnl_attribution(events: list[LedgerEvent], prices: dict[str, dict]) -> list[dict]:
        state = PortfolioState()
        realized = defaultdict(float)
        dividends = defaultdict(float)
        for event in sorted(events, key=lambda e: (e.event_date, int(e.id or 0))):
            before = state.realized_pnl
            apply_event(state, event)
            if event.symbol and state.realized_pnl != before:
                realized[event.symbol] += state.realized_pnl - before
            if event.event_type == EventType.CASH_DIVIDEND and event.symbol:
                dividends[event.symbol] += float(event.amount or 0)
        symbols = sorted(set(realized) | set(dividends) | set(state.positions))
        rows = []
        for symbol in symbols:
            position = state.positions.get(symbol)
            unrealized = 0.0
            if position:
                quote = prices.get(symbol)
                if quote and quote.get("close") is not None:
                    unrealized = position.shares * float(quote["close"]) - position.cost_basis
            total = realized[symbol] + dividends[symbol] + unrealized
            rows.append({
                "symbol": symbol,
                "realized_pnl": realized[symbol],
                "unrealized_pnl": unrealized,
                "dividend_income": dividends[symbol],
                "total_contribution_vnd": total,
            })
        rows.sort(key=lambda x: abs(x["total_contribution_vnd"]), reverse=True)
        return rows

    def exceptions(self, *, settlement: dict, reconciliations: list[dict], corporate_actions: list[dict], restatements: list[dict], market_status: str) -> list[dict]:
        out = []
        if market_status != "VALID":
            out.append({"severity": "WARNING", "code": "MARKET_DATA", "message": "Market data is not fully aligned."})
        for trade in settlement.get("trades") or []:
            if trade["status"] == "DUE_UNCONFIRMED":
                out.append({"severity": "WARNING", "code": "SETTLEMENT_DUE", "message": f"Trade #{trade['event_id']} {trade['symbol']} is due but not confirmed settled.", "ref": trade["event_id"]})
        if not reconciliations:
            out.append({"severity": "INFO", "code": "NO_RECONCILIATION", "message": "No broker reconciliation has been recorded yet."})
        elif reconciliations[0].get("status") != "MATCH":
            out.append({"severity": "WARNING", "code": "RECONCILIATION_MISMATCH", "message": f"Latest broker reconciliation #{reconciliations[0]['id']} has differences.", "ref": reconciliations[0]["id"]})
        for action in corporate_actions:
            if action.get("receipt") and action.get("status") != "RECONCILED":
                out.append({"severity": "WARNING", "code": "CORPORATE_ACTION_MISMATCH", "message": f"{action['symbol']} corporate action #{action['id']} receipt differs from expected entitlement.", "ref": action["id"]})
            elif action.get("verification_status") != "VERIFIED" and action.get("record_date") and action["record_date"] >= self.today_fn():
                out.append({"severity": "INFO", "code": "CORPORATE_ACTION_UNVERIFIED", "message": f"Upcoming {action['symbol']} corporate action #{action['id']} is not VSDC/exchange verified yet.", "ref": action["id"]})
        for item in restatements:
            if item.get("status") == "OPEN":
                out.append({"severity": "WARNING", "code": "NAV_RESTATEMENT", "message": f"NAV history from {item['affected_from_date']} requires restatement review.", "ref": item["id"]})
        return out

    def overview(self, *, events: list[LedgerEvent], state: PortfolioState, prices: dict[str, dict], snapshots: list[dict], preferences: dict, market_status: str) -> dict:
        symbols = sorted(state.positions)
        self.ensure_securities(symbols)
        reserve = preferences.get("cash_reserve") if preferences.get("cash_reserve_configured") else None
        settlement = self.settlement_view(events, state.cash, reserve=reserve)
        reconciliations = self.reconciliations()
        actions = self.corporate_actions(events)
        restatements = self.restatements()
        controlled_nav = self.nav_status(snapshots)
        return {
            "book_type": "INSTITUTIONAL_LITE_IBOR",
            "accounting_cost_method": "FIFO_TAX_LOTS",
            "position_recognition": "TRADE_DATE",
            "securities": self.securities(),
            "tax_lots": self.tax_lots(state),
            "settlement": settlement,
            "reconciliations": reconciliations,
            "corporate_actions": actions,
            "corporate_action_provider": self.ca_provider.health(),
            "nav_controls": controlled_nav,
            "restatements": restatements,
            "pnl_attribution": self.pnl_attribution(events, prices),
            "exceptions": self.exceptions(
                settlement=settlement,
                reconciliations=reconciliations,
                corporate_actions=actions,
                restatements=restatements,
                market_status=market_status,
            ),
            "controls": {
                "source_ledger": "IMMUTABLE_WITH_APPEND_ONLY_CORRECTIONS",
                "reconciliation": "MANUAL_BROKER_SNAPSHOT",
                "corporate_action_posting": "PROPOSAL_AND_RECONCILIATION_ONLY",
                "nav_locking": "SUPPORTED",
                "full_double_entry_gl": "DEFERRED",
                "multi_currency": "DEFERRED",
            },
        }
