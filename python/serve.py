#!/usr/bin/env python3
"""Serve SSR frontend + joint/fixed allocation optimizer APIs."""

from __future__ import annotations

import argparse
import io
import json
import os
import re
import shutil
import subprocess
import sys
import threading
import time
import urllib.request
import zipfile
from dataclasses import replace
from datetime import datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import unquote, urlparse, parse_qsl

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RESULTS_DIR = os.path.join(REPO, "python", "results")
OPTIMIZER_DIR = os.path.join(RESULTS_DIR, "optimizer")
FRONTEND_DIR = os.path.join(REPO, "frontend")
DIST_DIR = os.path.join(FRONTEND_DIR, "dist")

SSR_HOST = "127.0.0.1"
SSR_PORT = int(os.environ.get("SSR_PORT", "8099"))
SSR_URL = f"http://{SSR_HOST}:{SSR_PORT}"
NODE_SSR = os.path.join(FRONTEND_DIR, "ssr", "server.mjs")

CLIENT_JS = "/assets/client.js"
CLIENT_CSS_DEFAULT = "/assets/entry-client.css"

MIN_FIXED_SYMBOLS = 5
MAX_FIXED_SYMBOLS = 10
MIN_ALLOCATIONS = 1
MAX_ALLOCATIONS = 6
VALID_UNIVERSES = {"all", "vn100", "vn50", "vn30"}

_css_url = None
_backtest_ctx = None
_optimizer_runs: dict = {}
_optimizer_lock = threading.Lock()


def _get_backtest():
    global _backtest_ctx
    if _backtest_ctx is None:
        from backtest import BacktestParams, load_panel
        from backtest.candidate import Candidate
        from backtest.simulation import simulate_combination
        from backtest.optimize.evaluate import result_metrics, allocation_dates_with_initialization

        params = BacktestParams(universe="all")
        prices, _ = load_panel(params)
        _backtest_ctx = {
            "params": params,
            "prices": prices,
            "dates": list(prices.index),
            "symbols": sorted(str(c).upper() for c in prices.columns),
            "Candidate": Candidate,
            "allocation_dates_with_initialization": allocation_dates_with_initialization,
            "simulate_combination": simulate_combination,
            "result_metrics": result_metrics,
        }
    return _backtest_ctx


def _normalise_symbols(value) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        parts = re.split(r"[^A-Za-z0-9]+", value)
    elif isinstance(value, (list, tuple)):
        parts = value
    else:
        return []
    return [str(s).strip().upper() for s in parts if str(s).strip()]


def _client_css_url() -> str:
    global _css_url
    if _css_url is None:
        assets = os.path.join(DIST_DIR, "assets")
        if os.path.isdir(assets):
            for f in sorted(os.listdir(assets)):
                if f.endswith(".css"):
                    _css_url = f"/assets/{f}"
                    break
        if _css_url is None:
            _css_url = CLIENT_CSS_DEFAULT
    return _css_url


MIME = {
    ".html": "text/html; charset=utf-8",
    ".js": "application/javascript; charset=utf-8",
    ".mjs": "application/javascript; charset=utf-8",
    ".css": "text/css; charset=utf-8",
    ".json": "application/json; charset=utf-8",
    ".png": "image/png",
    ".svg": "image/svg+xml",
    ".ico": "image/x-icon",
}

_ssr_proc: subprocess.Popen | None = None
_ssr_lock = threading.Lock()


def _ssr_health() -> bool:
    try:
        with urllib.request.urlopen(f"{SSR_URL}/health", timeout=1.5):
            return True
    except Exception:
        return False


