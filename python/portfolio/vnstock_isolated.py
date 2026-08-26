from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import time
from pathlib import Path
from typing import Any
import pandas as pd


class VnstockIsolatedError(RuntimeError):
    pass


_WORKER_PATH = Path(__file__).resolve()
_HEALTH_CACHE: dict[str, tuple[float, dict]] = {}


def _writable_runtime_env(base: dict[str, str] | None = None) -> dict[str, str]:
    """Point third-party config/cache writes at Vercel's writable /tmp."""
    env = dict(base or os.environ)
    runtime_dir = Path(env.get("QPORT_VNSTOCK_RUNTIME_DIR") or "/tmp/qport-vnstock")
    paths = {
        "HOME": runtime_dir,
        "USERPROFILE": runtime_dir,
        "XDG_CONFIG_HOME": runtime_dir / "config",
        "XDG_CACHE_HOME": runtime_dir / "cache",
        "XDG_DATA_HOME": runtime_dir / "data",
        "MPLCONFIGDIR": runtime_dir / "matplotlib",
    }
    for path in paths.values():
        path.mkdir(parents=True, exist_ok=True)
    env.update({key: str(path) for key, path in paths.items()})
    return env


def configured_python() -> str:
    """Python interpreter used exclusively for Vnstock calls.

    QPort itself may run on another Python version. Set QPORT_VNSTOCK_PYTHON to
    the python.exe inside the environment where Vnstock is known to work, e.g.
    a Python 3.12 venv. When unset, QPort falls back to its own interpreter.
    """
    configured = str(os.environ.get("QPORT_VNSTOCK_PYTHON") or "").strip().strip('"')
    return str(Path(configured).expanduser()) if configured else sys.executable


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


def _execute_task(task: str, payload: dict[str, Any]) -> dict:
    if task == "probe_reference":
        _, provider, variant = _reference_factory()
        return {
            "status": "success", "data": [], "provider": provider,
            "api_variant": variant, "python": sys.executable,
            "python_version": sys.version.split()[0], "capability": "reference",
        }
    if task == "probe_market":
        _, variant = _market_factory()
        return {
            "status": "success", "data": [], "provider": "vnstock",
            "api_variant": variant, "python": sys.executable,
            "python_version": sys.version.split()[0], "capability": "market",
        }
    if task == "ohlcv":
        Market, variant = _market_factory()
        rows = _records(_ohlcv(Market(), payload["symbol"], payload["start"], payload["end"]))
        return {"status": "success", "data": rows, "provider": "vnstock", "api_variant": variant}

    if task == "valuation_snapshot":
        from datetime import date, timedelta

        symbol = str(payload.get("symbol") or "").upper().strip()
        if not re.fullmatch(r"[A-Z0-9]{3,10}", symbol):
            raise RuntimeError("Invalid symbol")

        def call(method, **kwargs):
            try:
                return _records(method(**kwargs))
            except TypeError:
                kwargs.pop("lang", None)
                return _records(method(**kwargs))

        profile_rows: list[dict] = []
        try:
            Reference, _, _ = _reference_factory()
            profile_rows = _company_info(Reference(), symbol)
        except Exception:
            profile_rows = []

        try:
            from vnstock import Fundamental
            equity = Fundamental().equity(symbol)
            income = call(equity.income_statement, period="quarter", lang="en")
            balance = call(equity.balance_sheet, period="quarter", lang="en")
            cash_flow = call(equity.cash_flow, period="quarter", lang="en")
            ratios = call(equity.ratio, period="quarter", lang="en")
            api_variant = "unified_fundamental_v4"
        except Exception:
            from vnstock import Vnstock
            finance = Vnstock().stock(symbol=symbol, source="VCI").finance
            income = call(finance.income_statement, period="quarter", lang="en")
            balance = call(finance.balance_sheet, period="quarter", lang="en")
            cash_flow = call(finance.cash_flow, period="quarter", lang="en")
            ratios = call(finance.ratio, period="quarter", lang="en")
            api_variant = "legacy_finance_vci"

        end = date.today()
        start = end - timedelta(days=14)
        Market, market_variant = _market_factory()
        prices = _records(_ohlcv(Market(), symbol, start.isoformat(), end.isoformat()))
        if not any((income, balance, cash_flow, ratios)):
            raise RuntimeError(f"No financial data returned for {symbol}")
        return {
            "status": "success",
            "symbol": symbol,
            "provider": "vnstock",
            "api_variant": api_variant,
            "market_variant": market_variant,
            "fetched_at": __import__("datetime").datetime.now(__import__("datetime").timezone.utc).isoformat(),
            "profile": profile_rows,
            "income_statement": income,
            "balance_sheet": balance,
            "cash_flow": cash_flow,
            "ratios": ratios,
            "prices": prices,
        }

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
        return {"status": "success", "data": rows, "provider": provider, "api_variant": variant}
    if task == "company_info":
        rows = _company_info(ref, str(payload["symbol"]).upper())
        return {"status": "success", "data": rows, "provider": provider, "api_variant": variant}
    if task == "financial_statements":
        symbol = str(payload.get("symbol") or "FPT").upper()
        st_type = str(payload.get("statement_type") or "INCOME_STATEMENT")
        period = str(payload.get("period") or "quarter")
        try:
            from vnstock import Vnstock
            v = Vnstock().stock(symbol=symbol, source="VCI")
            fin = v.finance
            if "BALANCE" in st_type:
                df = fin.balance_sheet(period=period, lang="vi")
            elif "CASH" in st_type:
                df = fin.cash_flow(period=period, lang="vi")
            else:
                df = fin.income_statement(period=period, lang="vi")
            rows = _records(df)
            return {"status": "success", "data": rows, "provider": "vnstock", "symbol": symbol, "statement_type": st_type}
        except Exception as exc:
            return {"status": "error", "error": str(exc), "symbol": symbol}
    raise RuntimeError(f"Unknown Vnstock task: {task}")


