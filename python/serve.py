#!/usr/bin/env python3
"""Serve the SSR frontend (Python backend + React SSR via a Node renderer) + the run data API.

Pages (server-rendered HTML, React hydrates on the client):
    GET /                                          -> home (list of runs)
    GET /runs/<run_id>                             -> ranking board for a run
    GET /runs/<run_id>/combinations/<slug>         -> combination detail

JSON API:
    GET /api/runs
    GET /api/runs/<run_id>/meta
    GET /api/runs/<run_id>/index
    GET /api/runs/<run_id>/combinations/<slug>

React SSR is done by a small Node worker (frontend/ssr/server.mjs, port 8099) which
renders the shared React components to HTML via react-dom/server. The Python server
spawns it automatically if it is not already running.

Build the frontend first:
    cd frontend && npm run build && npm run build:ssr

Run:
    python serve.py [--port 8080]
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import threading
import time
import urllib.request
from datetime import datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import unquote, urlparse, parse_qsl

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # .../shannon_allocation
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

_css_url = None

# Lazy-loaded backtest engine (price panel loaded once).
_backtest_ctx = None
_optimizer_runs: dict = {}
_optimizer_lock = threading.Lock()


def _get_backtest():
    global _backtest_ctx
    if _backtest_ctx is None:
        from backtest import BacktestParams, load_panel
        from backtest.candidate import Candidate, schedule_for_window
        from backtest.simulation import simulate_combination
        from backtest.optimize.evaluate import result_metrics

        params = BacktestParams()  # default costs/lookahead + F:/data_finance/data
        prices, _ = load_panel(params)
        _backtest_ctx = {
            "params": params,
            "prices": prices,
            "dates": list(prices.index),
            "Candidate": Candidate,
            "schedule_for_window": schedule_for_window,
            "simulate_combination": simulate_combination,
            "result_metrics": result_metrics,
        }
    return _backtest_ctx


def _client_css_url() -> str:
    """Discover the emitted CSS asset (named after the entry chunk)."""
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


# --------------------------------------------------------------------------- SSR worker
def _ssr_health() -> bool:
    try:
        with urllib.request.urlopen(f"{SSR_URL}/health", timeout=1.5):
            return True
    except Exception:
        return False


def _ensure_ssr_worker() -> None:
    global _ssr_proc
    if _ssr_health():
        return
    if not os.path.isfile(os.path.join(FRONTEND_DIR, "dist-ssr", "ssr-entry.mjs")):
        raise RuntimeError(
            "SSR bundle not built. Run: cd frontend && npm run build && npm run build:ssr"
        )
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
    # Wait for the worker to come up.
    for _ in range(50):
        if _ssr_health():
            return
        import time

        time.sleep(0.1)
    raise RuntimeError("Node SSR worker failed to start.")


def _ssr_render(page: str, props: dict) -> str:
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


# --------------------------------------------------------------------------- data helpers
class Handler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def log_message(self, fmt, *args):  # quieter
        pass

    def _send_json(self, status, payload):
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def _send_bytes(self, status, body, content_type):
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

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

    # --------------------------------------------------------------------- API
    def _handle_api(self, parts):
        if not parts:
            return self._send_json(404, {"error": "Not found."})
        if parts[1] == "runs":
            return self._handle_runs(parts[2:])
        if parts[1] == "optimizer":
            return self._handle_optimizer(parts[2:])
        return self._send_json(404, {"error": "Not found."})

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
        self.wfile.write(data)

    def _handle_delete_run(self, rid):
        base = self._safe_join(RESULTS_DIR, "runs", rid)
        if not base or not os.path.isdir(base):
            return self._send_json(404, {"error": f"Run not found: {rid}"})
        shutil.rmtree(base, ignore_errors=True)
        exp = self._safe_join(RESULTS_DIR, "export", rid)
        if exp and os.path.isdir(exp):
            shutil.rmtree(exp, ignore_errors=True)
        return self._send_json(200, {"ok": True, "run_id": rid})

    # --------------------------------------------------------------------- optimizer
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
            out.append({"experiment_id": eid, "generated_at": meta.get("generated_at")})
        out.sort(key=lambda e: e.get("generated_at") or "", reverse=True)
        return out

    def _handle_optimizer(self, parts):
        # parts[0] == 'optimizer' is already stripped; parts = [eid] or [eid, 'file'] or ['status']
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
            return self._send_json(404, {"error": f"No experiment.json for {eid} (re-run the optimizer)."})
        if len(parts) == 2 and parts[1] == "file":
            params = dict(parse_qsl(urlparse(self.path).query))
            name = params.get("name", "")
            target = self._safe_join(base, name) if name else None
            if target and os.path.isfile(target):
                return self._send_file(target)
            return self._send_json(404, {"error": "File not found."})
        if len(parts) == 2 and parts[1] == "candidate":
            return self._handle_optimizer_candidate(eid)
        return self._send_json(404, {"error": "Not found."})

    def _handle_optimizer_candidate(self, eid):
        """Backtest one candidate on-demand and return its full allocation history."""
        params = dict(parse_qsl(urlparse(self.path).query))
        symbols = [s.strip().upper() for s in params.get("symbols", "").split(",") if s.strip()]
        days = [int(x) for x in params.get("days", "").split(",") if x.strip()]
        if len(symbols) < 5 or len(days) != 4:
            return self._send_json(400, {"error": "Need symbols (>=5) and exactly 4 allocation days."})
        bt = _get_backtest()
        alloc_dates = bt["schedule_for_window"](bt["Candidate"](tuple(sorted(symbols)), tuple(days)), bt["dates"])
        result = bt["simulate_combination"](symbols, bt["prices"], bt["params"], allocation_dates=alloc_dates)
        if result.error:
            return self._send_json(500, {"error": result.error})
        payload = {
            "symbols": list(result.symbols),
            "allocation_days": sorted(days),
            "metrics": bt["result_metrics"](result),
            "nav_history": result.nav_history,
            "allocations": result.allocations,
        }
        return self._send_json(200, payload)

    def _handle_optimizer_run(self, body: dict):
        """Start an optimizer run in a background thread; returns immediately."""
        seed = int(body.get("seed", 42))
        population = int(body.get("population", 30))
        generations = int(body.get("generations", 15))
        random_n = int(body.get("random", 150))
        finalists = int(body.get("finalists", 5))
        run_id = f"run_{int(time.time())}"
        started = datetime.now().isoformat(timespec="seconds")
        with _optimizer_lock:
            _optimizer_runs[run_id] = {"status": "running", "started_at": started}

        def work():
            try:
                from backtest.optimize import run_optimizer, OptimizerConfig
                from backtest import BacktestParams

                params = BacktestParams()
                opt = OptimizerConfig(seed=seed, population_size=population, generations=generations,
                                      n_random=random_n, n_finalists=finalists)
                res = run_optimizer(params, opt, progress=False)
                with _optimizer_lock:
                    _optimizer_runs[run_id] = {
                        "status": "done",
                        "experiment_id": res["experiment_id"],
                        "out_dir": res["out_dir"],
                        "started_at": started,
                        "finished_at": datetime.now().isoformat(timespec="seconds"),
                    }
            except Exception as exc:
                with _optimizer_lock:
                    _optimizer_runs[run_id] = {"status": "failed", "error": str(exc), "started_at": started}

        threading.Thread(target=work, daemon=True).start()
        return self._send_json(202, {"run_id": run_id, "status": "running", "started_at": started})

    def _handle_optimizer_status(self):
        with _optimizer_lock:
            runs = [dict(v, run_id=k) for k, v in _optimizer_runs.items()]
        return self._send_json(200, {"runs": runs})

    # --------------------------------------------------------------------- pages
    def _handle_page(self, parts):
        # parts[0] is 'runs' for run/combo pages, empty for home
        try:
            if not parts:
                return self._send_page("home", {"runs": self._runs()}, "Shannon / ERC Backtest")
            if parts[0] == "optimizer":
                if len(parts) == 1:
                    return self._send_page("optimizer_list",
                                           {"experiments": self._list_optimizer_experiments()},
                                           "Optimizer · Shannon/ERC")
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
        except Exception as exc:  # SSR worker errors
            return self._send_json(500, {"error": f"SSR failed: {exc}"})

    def _send_page(self, page, props, title):
        body = _build_document(page, props, title)
        self._send_bytes(200, body, "text/html; charset=utf-8")

    # --------------------------------------------------------------------- entry
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
            parts = [unquote(p) for p in path.split("/") if p]
            return self._handle_page(parts)
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
        if path == "/api/optimizer/run":
            return self._handle_optimizer_run(body)
        return self._send_json(404, {"error": "Not found."})


# --------------------------------------------------------------------------- entry
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
    ap = argparse.ArgumentParser(description="Serve SSR frontend + run data")
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