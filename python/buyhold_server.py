#!/usr/bin/env python3
"""Standalone QPort Buy & Hold institutional-lite portfolio web application."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import unquote, urlparse

from portfolio.correctable_service import CorrectablePortfolioService
from portfolio.locale import resolve_locale
from portfolio.scheduler import DailySyncScheduler
from portfolio.validation import InputValidationError

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FRONTEND_DIR = os.path.join(REPO, "frontend")
DIST_DIR = os.path.join(FRONTEND_DIR, "dist")
SSR_HOST = "127.0.0.1"
SSR_PORT = int(os.environ.get("SSR_PORT", "8099"))
SSR_URL = f"http://{SSR_HOST}:{SSR_PORT}"
NODE_SSR = os.path.join(FRONTEND_DIR, "ssr", "server.mjs")
CLIENT_JS = "/assets/client.js"
CLIENT_CSS_DEFAULT = "/assets/entry-client.css"
MIME = {
    ".html": "text/html; charset=utf-8",
    ".js": "application/javascript; charset=utf-8",
    ".mjs": "application/javascript; charset=utf-8",
    ".css": "text/css; charset=utf-8",
    ".json": "application/json; charset=utf-8",
    ".png": "image/png", ".svg": "image/svg+xml", ".ico": "image/x-icon",
}

_css_url = None
_ssr_proc: subprocess.Popen | None = None
_service: CorrectablePortfolioService | None = None


def _portfolio() -> CorrectablePortfolioService:
    global _service
    if _service is None:
        _service = CorrectablePortfolioService()
    return _service


def _client_css_url() -> str:
    global _css_url
    if _css_url is None:
        assets = os.path.join(DIST_DIR, "assets")
        if os.path.isdir(assets):
            for name in sorted(os.listdir(assets)):
                if name.endswith(".css"):
                    _css_url = f"/assets/{name}"
                    break
        _css_url = _css_url or CLIENT_CSS_DEFAULT
    return _css_url


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
        raise RuntimeError("SSR bundle not built. Run: cd frontend && npm run build && npm run build:ssr")
    if not os.path.isfile(os.path.join(DIST_DIR, "assets", "client.js")):
        raise RuntimeError("Client bundle not built. Run: cd frontend && npm run build")
    env = dict(os.environ, SSR_PORT=str(SSR_PORT), SSR_HOST=SSR_HOST)
    _ssr_proc = subprocess.Popen(["node", NODE_SSR], cwd=FRONTEND_DIR, env=env, stdout=sys.stdout, stderr=sys.stderr)
    for _ in range(50):
        if _ssr_health():
            return
        time.sleep(0.1)
    raise RuntimeError("Node SSR worker failed to start.")


def _ssr_render(page: str, props: dict) -> str:
    body = json.dumps({"page": page, "props": props}).encode("utf-8")
    req = urllib.request.Request(f"{SSR_URL}/render", data=body, headers={"Content-Type": "application/json"}, method="POST")
    with urllib.request.urlopen(req, timeout=10) as resp:
        return json.loads(resp.read().decode("utf-8"))["html"]


def _build_document(page: str, props: dict, title: str) -> bytes:
    html = _ssr_render(page, props)
    serialized = json.dumps({"page": page, "props": props}, ensure_ascii=False).replace("<", "\\u003c")
    lang = "vi" if props.get("locale") == "vi" else "en"
    return (
        f"<!doctype html>\n<html lang='{lang}'><head><meta charset='utf-8'>"
        "<meta name='viewport' content='width=device-width, initial-scale=1'>"
        f"<title>{title}</title><link rel='stylesheet' href='{_client_css_url()}'>"
        f"</head><body><div id='root'>{html}</div><script>window.__PAGE__={serialized};</script>"
        f"<script type='module' crossorigin src='{CLIENT_JS}'></script></body></html>"
    ).encode("utf-8")


def _bind_with_fallback(host, port, handler, attempts=20):
    for offset in range(attempts):
        candidate = port + offset
        try:
            return candidate, ThreadingHTTPServer((host, candidate), handler)
        except OSError as exc:
            if candidate == port:
                print(f"Port {port} unavailable ({exc.__class__.__name__}): {exc}", flush=True)
    raise SystemExit(f"Could not bind to any port from {port} to {port + attempts - 1}.")


class Handler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def log_message(self, fmt, *args):
        pass

    @staticmethod
    def _parts(path: str) -> list[str]:
        return [unquote(p) for p in path.split("/") if p]

    def _locale(self) -> str:
        return resolve_locale(cookie_header=self.headers.get("Cookie"), accept_language=self.headers.get("Accept-Language"))

    def _title(self, en: str, vi: str) -> str:
        return vi if self._locale() == "vi" else en

    def _write_body(self, body):
        try:
            self.wfile.write(body); self.wfile.flush()
        except (BrokenPipeError, ConnectionAbortedError, ConnectionResetError, OSError):
            return

    def _send_json(self, status, payload):
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status); self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body))); self.send_header("Cache-Control", "no-store")
        self.end_headers(); self._write_body(body)

    def _send_bytes(self, status, body, content_type):
        self.send_response(status); self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body))); self.end_headers(); self._write_body(body)

    def _safe_join(self, base, *parts):
        target, root = os.path.realpath(os.path.join(base, *parts)), os.path.realpath(base)
        return target if target == root or target.startswith(root + os.sep) else None

    def _send_file(self, path):
        try:
            with open(path, "rb") as fh: body = fh.read()
        except FileNotFoundError:
            return self._send_json(404, {"error": "Not found."})
        self._send_bytes(200, body, MIME.get(os.path.splitext(path)[1].lower(), "application/octet-stream"))

    def _send_page(self, page, props, title):
        props = {**(props or {}), "locale": self._locale()}
        self._send_bytes(200, _build_document(page, props, title), "text/html; charset=utf-8")

    def _read_body_json(self):
        length = int(self.headers.get("Content-Length", 0) or 0)
        raw = self.rfile.read(length) if length else b"{}"
        try: return json.loads(raw.decode("utf-8") or "{}")
        except Exception: return {}

    @staticmethod
    def _transaction_id(path: str) -> int | None:
        parts = Handler._parts(path)
        if len(parts) == 4 and parts[:3] == ["api", "portfolio", "transactions"]:
            try: return int(parts[3])
            except ValueError: return None
        return None

    def _api_get(self, parts):
        svc = _portfolio()
        routes = {
            (): lambda: svc.dashboard(),
            ("transactions",): lambda: {"transactions": svc.transactions()},
            ("transaction-audit",): lambda: {"corrections": svc.transaction_audit()},
            ("performance",): svc.performance,
            ("risk",): svc.risk,
            ("snapshots",): lambda: {"snapshots": svc.snapshots()},
            ("market",): lambda: svc.dashboard().get("market_data") or {},
            ("preferences",): svc.preferences,
            ("operations",): svc.institutional_overview,
        }
        fn = routes.get(tuple(parts))
        return self._send_json(200, fn()) if fn else self._send_json(404, {"error": "Portfolio endpoint not found."})

    def _page(self, page):
        svc = _portfolio()
        configs = {
            "portfolio": ({"dashboard": svc.dashboard()}, self._title("Portfolio · QPort", "Danh mục · QPort")),
            "transactions": ({"transactions": svc.transactions(), "corrections": svc.transaction_audit(), "today": svc.today_vn()}, self._title("Transactions · QPort", "Giao dịch · QPort")),
            "performance": ({"performance": svc.performance()}, self._title("Performance · QPort", "Hiệu suất · QPort")),
            "risk": ({"risk": svc.risk()}, self._title("Risk · QPort", "Rủi ro · QPort")),
            "snapshots": ({"snapshots": svc.snapshots()}, self._title("Snapshots · QPort", "Snapshot · QPort")),
            "operations": ({"operations": svc.institutional_overview(), "today": svc.today_vn()}, self._title("Operations · QPort", "Vận hành · QPort")),
            "settings": ({"dashboard": svc.dashboard()}, self._title("Settings · QPort", "Cài đặt · QPort")),
            "guide": ({}, self._title("Guide · QPort", "Hướng dẫn · QPort")),
        }
        if page not in configs: return self._send_json(404, {"error": "Page not found."})
        props, title = configs[page]; return self._send_page(page, props, title)

    def do_GET(self):
        path = urlparse(self.path).path
        if path.startswith("/api/portfolio"):
            return self._api_get(self._parts(path)[2:])
        if path.startswith("/assets/"):
            target = self._safe_join(DIST_DIR, path.lstrip("/"))
            return self._send_file(target) if target and os.path.isfile(target) else self._send_json(404, {"error": "Asset not found."})
        if path in {"", "/"}: return self._page("portfolio")
        routes = {f"/{x}": x for x in ("transactions", "performance", "risk", "snapshots", "operations", "settings", "guide")}
        return self._page(routes[path]) if path in routes else self._send_json(404, {"error": "Not found."})

    do_HEAD = do_GET

    def do_POST(self):
        path, body, svc = urlparse(self.path).path, self._read_body_json(), _portfolio()
        parts = self._parts(path)
        try:
            if path == "/api/portfolio/transactions": return self._send_json(201, svc.append_event(body))
            if path == "/api/portfolio/sync": return self._send_json(200, svc.sync_daily())
            if path == "/api/portfolio/reference-weights": return self._send_json(200, svc.set_reference_weights(body.get("weights") or {}))
            if path == "/api/portfolio/cash-reserve": return self._send_json(200, svc.set_cash_reserve(body.get("amount")))
            if path == "/api/portfolio/reconciliation": return self._send_json(201, svc.reconcile_broker(body))
            if path == "/api/portfolio/corporate-actions/sync": return self._send_json(200, svc.sync_corporate_actions(body.get("start"), body.get("end")))
            if len(parts) == 5 and parts[:3] == ["api", "portfolio", "corporate-actions"] and parts[4] == "verify":
                return self._send_json(200, svc.verify_corporate_action(int(parts[3]), body.get("source_url")))
            if len(parts) == 5 and parts[:3] == ["api", "portfolio", "corporate-actions"] and parts[4] == "receipt":
                return self._send_json(200, svc.record_corporate_action_receipt(int(parts[3]), body))
            if len(parts) == 5 and parts[:3] == ["api", "portfolio", "settlements"] and parts[4] == "confirm":
                return self._send_json(200, svc.confirm_settlement(int(parts[3]), body.get("note") or ""))
            if len(parts) == 5 and parts[:3] == ["api", "portfolio", "nav"] and parts[4] == "lock":
                return self._send_json(200, svc.lock_nav(parts[3]))
            if len(parts) == 5 and parts[:3] == ["api", "portfolio", "restatements"] and parts[4] == "resolve":
                return self._send_json(200, svc.resolve_restatement(int(parts[3])))
            if len(parts) == 4 and parts[:3] == ["api", "portfolio", "securities"]:
                return self._send_json(200, svc.update_security(parts[3], body))
        except InputValidationError as exc:
            return self._send_json(400, exc.as_dict())
        except Exception as exc:
            return self._send_json(400, {"error": str(exc), "code": "PORTFOLIO_ERROR", "field": None})
        return self._send_json(404, {"error": "Not found."})

    def do_PATCH(self):
        event_id = self._transaction_id(urlparse(self.path).path)
        if event_id is None: return self._send_json(404, {"error": "Transaction endpoint not found."})
        try: return self._send_json(200, _portfolio().update_event(event_id, self._read_body_json()))
        except InputValidationError as exc: return self._send_json(400, exc.as_dict())
        except Exception as exc: return self._send_json(400, {"error": str(exc), "code": "PORTFOLIO_ERROR", "field": None})

    def do_DELETE(self):
        event_id = self._transaction_id(urlparse(self.path).path)
        if event_id is None: return self._send_json(404, {"error": "Transaction endpoint not found."})
        try: return self._send_json(200, _portfolio().delete_event(event_id, self._read_body_json().get("reason")))
        except InputValidationError as exc: return self._send_json(400, exc.as_dict())
        except Exception as exc: return self._send_json(400, {"error": str(exc), "code": "PORTFOLIO_ERROR", "field": None})


def main():
    parser = argparse.ArgumentParser(description="Serve QPort institutional-lite Buy & Hold portfolio book")
    parser.add_argument("--port", type=int, default=8080); parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--no-daily-sync", action="store_true"); args = parser.parse_args()
    _ensure_ssr_worker(); service = _portfolio(); scheduler = None
    if not args.no_daily_sync:
        scheduler = DailySyncScheduler(service); scheduler.start()
    print(f"SSR renderer : {SSR_URL}", flush=True); print(f"Portfolio DB : {service.store.path}", flush=True)
    print(f"Daily sync   : {'disabled' if args.no_daily_sync else scheduler.hhmm + ' Asia/Ho_Chi_Minh'}", flush=True)
    port, server = _bind_with_fallback(args.host, args.port, Handler)
    print(f"Open http://{args.host}:{port}", flush=True); print("Mode: BUY & HOLD institutional-lite portfolio book", flush=True)
    try: server.serve_forever()
    except KeyboardInterrupt: print("\nShutting down.")
    finally:
        if scheduler: scheduler.stop()
        if _ssr_proc: _ssr_proc.terminate()


if __name__ == "__main__": main()