def _worker_main() -> int:
    """JSON stdin/stdout worker so QPort can use a different Python runtime."""
    import io
    os.environ.update(_writable_runtime_env())
    # Strip current directory and python/ from sys.path to avoid shadowing stdlib locale
    portfolio_dir = str(Path(__file__).resolve().parent)
    python_dir = str(Path(__file__).resolve().parents[1])
    sys.path = [p for p in sys.path if p not in (portfolio_dir, python_dir, "", ".")]
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")
    try:
        request = json.loads(sys.stdin.read() or "{}")
        result = _execute_task(str(request.get("task") or ""), dict(request.get("payload") or {}))
    except BaseException as exc:  # contains SystemExit from third-party code too
        result = {"status": "error", "error": f"{type(exc).__name__}: {exc}", "python": sys.executable}
    sys.stdout.write(json.dumps(result, ensure_ascii=False, default=str) + "\n")
    sys.stdout.flush()
    return 0


def _decode_worker_output(stdout: str) -> dict | None:
    # Some Vnstock builds print banners/notices. The worker result is the last
    # JSON object line, so inspect output from the bottom instead of assuming a
    # clean stdout stream.
    for line in reversed(str(stdout or "").splitlines()):
        line = line.strip()
        if not line:
            continue
        try:
            value = json.loads(line)
            if isinstance(value, dict) and value.get("status") in {"success", "error"}:
                return value
        except Exception:
            continue
    return None


def _run_once(task: str, payload: dict[str, Any], *, timeout: float) -> dict:
    python_exe = configured_python()
    if not Path(python_exe).exists() and python_exe != sys.executable:
        raise VnstockIsolatedError(f"QPORT_VNSTOCK_PYTHON does not exist: {python_exe}")
    
    # Check if running in a serverless environment (e.g. Vercel / AWS Lambda)
    is_serverless = bool(os.environ.get("VERCEL") or os.environ.get("AWS_LAMBDA_FUNCTION_NAME"))
    
    worker_env = _writable_runtime_env()
    worker_env.pop("PYTHONPATH", None)
    worker_env["PYTHONIOENCODING"] = "utf-8"
    root_dir = str(Path(__file__).resolve().parents[2])
    
    try:
        proc = subprocess.run(
            [python_exe, str(_WORKER_PATH), "--worker"],
            input=json.dumps({"task": task, "payload": payload}, ensure_ascii=False),
            text=True,
            encoding="utf-8",
            errors="replace",
            capture_output=True,
            timeout=timeout,
            check=False,
            env=worker_env,
            cwd=root_dir,
        )
        result = _decode_worker_output(proc.stdout)
        if result is not None and result.get("status") == "success":
            result.setdefault("worker_python", python_exe)
            return result
        if result is not None and result.get("status") != "success":
            raise VnstockIsolatedError(str(result.get("error") or f"Vnstock {task} failed"))
    except (subprocess.TimeoutExpired, OSError, VnstockIsolatedError) as exc:
        if not is_serverless:
            raise
    
    # Fallback to direct in-process execution for Serverless / restricted runtimes
    try:
        os.environ.update(_writable_runtime_env())
        direct_result = _execute_task(task, payload)
        direct_result.setdefault("worker_python", sys.executable)
        return direct_result
    except Exception as exc:
        raise VnstockIsolatedError(f"Vnstock {task} in-process failed: {exc}") from exc


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
    """Run Vnstock in a crash-isolated, optionally separate Python environment.

    Set ``QPORT_VNSTOCK_PYTHON`` to the Python 3.12 interpreter/venv where
    Vnstock works. This is intentionally stronger than multiprocessing.spawn:
    the QPort web server may remain on another Python runtime while all Vnstock
    calls execute in the known-good data environment.
    """
    last_error = "unknown Vnstock failure"
    for attempt in range(1, max(1, int(max_attempts)) + 1):
        try:
            return _run_once(task, dict(payload), timeout=timeout)
        except Exception as exc:
            last_error = str(exc)
        if attempt < max_attempts:
            time.sleep(_wait_seconds(last_error) if _is_rate_limit(last_error) else min(10, 2 * attempt))
    raise VnstockIsolatedError(last_error)


