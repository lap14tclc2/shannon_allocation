from __future__ import annotations

import json
import re
from dataclasses import replace
from datetime import date, timedelta

from .accounting import derive_state
from .correctable_service import CorrectablePortfolioService
from .corrections import effective_events
from .domain import EventType
from .market_data import frame_to_price_rows
from .tax_policy import CASH_DIVIDEND_WITHHOLDING_RATE, apply_dividend_tax_policy
from .validation import normalize_event_payload

VIETNAM_PAR_VALUE_VND = 10_000.0


def _previous_day(day: str) -> str:
    return (date.fromisoformat(day) - timedelta(days=1)).isoformat()


def _cash_percent_fallback(action: dict) -> tuple[float | None, float | None]:
    """Return (cash_per_share, percent) when a provider only says e.g. 7% cash."""
    explicit = action.get("cash_per_share")
    if explicit not in (None, ""):
        try:
            value = float(explicit)
            return (value if value > 0 else None), None
        except Exception:
            pass

    raw = action.get("raw_json") or action.get("raw") or {}
    if not isinstance(raw, str):
        raw = json.dumps(raw, ensure_ascii=False)
    text = raw.lower().replace(",", ".")
    patterns = (
        r"(\d+(?:\.\d+)?)\s*%\s*(?:bằng\s*)?(?:tiền|tiền mặt|cash)",
        r"(?:tiền|tiền mặt|cash)[^\d%]{0,30}(\d+(?:\.\d+)?)\s*%",
    )
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            pct = float(match.group(1))
            if 0 < pct <= 100:
                return VIETNAM_PAR_VALUE_VND * pct / 100.0, pct
    return None, None


