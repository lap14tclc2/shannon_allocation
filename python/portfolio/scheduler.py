from __future__ import annotations

import logging
import os
import threading
import time
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from .service import PortfolioService

log = logging.getLogger(__name__)
VN_TZ = ZoneInfo("Asia/Ho_Chi_Minh")


class DailySyncScheduler:
    """Small idempotent EOD scheduler for a continuously running local server.

    It performs data sync/snapshot creation only. It has no access to an API that
    can create ledger transactions.
    """

    def __init__(self, service: PortfolioService, hhmm: str | None = None) -> None:
        self.service = service
        self.hhmm = hhmm or os.environ.get("PORTFOLIO_SYNC_TIME", "15:30")
        hour, minute = self.hhmm.split(":", 1)
        self.hour = int(hour)
        self.minute = int(minute)
        if not (0 <= self.hour <= 23 and 0 <= self.minute <= 59):
            raise ValueError("PORTFOLIO_SYNC_TIME must be HH:MM")
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None
        self._last_attempt_date: str | None = None

    def start(self) -> None:
        if self._thread and self._thread.is_alive():
            return
        self._thread = threading.Thread(target=self._loop, name="portfolio-daily-sync", daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()

    def _loop(self) -> None:
        while not self._stop.is_set():
            now = datetime.now(VN_TZ)
            today = now.date().isoformat()
            after_time = (now.hour, now.minute) >= (self.hour, self.minute)
            weekday = now.weekday() < 5
            if weekday and after_time and self._last_attempt_date != today:
                self._last_attempt_date = today
                try:
                    result = self.service.sync_daily()
                    log.info("Daily portfolio sync: %s", result.get("message"))
                except Exception:
                    log.exception("Daily portfolio sync failed")
            self._stop.wait(30.0)