def run_valuation_snapshot(symbol: str, *, timeout: float = 120.0, max_attempts: int = 2) -> dict:
    """Fetch one symbol, falling back to fresh CafeF HTML when Vnstock is unusable or incomplete."""
    vnstock_error = None
    try:
        snapshot = run_vnstock_task("valuation_snapshot", {"symbol": symbol}, timeout=timeout, max_attempts=max_attempts)
        flattened_keys = {
            re.sub(r"[^a-z0-9]+", "", str(key).lower())
            for group in ("income_statement", "ratios", "profile")
            for row in snapshot.get(group) or []
            if isinstance(row, dict)
            for key, value in row.items()
            if value is not None and value != ""
        }
        has_profit = any(key.endswith(alias) for key in flattened_keys for alias in ("netprofit", "netprofitaftertax", "profitaftertax", "netincome"))
        has_shares = any(key.endswith(alias) for key in flattened_keys for alias in ("outstandingshare", "outstandingshares", "sharesoutstanding"))
        if has_profit and has_shares:
            return snapshot
        vnstock_error = "Vnstock snapshot is missing net income or outstanding shares"
    except Exception as exc:
        vnstock_error = str(exc)

    from portfolio.cafef_financials import cafef_valuation_snapshot
    fallback = cafef_valuation_snapshot(symbol)
    fallback["fallback_from"] = "vnstock"
    fallback["fallback_reason"] = vnstock_error
    return fallback


def vnstock_runtime_health(capability: str = "reference", *, cache_seconds: float = 60.0) -> dict:
    """Probe actual capability in the configured worker interpreter.

    This prevents the previous false-positive state where the parent Python had
    a package named ``vnstock`` but that version did not expose ``Reference``.
    """
    capability = "market" if capability == "market" else "reference"
    cache_key = f"{configured_python()}::{capability}"
    cached = _HEALTH_CACHE.get(cache_key)
    now = time.monotonic()
    if cached and now - cached[0] <= cache_seconds:
        return dict(cached[1])
    task = "probe_market" if capability == "market" else "probe_reference"
    try:
        result = _run_once(task, {}, timeout=15.0)
        health = {
            "available": True,
            "provider": result.get("provider") or "vnstock",
            "api_variant": result.get("api_variant"),
            "worker_python": result.get("worker_python") or configured_python(),
            "python_version": result.get("python_version"),
            "capability": capability,
            "error": None,
        }
    except Exception as exc:
        health = {
            "available": False,
            "provider": "vnstock",
            "api_variant": "unavailable",
            "worker_python": configured_python(),
            "python_version": None,
            "capability": capability,
            "error": str(exc),
        }
    _HEALTH_CACHE[cache_key] = (now, health)
    return dict(health)


def vnstock_available() -> bool:
    # Compatibility helper used by existing adapters. It now means the actual
    # Reference capability is executable, not merely that a package is importable.
    return bool(vnstock_runtime_health("reference").get("available"))


if __name__ == "__main__":
    if "--worker" in sys.argv:
        raise SystemExit(_worker_main())