def _ensure_ssr_worker() -> None:
    """Start (or restart) the Node SSR renderer.

    Called at server startup AND lazily before every SSR render, so a worker that
    died mid-session is automatically respawned instead of the page failing with
    'connection refused'. Guarded by a lock for the threaded server.
    """
    global _ssr_proc
    if _ssr_health():
        return
    with _ssr_lock:
        if _ssr_health():
            return
        if not os.path.isfile(os.path.join(FRONTEND_DIR, "dist-ssr", "ssr-entry.mjs")):
            raise RuntimeError("SSR bundle not built. Run: cd frontend && npm run build && npm run build:ssr")
        if not os.path.isfile(os.path.join(DIST_DIR, "assets", "client.js")):
            raise RuntimeError("Client bundle not built. Run: cd frontend && npm run build")
        env = dict(os.environ, SSR_PORT=str(SSR_PORT), SSR_HOST=SSR_HOST)
        _ssr_proc = subprocess.Popen(
            ["node", NODE_SSR],
            cwd=FRONTEND_DIR,
            env=env,
            stdout=sys.stdout,
            stderr=sys.stderr,
        )
        for _ in range(50):
            if _ssr_health():
                return
            time.sleep(0.1)
        raise RuntimeError("Node SSR worker failed to start.")


def _ssr_render(page: str, props: dict) -> str:
    _ensure_ssr_worker()
    body = json.dumps({"page": page, "props": props}).encode("utf-8")
    req = urllib.request.Request(
        f"{SSR_URL}/render",
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=10) as resp:
        payload = json.loads(resp.read().decode("utf-8"))
    return payload["html"]


def _build_document(page: str, props: dict, title: str) -> bytes:
    html = _ssr_render(page, props)
    serialized = json.dumps({"page": page, "props": props}).replace("<", "\\u003c")
    doc = (
        "<!doctype html>\n<html lang='en'><head>"
        "<meta charset='utf-8'>"
        "<meta name='viewport' content='width=device-width, initial-scale=1'>"
        f"<title>{title}</title>"
        f"<link rel='stylesheet' href='{_client_css_url()}'>"
        "</head><body>"
        f"<div id='root'>{html}</div>"
        f"<script>window.__PAGE__={serialized};</script>"
        f"<script type='module' crossorigin src='{CLIENT_JS}'></script>"
        "</body></html>"
    )
    return doc.encode("utf-8")


