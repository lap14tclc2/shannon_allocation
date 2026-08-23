from __future__ import annotations

import importlib.util
import json
import multiprocessing as mp
import re
import time
from typing import Any


class VnstockIsolatedError(RuntimeError):
    pass


def vnstock_available() -> bool:
    return importlib.util.find_spec("vnstock") is not None or importlib.util.find_spec("vnstock_data") is not None


def _records(frame) -> list[dict]:
    if frame is None:
        return []
    if hasattr(frame, "to_json"):
        try:
            return json.loads(frame.to_json(orient="records", date_format="iso"))
        except Exception:
            pass
    if hasattr(frame, "to_dict"):
        try:
            return [dict(row) for row in frame.to_dict("records")]
        except Exception:
            pass
    if isinstance(frame, dict):
        return [dict(frame)]
    if isinstance(frame, list):
        return [dict(row) for row in frame if isinstance(row, dict)]
    return []


def _reference_factory():
    try:
        from vnstock import Reference  # type: ignore
        return Reference, "vnstock", "community_v4"
    except Exception as community_exc:
        try:
            from vnstock_data import Reference  # type: ignore
            return Reference, "vnstock_data", "sponsor"
        except Exception as sponsor_exc:
            raise RuntimeError(f"vnstock: {community_exc}; vnstock_data: {sponsor_exc}") from sponsor_exc


def _market_factory():
    try:
        from vnstock import Market  # type: ignore
        return Market, "community_v4"
    except Exception:
        from vnstock.ui import Market  # type: ignore
        return Market, "legacy_ui"


def _company_events(ref, symbol: str) -> list[dict]:
    company = getattr(ref, "company", None)
    if company is None:
        return []
    events_method = getattr(company, "events", None)
    if callable(events_method):
        for call in (lambda: events_method(symbol=symbol), lambda: events_method(symbol)):
            try:
                rows = _records(call())
                if rows:
                    return rows
            except Exception:
                pass
    if callable(company):
        try:
            obj = company(symbol)
            method = getattr(obj, "events", None)
            if callable(method):
                return _records(method())
        except Exception:
            pass
    return []


def _company_info(ref, symbol: str) -> list[dict]:
    company = getattr(ref, "company", None)
    if company is None:
        return []
    if callable(company):
        try:
            obj = company(symbol)
            method = getattr(obj, "info", None)
            if callable(method):
                rows = _records(method())
                if rows:
                    return rows
        except Exception:
            pass
    info = getattr(company, "info", None)
    if callable(info):
        for call in (lambda: info(symbol=symbol), lambda: info(symbol)):
            try:
                rows = _records(call())
                if rows:
                    return rows
            except Exception:
                pass
    return []


def _calendar_events(ref, start: str, end: str) -> list[dict]:
    events_obj = getattr(ref, "events", None)
    calendar = getattr(events_obj, "calendar", None) if events_obj is not None else None
    if not callable(calendar):
        return []
    try:
        return _records(calendar(start=start, end=end, event_type="dividend"))
    except Exception:
        return []


def _ohlcv(market, symbol: str, start: str, end: str):
    equity = market.equity
    if hasattr(equity, "ohlcv"):
        return equity.ohlcv(symbol=symbol.upper(), start=start, end=end, interval="1D")
    if callable(equity):
        return equity(symbol.upper()).ohlcv(start=start, end=end, interval="1D")
    raise RuntimeError("Unsupported Vnstock Market.equity interface")


def _worker(task: str, payload: dict[str, Any], queue) -> None:
    try:
        if task == "ohlcv":
            Market, variant = _market_factory()
            rows = _records(_ohlcv(Market(), payload["symbol"], payload["start"], payload["end"]))
            queue.put({"status": "success", "data": rows, "provider": "vnstock", "api_variant": variant})
            return

        Reference, provider, variant = _reference_factory()
        ref = Reference()
        if task == "events":
            symbols = [str(s).upper() for s in payload.get("symbols") or []]
            rows = _calendar_events(ref, payload["start"], payload["end"])
            if not rows:
                rows = []
                for symbol in symbols:
                    for row in _company_events(ref, symbol):
                        item = dict(row)
                        item.setdefault("symbol", symbol)
                        rows.append(item)
            queue.put({"status": "success", "data": rows, "provider": provider, "api_variant": variant})
            return
        if task == "company_info":
            rows = _company_info(ref, str(payload["symbol"]).upper())
            queue.put({"status": "success", "data": rows, "provider": provider, "api_variant": variant})
            return
        raise RuntimeError(f"Unknown Vnstock task: {task}")
    except BaseException as exc:  # child isolation deliberately contains SystemExit too
        try:
            queue.put({"status": "error", "error": f"{type(exc).__name__}: {exc}"})
        except Exception:
            pass


def _is_rate_limit(text: str) -> bool:
    low = str(text or "").lower()
    return any(key in low for key in ("rate limit", "429", "wait to retry", "maximum api request", "20 requests"))


def _wait_seconds(text: str) -> int:
    for pattern in (r"chờ\s+(\d+)\s*giây", r"wait\s+(\d+)\s*seconds?", r"retry\s+after\s+(\d+)"):
        match = re.search(pattern, str(text or ""), re.IGNORECASE)
        if match:
            return min(120, int(match.group(1)) + 2)
    return 15


def run_vnstock_task(task: str, payload: dict[str, Any], *, timeout: float = 120.0, max_attempts: int = 3) -> dict:
    """Run one Vnstock call in an isolated spawned child process.

    This mirrors the proven pattern used by the user's dnse_bot: the parent QPort
    server survives Vnstock SystemExit/crashes/timeouts and handles rate limits
    as temporary provider failures instead of process-wide failures.
    """
    if not vnstock_available():
        raise VnstockIsolatedError("Vnstock is not installed. Install python/requirements-vnstock.txt.")
    last_error = "unknown Vnstock failure"
    ctx = mp.get_context("spawn")
    for attempt in range(1, max(1, int(max_attempts)) + 1):
        queue = ctx.Queue()
        process = ctx.Process(target=_worker, args=(task, dict(payload), queue), daemon=True)
        process.start()
        process.join(timeout=timeout)
        if process.is_alive():
            process.terminate(); process.join(timeout=5)
            last_error = f"Vnstock {task} timed out after {timeout:g}s"
        else:
            result = None
            try:
                if not queue.empty():
                    result = queue.get_nowait()
            except Exception:
                result = None
            if result and result.get("status") == "success":
                return result
            if result:
                last_error = str(result.get("error") or last_error)
            else:
                last_error = f"Vnstock {task} child exited without result (exitcode={process.exitcode})"
        if attempt < max_attempts:
            time.sleep(_wait_seconds(last_error) if _is_rate_limit(last_error) else min(10, 2 * attempt))
    raise VnstockIsolatedError(last_error)
