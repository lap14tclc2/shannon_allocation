from __future__ import annotations

import json
import re
from datetime import date, timedelta

from .accounting import derive_state
from .correctable_service import CorrectablePortfolioService
from .corrections import effective_events

VIETNAM_PAR_VALUE_VND = 10_000.0


def _previous_day(day: str) -> str:
    return (date.fromisoformat(day) - timedelta(days=1)).isoformat()


def _cash_percent_fallback(action: dict) -> tuple[float | None, float | None]:
    """Return (cash_per_share, percent) when a provider only says e.g. 7% cash.

    Vietnamese listed common shares normally use VND 10,000 par value for a
    dividend percentage announcement. Explicit provider cash_per_share always
    wins; this parser is only a fallback for text-only provider events.
    """
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
    """QPort service that automatically posts due dividend entitlements.

    Discovery remains provider-driven. Once a CASH_DIVIDEND or STOCK_DIVIDEND
    has a payment date at or before today and enough entitlement information,
    QPort creates the matching immutable ledger transaction exactly once.
    """

    def _entitlement_state(self, action: dict):
        # The holder must own the stock before ex-date. If ex-date is unavailable,
        # record date is the next-best entitlement cutoff.
        ex_date = action.get("ex_date")
        cutoff = _previous_day(ex_date) if ex_date else (action.get("record_date") or action.get("payment_date"))
        if not cutoff:
            return None, None
        events = [event for event in effective_events(self.store) if event.event_date <= cutoff]
        return derive_state(events), cutoff

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

            posting_type = "CASH" if action_type == "CASH_DIVIDEND" else "STOCK"
            if (action_id, posting_type) in posted:
                continue

            entitlement_state, entitlement_date = self._entitlement_state(action)
            position = (entitlement_state.positions.get(action["symbol"]) if entitlement_state else None)
            entitled_shares = float(position.shares) if position else 0.0
            if entitled_shares <= 0:
                skipped.append({"action_id": action_id, "symbol": action["symbol"], "reason": "NO_ENTITLED_SHARES"})
                continue

            metadata = {
                "corporate_action_id": action_id,
                "corporate_action_source": action.get("source_url") or action.get("source"),
                "auto_generated": True,
                "entitlement_date": entitlement_date,
                "entitlement_shares": entitled_shares,
                "payment_date": payment_date,
                # UNASSIGNED intentionally allocates a stock dividend pro-rata
                # across all open broker/account lots instead of inventing a broker.
                "broker_code": "UNASSIGNED",
                "account_id": "PRIMARY",
            }

            if posting_type == "CASH":
                cash_per_share, cash_pct = _cash_percent_fallback(action)
                if not cash_per_share or cash_per_share <= 0:
                    skipped.append({"action_id": action_id, "symbol": action["symbol"], "reason": "MISSING_CASH_PER_SHARE"})
                    continue
                amount = entitled_shares * cash_per_share
                metadata.update({"cash_per_share": cash_per_share, "cash_rate_percent": cash_pct})
                payload = {
                    "event_type": "CASH_DIVIDEND",
                    "event_date": payment_date,
                    "symbol": action["symbol"],
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
                metadata.update({"stock_ratio": ratio})
                payload = {
                    "event_type": "STOCK_DIVIDEND",
                    "event_date": payment_date,
                    "symbol": action["symbol"],
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
            with self.store.connect() as db:
                db.execute(
                    "INSERT OR IGNORE INTO corporate_action_postings(action_id,posting_type,event_id,created_by,created_at) VALUES (?,?,?,?,datetime('now'))",
                    (action_id, posting_type, event_id, created_by),
                )
            posted.add((action_id, posting_type))
            created.append({
                "action_id": action_id,
                "event_id": event_id,
                "symbol": action["symbol"],
                "event_type": action_type,
                "event_date": payment_date,
                "entitlement_shares": entitled_shares,
                "amount": payload.get("amount"),
                "quantity": payload.get("quantity"),
            })

        result = {
            "ok": True,
            "as_of": today,
            "created": created,
            "created_count": len(created),
            "skipped": skipped,
            "posting_policy": "AUTOMATIC_ON_PAYMENT_DATE_IDEMPOTENT",
        }
        if created or skipped:
            self._log(
                "SYSTEM", created_by, "CORPORATE_ACTION", "DIVIDEND_AUTO_POST",
                f"Dividend automation created {len(created)} ledger transaction(s).",
                details=result,
                status="SUCCESS" if not skipped else "PARTIAL",
            )
        return result

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
