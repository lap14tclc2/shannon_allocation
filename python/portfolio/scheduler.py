from __future__ import annotations

import logging
import os
import threading
from datetime import datetime
from zoneinfo import ZoneInfo

from .activity import append_activity
from .service import PortfolioService

log = logging.getLogger(__name__)
VN_TZ = ZoneInfo("Asia/Ho_Chi_Minh")


class DailySyncScheduler:
    """Small idempotent EOD scheduler for a continuously running local server.

    At the configured time (15:30 Asia/Ho_Chi_Minh by default):
      * trading weekdays: sync D1 prices and rebuild snapshots;
      * every calendar day: discover corporate actions for current holdings.

    Discovery never posts dividends/shares to the source ledger. Receipt and
    posting remain explicit user actions after verification/reconciliation.
    """

    def __init__(self, service: PortfolioService, hhmm: str | None = None) -> None:
        self.service = service
        self.hhmm = hhmm or os.environ.get("PORTFOLIO_SYNC_TIME", "15:30")
        hour, minute = self.hhmm.split(":", 1)
        self.hour = int(hour); self.minute = int(minute)
        if not (0 <= self.hour <= 23 and 0 <= self.minute <= 59):
            raise ValueError("PORTFOLIO_SYNC_TIME must be HH:MM")
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None
        self._last_attempt_date: str | None = None

    def start(self) -> None:
        if self._thread and self._thread.is_alive(): return
        self._thread = threading.Thread(target=self._loop, name="portfolio-daily-sync", daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()

    def _sync_corporate_actions(self) -> dict | None:
        book = getattr(self.service, "book", None)
        if book is None or not hasattr(book, "sync_corporate_actions"):
            return None
        symbols = sorted(getattr(self.service.current_state(), "positions", {}).keys())
        result = book.sync_corporate_actions(symbols)
        try:
            append_activity(
                self.service.store,
                actor_type="SYSTEM",
                actor_id="scheduler",
                category="CORPORATE_ACTION",
                action="CORPORATE_ACTION_SYNC",
                summary=f"Scheduled corporate-action sync discovered {result.get('discovered', 0)} event(s).",
                details=result,
                status="SUCCESS" if result.get("ok", True) else "PARTIAL",
            )
        except Exception:
            log.exception("Could not append corporate-action scheduler activity")
        return result

    def run_once(self, now: datetime | None = None) -> dict:
        now = now or datetime.now(VN_TZ)
        weekday = now.weekday() < 5
        result: dict = {"date": now.date().isoformat(), "scheduled_time": self.hhmm, "market": None, "corporate_actions": None}
        if weekday:
            result["market"] = self.service.sync_daily()
        try:
            result["corporate_actions"] = self._sync_corporate_actions()
        except Exception as exc:
            result["corporate_actions"] = {"ok": False, "error": str(exc)}
            log.exception("Scheduled corporate-action sync failed")
        return result

    def _loop(self) -> None:
        while not self._stop.is_set():
            now = datetime.now(VN_TZ)
            today = now.date().isoformat()
            after_time = (now.hour, now.minute) >= (self.hour, self.minute)
            if after_time and self._last_attempt_date != today:
                self._last_attempt_date = today
                try:
                    result = self.run_once(now)
                    market = result.get("market") or {}
                    ca = result.get("corporate_actions") or {}
                    log.info(
                        "Daily QPort sync: market=%s corporate_actions=%s",
                        market.get("message") or ("skipped-weekend" if now.weekday() >= 5 else "done"),
                        ca.get("discovered", ca.get("error", "n/a")),
                    )
                except Exception:
                    log.exception("Daily QPort sync failed")
            self._stop.wait(30.0)