class AutomatedPortfolioService(CorrectablePortfolioService):
    """Operational QPort service with automatic dividend posting and tax policy."""

    def _apply_tax_to_payload(self, payload: dict, prior_events: list, *, event_id=None, created_by="local") -> dict:
        clean = normalize_event_payload(payload, today=self.today_vn())
        draft = self._event_from_clean(clean, event_id=event_id, created_by=str(created_by or "local")[:100])
        taxed = apply_dividend_tax_policy(draft, prior_events)
        return {
            "event_type": taxed.event_type.value,
            "event_date": taxed.event_date,
            "symbol": taxed.symbol,
            "quantity": taxed.quantity,
            "price": taxed.price,
            "fee": taxed.fee,
            "tax": taxed.tax,
            "amount": taxed.amount,
            "ratio": taxed.ratio,
            "note": taxed.note,
            "metadata": taxed.metadata,
            "broker_code": taxed.broker_code,
            "account_id": taxed.account_id,
            "settlement_date": taxed.settlement_date,
        }

    def append_event(self, payload: dict, created_by: str = "local") -> dict:
        prior = effective_events(self.store)
        taxed_payload = self._apply_tax_to_payload(payload, prior, created_by=created_by)
        result = super().append_event(taxed_payload, created_by=created_by)
        # Holdings, Performance and Transaction history all derive from the same
        # effective ledger. Rebuild immediately when the parent service did not
        # already rebuild a historical mutation.
        if result.get("history") is None:
            result["history"] = self._refresh_derived_history()
        result["portfolio_sync"] = "LEDGER_DERIVED_IMMEDIATE"
        return result

    def _replacement_event(self, event_id: int, payload: dict):
        current = next((e for e in effective_events(self.store) if int(e.id or 0) == int(event_id)), None)
        replacement = super()._replacement_event(event_id, payload)
        # The frontend sends the visible total SELL tax. Restore previous automatic
        # tax metadata before recalculation so an edit cannot double-count it.
        if current is not None:
            old_meta = current.metadata or {}
            new_meta = dict(replacement.metadata or {})
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
                if key in old_meta and key not in new_meta:
                    new_meta[key] = old_meta[key]
            replacement = replace(replacement, metadata=new_meta)
        prior = [e for e in effective_events(self.store) if int(e.id or 0) != int(event_id)]
        return apply_dividend_tax_policy(replacement, prior)

    def _sync_symbol(self, symbol: str, today: date, force: bool = False) -> dict:
        """Fetch enough D1 history for both valuation and meaningful risk metrics."""
        return super()._sync_symbol(symbol, today, force=force)

    def dashboard(self) -> dict:
        data = super().dashboard()
        health = data.get("health") or {}
        risk = data.get("risk") or {}
        perf = data.get("performance_summary") or {}
        quality = risk.get("quality") or {}
        missing = quality.get("missing_symbols") or []
        for flag in health.get("flags") or []:
            if flag.get("code") == "RISK_COVERAGE":
                coverage = float(quality.get("coverage_weight") or 0)
                suffix = f" Missing D1 history: {', '.join(missing)}." if missing else ""
                flag["message"] = (
                    f"Risk coverage is {coverage * 100:.1f}% (target ≥90%).{suffix} "
                    "Volatility/correlation/tail-risk fields stay suppressed until evidence is sufficient."
                )
            elif flag.get("code") == "PERFORMANCE_HISTORY":
                count = int(perf.get("official_snapshot_count") or 0)
                flag["message"] = (
                    f"Only {count} official daily snapshots are available. "
                    "QPort needs at least 20 for basic short-history statistics and roughly 252 for a full 1-year view."
                )

        events = effective_events(self.store)
        cash_dividend_tax = sum(
            float((e.metadata or {}).get("cash_dividend_withholding_tax") or 0)
            for e in events if e.event_type == EventType.CASH_DIVIDEND
        )
        stock_dividend_sale_tax = sum(
            float((e.metadata or {}).get("stock_dividend_sale_tax") or 0)
            for e in events if e.event_type == EventType.SELL
        )
        perf["cash_dividend_tax"] = cash_dividend_tax
        perf["stock_dividend_sale_tax"] = stock_dividend_sale_tax
        perf["net_dividend_income"] = float(perf.get("dividend_income") or 0) - cash_dividend_tax
        perf["tax_policy"] = "CASH_DIVIDEND_5PCT_WITHHOLDING; STOCK_DIVIDEND_5PCT_PAR_OR_LOWER_TRANSFER_PRICE_ON_SALE"
        data["performance_summary"] = perf
        data["health"] = health
        return data

    def performance(self) -> dict:
        perf = super().performance()
        events = effective_events(self.store)
        cash_tax = sum(float((e.metadata or {}).get("cash_dividend_withholding_tax") or 0) for e in events if e.event_type == EventType.CASH_DIVIDEND)
        stock_tax = sum(float((e.metadata or {}).get("stock_dividend_sale_tax") or 0) for e in events if e.event_type == EventType.SELL)
        perf.update({
            "cash_dividend_tax": cash_tax,
            "stock_dividend_sale_tax": stock_tax,
            "net_dividend_income": float(perf.get("dividend_income") or 0) - cash_tax,
            "tax_policy": "CASH_DIVIDEND_5PCT_WITHHOLDING; STOCK_DIVIDEND_5PCT_PAR_OR_LOWER_TRANSFER_PRICE_ON_SALE",
        })
        return perf

    def _entitlement_state(self, action: dict):
        ex_date = action.get("ex_date")
        cutoff = _previous_day(ex_date) if ex_date else (action.get("record_date") or action.get("payment_date"))
        if not cutoff:
            return None, None
        events = [event for event in effective_events(self.store) if event.event_date <= cutoff]
        return derive_state(events), cutoff

    @staticmethod
    def _broker_account_entitlements(entitlement_state, symbol: str) -> list[dict]:
        """Capture who owned the entitled shares at the entitlement cutoff."""
        position = entitlement_state.positions.get(symbol) if entitlement_state else None
        if position is None or position.shares <= 0:
            return []
        groups: dict[tuple[str, str], float] = {}
        for lot in position.lots:
            quantity = float(lot.remaining_quantity or 0)
            if quantity <= 0:
                continue
            key = (str(lot.broker_code or "UNASSIGNED").upper(), str(lot.account_id or "PRIMARY").upper())
            groups[key] = groups.get(key, 0.0) + quantity
        if not groups:
            groups[("UNASSIGNED", "PRIMARY")] = float(position.shares)
        return [
            {"broker_code": broker, "account_id": account, "entitled_shares": shares}
            for (broker, account), shares in sorted(groups.items())
        ]

    @staticmethod
    def _with_cash_allocation(allocations: list[dict], total_shares: float, gross_cash: float) -> list[dict]:
        out = []
        for row in allocations:
            weight = float(row.get("entitled_shares") or 0) / total_shares if total_shares > 0 else 0.0
            gross = gross_cash * weight
            tax = gross * CASH_DIVIDEND_WITHHOLDING_RATE
            out.append({
                **row,
                "cash_dividend_gross": gross,
                "cash_dividend_tax": tax,
                "cash_dividend_net": gross - tax,
            })
        return out

    @staticmethod
    def _with_stock_allocation(allocations: list[dict], total_shares: float, received_shares: float) -> list[dict]:
        out = []
        allocated = 0.0
        for index, row in enumerate(allocations):
            if index == len(allocations) - 1:
                quantity = max(0.0, received_shares - allocated)
            else:
                weight = float(row.get("entitled_shares") or 0) / total_shares if total_shares > 0 else 0.0
                quantity = received_shares * weight
                allocated += quantity
            out.append({**row, "stock_dividend_shares": quantity})
        return out

    def auto_post_due_dividends(self, as_of: str | None = None, created_by: str = "system:corporate-action") -> dict:
        today = str(as_of or self.today_vn())
        events = effective_events(self.store)
        actions = self.book.corporate_actions(events)
        with self.store.connect() as db:
            posted = {
                (int(row["action_id"]), str(row["posting_type"]))
                for row in db.execute("SELECT action_id,posting_type FROM corporate_action_postings").fetchall()
            }

        created: list[dict] = []
        skipped: list[dict] = []
        for action in actions:
            action_id = int(action["id"])
            action_type = str(action.get("action_type") or "").upper()
            if action_type not in {"CASH_DIVIDEND", "STOCK_DIVIDEND"}:
                continue
            payment_date = action.get("payment_date")
            if not payment_date or payment_date > today:
                continue

            boundary = self._tracking_boundary()
            entitlement_date = self._corporate_action_entitlement_date(action)
            if (
                boundary.get("initialization_mode") == "CURRENT"
                and boundary.get("tracking_start_date")
                and entitlement_date
                and entitlement_date < boundary["tracking_start_date"]
            ):
                skipped.append({
                    "action_id": action_id,
                    "symbol": action["symbol"],
                    "reason": "ENTITLEMENT_BEFORE_TRACKING_START",
                    "entitlement_date": entitlement_date,
                })
                continue

            posting_type = "CASH" if action_type == "CASH_DIVIDEND" else "STOCK"
            if (action_id, posting_type) in posted:
                continue

            entitlement_state, entitlement_date = self._entitlement_state(action)
            position = entitlement_state.positions.get(action["symbol"]) if entitlement_state else None
            entitled_shares = float(position.shares) if position else 0.0
            if entitled_shares <= 0:
                skipped.append({"action_id": action_id, "symbol": action["symbol"], "reason": "NO_ENTITLED_SHARES"})
                continue
            broker_allocations = self._broker_account_entitlements(entitlement_state, action["symbol"])

            metadata = {
                "corporate_action_id": action_id,
                "corporate_action_source": action.get("source_url") or action.get("source"),
                "auto_generated": True,
                "entitlement_date": entitlement_date,
                "entitlement_shares": entitled_shares,
                "payment_date": payment_date,
                "broker_code": "UNASSIGNED",
                "account_id": "PRIMARY",
            }

            if posting_type == "CASH":
                cash_per_share, cash_pct = _cash_percent_fallback(action)
                if not cash_per_share or cash_per_share <= 0:
                    skipped.append({"action_id": action_id, "symbol": action["symbol"], "reason": "MISSING_CASH_PER_SHARE"})
                    continue
                amount = entitled_shares * cash_per_share
                metadata.update({
                    "cash_per_share": cash_per_share,
                    "cash_rate_percent": cash_pct,
                    "broker_account_allocations": self._with_cash_allocation(broker_allocations, entitled_shares, amount),
                })
                payload = {
                    "event_type": "CASH_DIVIDEND", "event_date": payment_date, "symbol": action["symbol"],
                    "amount": amount,
                    "note": f"Auto dividend #{action_id}: {cash_per_share:g} VND/share × {entitled_shares:g} shares",
                    "metadata": metadata,
                }
            else:
                ratio = float(action.get("stock_ratio") or 0)
                if ratio <= 0:
                    skipped.append({"action_id": action_id, "symbol": action["symbol"], "reason": "MISSING_STOCK_RATIO"})
                    continue
                quantity = entitled_shares * ratio
                metadata.update({
                    "stock_ratio": ratio,
                    "broker_account_allocations": self._with_stock_allocation(broker_allocations, entitled_shares, quantity),
                })
                payload = {
                    "event_type": "STOCK_DIVIDEND", "event_date": payment_date, "symbol": action["symbol"],
                    "quantity": quantity,
                    "note": f"Auto stock dividend #{action_id}: {ratio * 100:g}% × {entitled_shares:g} shares",
                    "metadata": metadata,
                }

            try:
                result = self.append_event(payload, created_by=created_by)
            except Exception as exc:
                skipped.append({"action_id": action_id, "symbol": action["symbol"], "reason": "POST_FAILED", "error": str(exc)})
                continue

            event_id = int(result["event_id"])
            posted_event = result.get("event") or {}
            actual_cash = float(payload.get("amount") or 0)
            actual_shares = float(payload.get("quantity") or 0)
            with self.store.connect() as db:
                db.execute(
                    "INSERT OR IGNORE INTO corporate_action_postings(action_id,posting_type,event_id,created_by,created_at) VALUES (?,?,?,?,datetime('now'))",
                    (action_id, posting_type, event_id, created_by),
                )
                db.execute(
                    """
                    INSERT OR IGNORE INTO corporate_action_receipts(
                        action_id,received_date,actual_cash,actual_shares,note,created_by,created_at
                    ) VALUES (?,?,?,?,?,?,datetime('now'))
                    """,
                    (action_id, payment_date, actual_cash, actual_shares, f"Automatically calculated from {entitled_shares:g} entitled shares.", created_by),
                )
            posted.add((action_id, posting_type))
            created.append({
                "action_id": action_id, "event_id": event_id, "symbol": action["symbol"],
                "event_type": action_type, "event_date": payment_date, "entitlement_shares": entitled_shares,
                "broker_account_allocations": metadata.get("broker_account_allocations") or [],
                "amount": payload.get("amount"), "quantity": payload.get("quantity"),
                "tax": posted_event.get("tax"), "net_cash": (posted_event.get("metadata") or {}).get("cash_dividend_net_amount"),
            })

        result = {
            "ok": True, "as_of": today, "created": created, "created_count": len(created), "skipped": skipped,
            "posting_policy": "AUTOMATIC_ON_PAYMENT_DATE_IDEMPOTENT",
        }
        if created or skipped:
            self._log(
                "SYSTEM", created_by, "CORPORATE_ACTION", "DIVIDEND_AUTO_POST",
                f"Dividend automation created {len(created)} ledger transaction(s).",
                details=result, status="SUCCESS" if not skipped else "PARTIAL",
            )
        return result

    def institutional_overview(self) -> dict:
        overview = super().institutional_overview()
        grouped: dict[tuple[str, str, str], dict] = {}
        for event in effective_events(self.store):
            if event.event_type not in {EventType.CASH_DIVIDEND, EventType.STOCK_DIVIDEND} or not event.symbol:
                continue
            meta = event.metadata or {}
            allocations = meta.get("broker_account_allocations") or []
            if not allocations:
                allocations = [{
                    "broker_code": event.broker_code,
                    "account_id": event.account_id,
                    "entitled_shares": float(meta.get("entitlement_shares") or 0),
                    "stock_dividend_shares": float(event.quantity or 0) if event.event_type == EventType.STOCK_DIVIDEND else 0.0,
                    "cash_dividend_gross": float(event.amount or 0) if event.event_type == EventType.CASH_DIVIDEND else 0.0,
                    "cash_dividend_tax": float(meta.get("cash_dividend_withholding_tax") or 0),
                    "cash_dividend_net": float(meta.get("cash_dividend_net_amount") or 0),
                }]
            for allocation in allocations:
                broker = str(allocation.get("broker_code") or "UNASSIGNED").upper()
                account = str(allocation.get("account_id") or "PRIMARY").upper()
                key = (event.symbol.upper(), broker, account)
                row = grouped.setdefault(key, {
                    "symbol": event.symbol.upper(),
                    "broker_code": broker,
                    "account_id": account,
                    "stock_dividend_shares_received": 0.0,
                    "cash_dividend_gross": 0.0,
                    "cash_dividend_tax": 0.0,
                    "cash_dividend_net": 0.0,
                    "event_ids": [],
                    "last_received_date": None,
                })
                row["stock_dividend_shares_received"] += float(allocation.get("stock_dividend_shares") or 0)
                row["cash_dividend_gross"] += float(allocation.get("cash_dividend_gross") or 0)
                row["cash_dividend_tax"] += float(allocation.get("cash_dividend_tax") or 0)
                row["cash_dividend_net"] += float(allocation.get("cash_dividend_net") or 0)
                row["event_ids"].append(int(event.id or 0))
                if not row["last_received_date"] or event.event_date > row["last_received_date"]:
                    row["last_received_date"] = event.event_date

        overview["dividend_receipts_by_broker"] = sorted(
            grouped.values(),
            key=lambda row: (row["symbol"], row["broker_code"], row["account_id"]),
        )
        overview["dividend_automation"] = {
            "posting_policy": "AUTOMATIC_ON_PAYMENT_DATE_IDEMPOTENT",
            "broker_allocation_basis": "ENTITLEMENT_DATE_OPEN_LOTS",
            "manual_transaction_form": "DIVIDEND_TYPES_HIDDEN",
        }
        overview["dividend_tax_policy"] = {
            "cash_dividend_withholding_rate": CASH_DIVIDEND_WITHHOLDING_RATE,
            "stock_dividend_tax_timing": "ON_SALE",
        }
        return overview

    def sync_daily(self, actor_type: str = "SYSTEM", actor_id: str = "scheduler") -> dict:
        result = super().sync_daily(actor_type=actor_type, actor_id=actor_id)
        try:
            corporate_actions = self.sync_corporate_actions()
        except Exception as exc:
            corporate_actions = {"ok": False, "error": str(exc)}
        try:
            auto_dividends = self.auto_post_due_dividends(created_by=f"{actor_type.lower()}:{actor_id}")
        except Exception as exc:
            auto_dividends = {"ok": False, "error": str(exc), "created_count": 0}
        result["corporate_actions"] = corporate_actions
        result["auto_dividends"] = auto_dividends
        return result