class Handler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def log_message(self, fmt, *args):
        pass

    def _write_body(self, body):
        try:
            self.wfile.write(body)
            self.wfile.flush()
        except (BrokenPipeError, ConnectionAbortedError, ConnectionResetError, OSError):
            return

    def _send_json(self, status, payload):
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        try:
            self.send_response(status)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self._write_body(body)
        except (BrokenPipeError, ConnectionAbortedError, ConnectionResetError, OSError):
            return

    def _send_bytes(self, status, body, content_type):
        try:
            self.send_response(status)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self._write_body(body)
        except (BrokenPipeError, ConnectionAbortedError, ConnectionResetError, OSError):
            return

    def _send_file(self, path, status=200):
        try:
            with open(path, "rb") as fh:
                body = fh.read()
        except FileNotFoundError:
            return self._send_json(404, {"error": "Not found."})
        ext = os.path.splitext(path)[1].lower()
        self._send_bytes(status, body, MIME.get(ext, "application/octet-stream"))

    def _safe_join(self, base, *parts):
        target = os.path.realpath(os.path.join(base, *parts))
        base_real = os.path.realpath(base)
        if not target.startswith(base_real + os.sep) and target != base_real:
            return None
        return target

    def _read_json(self, folder, filename):
        target = self._safe_join(folder, filename)
        if not target or not os.path.isfile(target):
            return None
        try:
            with open(target, "r", encoding="utf-8") as fh:
                return json.load(fh)
        except Exception:
            return None

    def _runs(self):
        runs_dir = os.path.join(RESULTS_DIR, "runs")
        if not os.path.isdir(runs_dir):
            return []
        out = []
        for rid in os.listdir(runs_dir):
            meta_path = os.path.join(runs_dir, rid, "meta.json")
            if not os.path.isfile(meta_path):
                continue
            try:
                with open(meta_path, "r", encoding="utf-8") as fh:
                    meta = json.load(fh)
            except Exception:
                meta = {}
            out.append({"run_id": rid, "generated_at": meta.get("generated_at")})
        out.sort(key=lambda r: r.get("generated_at") or "", reverse=True)
        return out

    def _handle_api(self, parts):
        if len(parts) < 2:
            return self._send_json(404, {"error": "Not found."})
        if parts[1] == "symbols":
            return self._handle_symbols()
        if parts[1] == "runs":
            return self._handle_runs(parts[2:])
        if parts[1] == "optimizer":
            return self._handle_optimizer(parts[2:])
        return self._send_json(404, {"error": "Not found."})

    def _handle_symbols(self):
        try:
            bt = _get_backtest()
            return self._send_json(
                200,
                {
                    "symbols": bt["symbols"],
                    "count": len(bt["symbols"]),
                    "min_selected": MIN_FIXED_SYMBOLS,
                    "max_selected": MAX_FIXED_SYMBOLS,
                    "min_allocations": MIN_ALLOCATIONS,
                    "max_allocations": MAX_ALLOCATIONS,
                    "selection_policy": "joint_or_user_fixed",
                    "default_strategic_min_equity_exposure": 0.0,
                    "risk_missing_data_exposure": 0.0,
                },
            )
        except Exception as exc:
            return self._send_json(500, {"error": f"Could not load symbols: {exc}"})

    def _handle_combination_health(self, body: dict):
        symbols = _normalise_symbols(body.get("symbols"))
        if len(set(symbols)) != len(symbols):
            return self._send_json(400, {"error": "Combination contains duplicate symbols."})
        if not (MIN_FIXED_SYMBOLS <= len(symbols) <= MAX_FIXED_SYMBOLS):
            return self._send_json(400, {"error": f"Select {MIN_FIXED_SYMBOLS}–{MAX_FIXED_SYMBOLS} symbols before analysis."})
        try:
            bt = _get_backtest()
            unknown = [s for s in symbols if s not in set(bt["symbols"])]
            if unknown:
                return self._send_json(400, {"error": f"Symbols not in loaded data: {unknown}"})
            from backtest.combination_health import analyze_combination_health
            result = analyze_combination_health(
                bt["prices"],
                symbols,
                params=bt["params"],
                available_symbols=bt["symbols"],
                holdout_days=252,
                include_suggestions=bool(body.get("include_suggestions", True)),
                suggestion_limit=min(10, max(0, int(body.get("suggestion_limit", 5)))),
            )
        except Exception as exc:
            return self._send_json(500, {"error": f"Combination analysis failed: {exc}"})
        return self._send_json(200, result)

    def _handle_runs(self, parts):
        if not parts:
            return self._send_json(200, {"runs": self._runs()})
        rid = parts[0]
        base = self._safe_join(RESULTS_DIR, "runs", rid)
        if not base or not os.path.isdir(base):
            return self._send_json(404, {"error": f"Run not found: {rid}"})
        if len(parts) == 1:
            return self._send_json(200, {"run_id": rid, "meta": self._read_json(base, "meta.json")})
        if len(parts) == 2:
            if parts[1] == "export":
                return self._handle_export(rid, base)
            if parts[1] == "meta":
                data = self._read_json(base, "meta.json")
                return self._send_json(200, data if data is not None else {"error": "No meta"})
            if parts[1] == "index":
                data = self._read_json(base, "index.json")
                return self._send_json(200, data if data is not None else {"error": "No index"})
        if len(parts) == 3 and parts[1] == "combinations":
            slug = parts[2]
            combo = self._read_json(os.path.join(base, "combinations"), f"{slug}.json")
            if combo is None:
                return self._send_json(404, {"error": f"Combination not found: {slug}"})
            return self._send_json(200, combo)
        return self._send_json(404, {"error": "Not found."})

    def _handle_export(self, rid, base):
        try:
            import export
            data = export.build_zip(rid)
        except Exception as exc:
            return self._send_json(500, {"error": f"Export failed: {exc}"})
        self.send_response(200)
        self.send_header("Content-Type", "application/zip")
        self.send_header("Content-Disposition", f'attachment; filename="{rid}_export.zip"')
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self._write_body(data)

    def _handle_delete_run(self, rid):
        base = self._safe_join(RESULTS_DIR, "runs", rid)
        if not base or not os.path.isdir(base):
            return self._send_json(404, {"error": f"Run not found: {rid}"})
        shutil.rmtree(base, ignore_errors=True)
        exp = self._safe_join(RESULTS_DIR, "export", rid)
        if exp and os.path.isdir(exp):
            shutil.rmtree(exp, ignore_errors=True)
        return self._send_json(200, {"ok": True, "run_id": rid})

    def _list_optimizer_experiments(self):
        if not os.path.isdir(OPTIMIZER_DIR):
            return []
        out = []
        for eid in os.listdir(OPTIMIZER_DIR):
            base = os.path.join(OPTIMIZER_DIR, eid)
            cfg = os.path.join(base, "optimizer_config.json")
            if not os.path.isfile(cfg):
                continue
            try:
                with open(cfg, "r", encoding="utf-8") as fh:
                    meta = json.load(fh)
            except Exception:
                meta = {}
            out.append({
                "experiment_id": eid,
                "generated_at": meta.get("generated_at"),
                "fixed_symbols": meta.get("fixed_symbols") or [],
                "mode": meta.get("mode"),
                "portfolio_size": meta.get("portfolio_size"),
            })
        out.sort(key=lambda e: e.get("generated_at") or "", reverse=True)
        return out

    def _handle_optimizer(self, parts):
        if not parts:
            return self._send_json(200, {"experiments": self._list_optimizer_experiments()})
        if parts == ["status"]:
            return self._handle_optimizer_status()
        eid = parts[0]
        base = self._safe_join(OPTIMIZER_DIR, eid)
        if not base or not os.path.isdir(base):
            return self._send_json(404, {"error": f"Optimizer experiment not found: {eid}"})
        if len(parts) == 1:
            exp_path = os.path.join(base, "experiment.json")
            if os.path.isfile(exp_path):
                with open(exp_path, "r", encoding="utf-8") as fh:
                    return self._send_json(200, json.load(fh))
            return self._send_json(404, {"error": f"No experiment.json for {eid}."})
        if len(parts) == 2 and parts[1] == "file":
            params = dict(parse_qsl(urlparse(self.path).query))
            name = params.get("name", "")
            target = self._safe_join(base, name) if name else None
            if target and os.path.isfile(target):
                return self._send_file(target)
            return self._send_json(404, {"error": "File not found."})
        if len(parts) == 2 and parts[1] == "download":
            return self._handle_optimizer_download(eid)
        if len(parts) == 2 and parts[1] == "candidate":
            return self._handle_optimizer_candidate(eid)
        if len(parts) == 2 and parts[1] == "recommendation":
            return self._handle_optimizer_recommendation(eid)
        return self._send_json(404, {"error": "Not found."})

    def _handle_optimizer_download(self, eid):
        base = self._safe_join(OPTIMIZER_DIR, eid)
        if not base or not os.path.isdir(base):
            return self._send_json(404, {"error": f"Optimizer experiment not found: {eid}"})
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
            for root, _dirs, names in os.walk(base):
                for name in names:
                    full = os.path.join(root, name)
                    zf.write(full, os.path.relpath(full, base))
        data = buf.getvalue()
        self.send_response(200)
        self.send_header("Content-Type", "application/zip")
        self.send_header("Content-Disposition", f'attachment; filename="{eid}_all_data.zip"')
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self._write_body(data)

    def _handle_optimizer_recommendation(self, eid):
        base = self._safe_join(OPTIMIZER_DIR, eid)
        if not base or not os.path.isdir(base):
            return self._send_json(404, {"error": f"Optimizer experiment not found: {eid}"})
        exp_path = os.path.join(base, "experiment.json")
        if not os.path.isfile(exp_path):
            return self._send_json(404, {"error": "experiment.json not found."})
        try:
            from backtest.recommendation import build_recommendation
            with open(exp_path, "r", encoding="utf-8") as fh:
                experiment = json.load(fh)
            rec = build_recommendation(experiment)
        except Exception as exc:
            return self._send_json(500, {"error": str(exc)})
        return self._send_json(200, rec)

    def _handle_optimizer_candidate(self, eid):
        """Backtest one candidate with the experiment's exact configuration."""
        query = dict(parse_qsl(urlparse(self.path).query))
        symbols = _normalise_symbols(query.get("symbols", ""))
        try:
            days = sorted({int(x) for x in query.get("days", "").split(",") if x.strip()})
        except ValueError:
            days = []
        if not (MIN_FIXED_SYMBOLS <= len(symbols) <= MAX_FIXED_SYMBOLS) or not (MIN_ALLOCATIONS <= len(days) <= MAX_ALLOCATIONS):
            return self._send_json(
                400,
                {"error": f"Need {MIN_FIXED_SYMBOLS}–{MAX_FIXED_SYMBOLS} symbols and {MIN_ALLOCATIONS}–{MAX_ALLOCATIONS} allocation days."},
            )
        bt = _get_backtest()
        exp_meta = self._read_json(os.path.join(OPTIMIZER_DIR, eid), "optimizer_config.json") or {}
        risk_cfg = exp_meta.get("risk_config") or {}
        cost_cfg = exp_meta.get("cost_config") or {}
        capital_cfg = exp_meta.get("capital_config") or {}
        allowed = set(bt["params"].as_dict())
        overrides = {k: v for k, v in {**risk_cfg, **cost_cfg, **capital_cfg}.items() if k in allowed}
        run_params = replace(bt["params"], **overrides)
        candidate = bt["Candidate"](tuple(sorted(symbols)), tuple(days))
        alloc_dates, init_date = bt["allocation_dates_with_initialization"](
            candidate,
            bt["prices"],
            run_params,
            bt["dates"],
            (None, None),
            run_params.lookback_days,
        )
        result = bt["simulate_combination"](
            symbols,
            bt["prices"],
            run_params,
            allocation_dates=alloc_dates,
        )
        if result.error:
            return self._send_json(500, {"error": result.error})
        init_text = str(init_date.date()) if init_date is not None else None
        for record in result.allocations:
            if init_text and record.get("allocation_date") == init_text:
                record["allocation_role"] = "INITIAL_DEPLOYMENT"
            else:
                record.setdefault("allocation_role", "SCHEDULED_RECALIBRATION")
        metrics = bt["result_metrics"](result)
        metrics["initial_deployment_date"] = init_text
        payload = {
            "symbols": list(result.symbols),
            "allocation_days": days,
            "allocation_count": len(days),
            "initial_deployment_date": init_text,
            "metrics": metrics,
            "nav_history": result.nav_history,
            "allocations": result.allocations,
            "capital_events": result.capital_events,
            "deployment_events": result.deployment_events,
            "capital_config": capital_cfg,
        }
        return self._send_json(200, payload)

    def _handle_optimizer_run(self, body: dict):
        """Run joint growth search or timing search for a user-owned combination."""
        requested_mode = str(body.get("mode", "joint")).lower()
        if requested_mode not in {"joint", "timing"}:
            return self._send_json(400, {"error": "mode must be 'joint' or 'timing'."})

        universe = str(body.get("universe", "all")).lower()
        if universe not in VALID_UNIVERSES:
            return self._send_json(400, {"error": f"universe must be one of {sorted(VALID_UNIVERSES)}"})

        fixed_symbols = None
        health = None
        if requested_mode == "timing":
            fixed_symbols = _normalise_symbols(body.get("fixed_symbols"))
            if len(set(fixed_symbols)) != len(fixed_symbols):
                return self._send_json(400, {"error": "fixed_symbols contains duplicates."})
            if not (MIN_FIXED_SYMBOLS <= len(fixed_symbols) <= MAX_FIXED_SYMBOLS):
                return self._send_json(400, {"error": f"Select {MIN_FIXED_SYMBOLS}–{MAX_FIXED_SYMBOLS} fixed symbols."})
            try:
                bt = _get_backtest()
                available = set(bt["symbols"])
                unknown = [s for s in fixed_symbols if s not in available]
                if unknown:
                    return self._send_json(400, {"error": f"Symbols not in loaded data: {unknown}"})
                from backtest.combination_health import analyze_combination_health
                health = analyze_combination_health(
                    bt["prices"], fixed_symbols, params=bt["params"],
                    available_symbols=bt["symbols"], holdout_days=252,
                    include_suggestions=False,
                )
            except Exception as exc:
                return self._send_json(400, {"error": f"Combination health check failed: {exc}"})
            if health.get("status") == "invalid":
                return self._send_json(400, {"error": "Combination is INVALID and cannot be optimized.", "health": health})
            portfolio_size = len(fixed_symbols)
        else:
            portfolio_size = int(body.get("portfolio_size", 7))
            if not (MIN_FIXED_SYMBOLS <= portfolio_size <= MAX_FIXED_SYMBOLS):
                return self._send_json(400, {"error": f"portfolio_size must be {MIN_FIXED_SYMBOLS}–{MAX_FIXED_SYMBOLS}."})

        seed = int(body.get("seed", 42))
        population = max(10, int(body.get("population", 60 if requested_mode == "joint" else 36)))
        generations = max(1, int(body.get("generations", 30 if requested_mode == "joint" else 18)))
        random_n = max(20, int(body.get("random", 250 if requested_mode == "joint" else 80)))
        finalists = max(1, int(body.get("finalists", 5)))
        robust_pool_size = max(finalists, int(body.get("robust_pool_size", 180 if requested_mode == "joint" else 50)))
        surrogate_pool_size = max(0, int(body.get("surrogate_pool_size", 5000 if requested_mode == "joint" else 1500)))
        surrogate_proposals = max(0, int(body.get("surrogate_proposals", 40 if requested_mode == "joint" else 16)))
        early_stop_generations = int(body.get("early_stop_generations", 15 if requested_mode == "joint" else 8))
        parallel_workers = max(0, int(body.get("parallel_workers", 0)))
        preselect_top = int(body.get("preselect_top", 45)) if requested_mode == "joint" else None

        initial_balance = float(body.get("initial_balance", 1_000_000_000))
        annual_deposit = float(body.get("annual_deposit", 20_000_000))
        risk_overlay = bool(body.get("risk_overlay", True))
        target_volatility = float(body.get("target_volatility", 0.18))
        max_oos_drawdown_pct = float(body.get("max_oos_drawdown_pct", 35.0))
        max_position_weight = float(body.get("max_position_weight", 0.30))
        min_equity_exposure = float(body.get("min_equity_exposure", 0.0))

        if initial_balance <= 0:
            return self._send_json(400, {"error": "initial_balance must be > 0."})
        if annual_deposit < 0:
            return self._send_json(400, {"error": "annual_deposit must be >= 0."})
        if target_volatility <= 0 or target_volatility > 1:
            return self._send_json(400, {"error": "target_volatility must be in (0, 1]."})
        if not (0 <= min_equity_exposure <= 1):
            return self._send_json(400, {"error": "min_equity_exposure must be 0..1."})
        if not (0 < max_position_weight <= 1):
            return self._send_json(400, {"error": "max_position_weight must be in (0, 1]."})
        min_feasible = 1.0 / portfolio_size
        if risk_overlay and max_position_weight + 1e-12 < min_feasible:
            return self._send_json(
                400,
                {"error": f"With {portfolio_size} symbols, max_position_weight cannot be below {min_feasible:.4f}."},
            )

        mode = requested_mode
        started = datetime.now().isoformat(timespec="seconds")
        run_id = f"run_{int(time.time())}"
        frozen_symbols = sorted(fixed_symbols) if fixed_symbols else None

        with _optimizer_lock:
            _optimizer_runs[run_id] = {
                "status": "running",
                "started_at": started,
                "universe": universe,
                "mode": mode,
                "fixed_symbols": frozen_symbols,
                "portfolio_size": portfolio_size,
                "risk_overlay": risk_overlay,
                "initial_balance": initial_balance,
                "annual_deposit": annual_deposit,
                "strategic_min_equity_exposure": min_equity_exposure,
                "risk_missing_data_exposure": 0.0,
                "allocation_search": f"{MIN_ALLOCATIONS}-{MAX_ALLOCATIONS} recalibrations/year",
                "combination_health_status": health.get("status") if health else None,
                "combination_health_score": (health.get("score") or {}).get("overall") if health else None,
            }

        def work():
            try:
                from backtest.optimize import run_optimizer, OptimizerConfig
                from backtest import BacktestParams

                params = BacktestParams(
                    universe=universe,
                    portfolio_size=None,
                    initial_balance=initial_balance,
                    annual_deposit=annual_deposit,
                    risk_overlay_enabled=risk_overlay,
                    target_volatility=target_volatility,
                    min_equity_exposure=min_equity_exposure,
                    risk_missing_data_exposure=0.0,
                    max_position_weight=max_position_weight,
                )
                opt = OptimizerConfig(
                    seed=seed,
                    population_size=population,
                    generations=generations,
                    n_random=random_n,
                    n_finalists=finalists,
                    mode=mode,
                    fixed_symbols=frozen_symbols,
                    portfolio_size=None if mode == "timing" else portfolio_size,
                    preselect_top=preselect_top,
                    robust_pool_size=robust_pool_size,
                    surrogate_pool_size=surrogate_pool_size,
                    surrogate_proposals=surrogate_proposals,
                    early_stop_generations=early_stop_generations if early_stop_generations > 0 else None,
                    parallel_workers=parallel_workers,
                    max_oos_drawdown_pct=max_oos_drawdown_pct if max_oos_drawdown_pct > 0 else None,
                )
                res = run_optimizer(params, opt, progress=False)
                with _optimizer_lock:
                    _optimizer_runs[run_id] = {
                        "status": "done",
                        "experiment_id": res["experiment_id"],
                        "out_dir": res["out_dir"],
                        "started_at": started,
                        "finished_at": datetime.now().isoformat(timespec="seconds"),
                        "mode": mode,
                        "fixed_symbols": frozen_symbols,
                        "portfolio_size": portfolio_size,
                    }
            except Exception as exc:
                with _optimizer_lock:
                    _optimizer_runs[run_id] = {
                        "status": "failed",
                        "error": str(exc),
                        "started_at": started,
                        "mode": mode,
                        "fixed_symbols": frozen_symbols,
                        "portfolio_size": portfolio_size,
                    }

        threading.Thread(target=work, daemon=True).start()
        return self._send_json(
            202,
            {
                "run_id": run_id,
                "status": "running",
                "started_at": started,
                "universe": universe,
                "mode": mode,
                "fixed_symbols": frozen_symbols,
                "portfolio_size": portfolio_size,
                "initial_balance": initial_balance,
                "annual_deposit": annual_deposit,
                "strategic_min_equity_exposure": min_equity_exposure,
                "risk_missing_data_exposure": 0.0,
                "allocation_search": {"min": MIN_ALLOCATIONS, "max": MAX_ALLOCATIONS},
            },
        )

    def _handle_optimizer_status(self):
        with _optimizer_lock:
            runs = [dict(v, run_id=k) for k, v in _optimizer_runs.items()]
        return self._send_json(200, {"runs": runs})

    def _handle_page(self, parts):
        try:
            if not parts:
                return self._send_page("home", {"runs": self._runs()}, "Shannon / ERC Backtest")
            if parts[0] == "optimizer":
                if len(parts) == 1:
                    return self._send_page(
                        "optimizer_list",
                        {"experiments": self._list_optimizer_experiments()},
                        "Growth Optimizer · Shannon/ERC",
                    )
                eid = parts[1]
                base = self._safe_join(OPTIMIZER_DIR, eid)
                exp = None
                if base and os.path.isfile(os.path.join(base, "experiment.json")):
                    with open(os.path.join(base, "experiment.json"), "r", encoding="utf-8") as fh:
                        exp = json.load(fh)
                if exp is None:
                    return self._send_json(404, {"error": f"Experiment not found: {eid}"})
                return self._send_page("optimizer_detail", {"experiment": exp}, f"Optimizer {eid}")
            rid = parts[0]
            base = self._safe_join(RESULTS_DIR, "runs", rid)
            if not base or not os.path.isdir(base):
                return self._send_json(404, {"error": f"Run not found: {rid}"})
            if len(parts) == 1:
                meta = self._read_json(base, "meta.json")
                index = self._read_json(base, "index.json")
                if not index:
                    return self._send_json(404, {"error": "Run has no ranking data."})
                return self._send_page("run", {"meta": meta, "index": index}, f"Run {rid} · Shannon/ERC")
            if len(parts) >= 3 and parts[1] == "combinations":
                slug = parts[2]
                combo = self._read_json(os.path.join(base, "combinations"), f"{slug}.json")
                if combo is None:
                    return self._send_json(404, {"error": f"Combination not found: {slug}"})
                title = " ".join(combo.get("symbols", [])) or slug
                return self._send_page("combo", {"combo": combo, "runId": rid}, f"{title} · Shannon/ERC")
            return self._send_json(404, {"error": "Not found."})
        except Exception as exc:
            return self._send_json(500, {"error": f"SSR failed: {exc}"})

    def _send_page(self, page, props, title):
        body = _build_document(page, props, title)
        self._send_bytes(200, body, "text/html; charset=utf-8")

    def do_GET(self):
        path = urlparse(self.path).path
        if path.startswith("/api/"):
            return self._handle_api([unquote(p) for p in path.split("/") if p])
        if path.startswith("/assets/"):
            target = self._safe_join(DIST_DIR, path.lstrip("/"))
            if target and os.path.isfile(target):
                return self._send_file(target)
            return self._send_json(404, {"error": "Asset not found."})
        if path == "/" or path == "":
            return self._handle_page([])
        if path == "/optimizer" or path.startswith("/optimizer/"):
            return self._handle_page([unquote(p) for p in path.split("/") if p])
        if path.startswith("/runs/"):
            parts = [unquote(p) for p in path.split("/") if p]
            return self._handle_page(parts[1:])
        return self._send_json(404, {"error": "Not found."})

    do_HEAD = do_GET

    def do_DELETE(self):
        path = urlparse(self.path).path
        if path.startswith("/api/runs/"):
            parts = [unquote(p) for p in path.split("/") if p]
            if len(parts) == 3:
                return self._handle_delete_run(parts[2])
        if path.startswith("/api/optimizer/"):
            parts = [unquote(p) for p in path.split("/") if p]
            if len(parts) == 3:
                return self._handle_delete_optimizer(parts[2])
        return self._send_json(404, {"error": "Not found."})

    def _handle_delete_optimizer(self, eid):
        base = self._safe_join(OPTIMIZER_DIR, eid)
        if not base or not os.path.isdir(base):
            return self._send_json(404, {"error": f"Optimizer experiment not found: {eid}"})
        shutil.rmtree(base, ignore_errors=True)
        return self._send_json(200, {"ok": True, "experiment_id": eid})

    def do_POST(self):
        path = urlparse(self.path).path
        length = int(self.headers.get("Content-Length", 0) or 0)
        raw = self.rfile.read(length) if length else b"{}"
        try:
            body = json.loads(raw.decode("utf-8") or "{}")
        except Exception:
            body = {}
        if path == "/api/combination/health":
            return self._handle_combination_health(body)
        if path == "/api/optimizer/run":
            return self._handle_optimizer_run(body)
        return self._send_json(404, {"error": "Not found."})


def _bind_with_fallback(host, port, handler, attempts=20):
    for offset in range(attempts):
        candidate = port + offset
        try:
            return candidate, ThreadingHTTPServer((host, candidate), handler)
        except OSError as exc:
            if candidate == port:
                print(f"Port {port} unavailable ({exc.__class__.__name__}): {exc}", flush=True)
            continue
    raise SystemExit(f"Could not bind to any port from {port} to {port + attempts - 1}.")


def main():
    ap = argparse.ArgumentParser(description="Serve SSR frontend + growth-first joint allocation optimizer")
    ap.add_argument("--port", type=int, default=8080)
    ap.add_argument("--host", default="127.0.0.1")
    args = ap.parse_args()

    _ensure_ssr_worker()
    print(f"SSR renderer : {SSR_URL}", flush=True)
    print(f"Results dir  : {RESULTS_DIR}", flush=True)

    port, server = _bind_with_fallback(args.host, args.port, Handler)
    print(f"Open http://{args.host}:{port}", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down.")
    finally:
        if _ssr_proc:
            _ssr_proc.terminate()


if __name__ == "__main__":
    main()
