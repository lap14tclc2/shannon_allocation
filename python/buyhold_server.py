#!/usr/bin/env python3
"""Standalone authenticated QPort Buy & Hold portfolio web application."""

from __future__ import annotations

import argparse
import ipaddress
import json
import os
import subprocess
import sys
import threading
import time
import urllib.request
from datetime import datetime
from http.cookies import SimpleCookie
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, unquote, urlparse
from zoneinfo import ZoneInfo

from portfolio.auth import AuthError, AuthStore, SESSION_DAYS
from portfolio.correctable_service import CorrectablePortfolioService
from portfolio.dividend_store import SqliteDividendService
from portfolio.dividends import DividendLookupError
from portfolio.locale import resolve_locale
from portfolio.scheduler import DailySyncScheduler
from portfolio.storage import PortfolioStore
from portfolio.validation import InputValidationError

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PYTHON_DIR = os.path.join(REPO, "python")
FRONTEND_DIR = os.path.join(REPO, "frontend")
DIST_DIR = os.path.join(FRONTEND_DIR, "dist")
SSR_HOST = "127.0.0.1"
SSR_PORT = int(os.environ.get("SSR_PORT", "8099"))
SSR_URL = f"http://{SSR_HOST}:{SSR_PORT}"
NODE_SSR = os.path.join(FRONTEND_DIR, "ssr", "server.mjs")
CLIENT_JS = "/assets/client.js"
CLIENT_CSS_DEFAULT = "/assets/entry-client.css"
SESSION_COOKIE = "qport_session"
MAX_REQUEST_BODY = int(os.environ.get("QPORT_MAX_REQUEST_BODY", str(1024 * 1024)))
VN_TZ = ZoneInfo("Asia/Ho_Chi_Minh")
MIME = {".html":"text/html; charset=utf-8",".js":"application/javascript; charset=utf-8",".mjs":"application/javascript; charset=utf-8",".css":"text/css; charset=utf-8",".json":"application/json; charset=utf-8",".png":"image/png",".svg":"image/svg+xml",".ico":"image/x-icon"}
SECURITY_HEADERS = {
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "Referrer-Policy": "no-referrer",
    "Permissions-Policy": "camera=(), microphone=(), geolocation=()",
    "Cross-Origin-Opener-Policy": "same-origin",
    "Content-Security-Policy": (
        "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; "
        "img-src 'self' data:; connect-src 'self'; object-src 'none'; base-uri 'none'; "
        "form-action 'self'; frame-ancestors 'none'"
    ),
}
ADMIN_RATE_WINDOW_SECONDS = 15 * 60
ADMIN_RATE_MAX_FAILURES = 5

_css_url = None
_ssr_proc: subprocess.Popen | None = None
_auth_store: AuthStore | None = None
_services: dict[int, CorrectablePortfolioService] = {}
_dividend_services: dict[int, SqliteDividendService] = {}
_admin_failures: dict[str, list[float]] = {}
_admin_failure_lock = threading.Lock()


def _auth() -> AuthStore:
    global _auth_store
    if _auth_store is None:
        _auth_store = AuthStore()
    return _auth_store


def _portfolio(user: dict) -> CorrectablePortfolioService:
    user_id = int(user["id"])
    service = _services.get(user_id)
    if service is None:
        store = PortfolioStore(_auth().portfolio_db_path(user_id))
        service = CorrectablePortfolioService(store=store)
        _services[user_id] = service
    return service


def _dividends(user: dict) -> SqliteDividendService:
    user_id = int(user["id"])
    service = _dividend_services.get(user_id)
    if service is None:
        service = SqliteDividendService(_portfolio(user).store, stop_on_first_data=False)
        _dividend_services[user_id] = service
    return service


def _drop_user_runtime(user_id: int) -> None:
    _services.pop(int(user_id), None)
    _dividend_services.pop(int(user_id), None)


def _cleanup_legacy_database() -> list[str]:
    """Remove the pre-auth single-user database so auth starts from clean data."""
    legacy = Path(PYTHON_DIR) / "data" / "portfolio.sqlite3"
    removed: list[str] = []
    for path in (legacy, Path(str(legacy) + "-wal"), Path(str(legacy) + "-shm")):
        if path.exists():
            path.unlink()
            removed.append(str(path))
    return removed


def _client_css_url() -> str:
    global _css_url
    if _css_url is None:
        assets = os.path.join(DIST_DIR, "assets")
        if os.path.isdir(assets):
            _css_url = next((f"/assets/{n}" for n in sorted(os.listdir(assets)) if n.endswith(".css")), None)
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
        time.sleep(.1)
    raise RuntimeError("Node SSR worker failed to start.")


def _ssr_render(page: str, props: dict) -> str:
    body = json.dumps({"page": page, "props": props}).encode()
    req = urllib.request.Request(f"{SSR_URL}/render", data=body, headers={"Content-Type":"application/json"}, method="POST")
    with urllib.request.urlopen(req, timeout=10) as resp:
        return json.loads(resp.read().decode())["html"]


def _build_document(page: str, props: dict, title: str) -> bytes:
    html = _ssr_render(page, props)
    serialized = json.dumps({"page":page,"props":props}, ensure_ascii=False).replace("<", "\\u003c")
    lang = "vi" if props.get("locale") == "vi" else "en"
    return (
        f"<!doctype html><html lang='{lang}'><head><meta charset='utf-8'>"
        f"<meta name='viewport' content='width=device-width, initial-scale=1'><title>{title}</title>"
        f"<link rel='stylesheet' href='{_client_css_url()}'></head><body><div id='root'>{html}</div>"
        f"<script id='qport-page-data' type='application/json'>{serialized}</script>"
        f"<script type='module' crossorigin src='{CLIENT_JS}'></script></body></html>"
    ).encode()


def _bind_with_fallback(host, port, handler, attempts=20):
    for offset in range(attempts):
        try:
            return port + offset, ThreadingHTTPServer((host, port + offset), handler)
        except OSError as exc:
            if offset == 0:
                print(f"Port {port} unavailable: {exc}", flush=True)
    raise SystemExit("Could not bind server port.")


def _is_loopback_host(host: str) -> bool:
    value = str(host or "").strip().lower()
    if value == "localhost":
        return True
    try:
        return ipaddress.ip_address(value).is_loopback
    except ValueError:
        return False


def _secure_cookie_enabled() -> bool:
    return str(os.environ.get("QPORT_SECURE_COOKIES", "0")).lower() in {"1", "true", "yes"}


def _admin_rate_key(client_address) -> str:
    return str((client_address or ("unknown",))[0] or "unknown")


def _admin_rate_limited(key: str) -> bool:
    now = time.monotonic()
    cutoff = now - ADMIN_RATE_WINDOW_SECONDS
    with _admin_failure_lock:
        recent = [stamp for stamp in _admin_failures.get(key, []) if stamp >= cutoff]
        if recent:
            _admin_failures[key] = recent
        else:
            _admin_failures.pop(key, None)
        return len(recent) >= ADMIN_RATE_MAX_FAILURES


def _record_admin_failure(key: str) -> None:
    now = time.monotonic()
    cutoff = now - ADMIN_RATE_WINDOW_SECONDS
    with _admin_failure_lock:
        recent = [stamp for stamp in _admin_failures.get(key, []) if stamp >= cutoff]
        recent.append(now)
        _admin_failures[key] = recent[-ADMIN_RATE_MAX_FAILURES:]


def _clear_admin_failures(key: str) -> None:
    with _admin_failure_lock:
        _admin_failures.pop(key, None)


class MultiUserDailySyncScheduler:
    """Run the existing safe daily sync once for every user database that exists."""

    def __init__(self, hhmm: str | None = None) -> None:
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
        self._thread = threading.Thread(target=self._loop, name="qport-multi-user-daily-sync", daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()

    def run_once(self, now: datetime | None = None) -> dict:
        now = now or datetime.now(VN_TZ)
        results = []
        for user in _auth().list_users():
            db_path = _auth().portfolio_db_path(user["id"])
            if not db_path.exists():
                continue
            try:
                result = DailySyncScheduler(_portfolio(user), hhmm=self.hhmm).run_once(now)
                results.append({"user_id": user["id"], "username": user["username"], "ok": True, "result": result})
            except Exception as exc:
                results.append({"user_id": user["id"], "username": user["username"], "ok": False, "error": str(exc)})
        return {"date": now.date().isoformat(), "users": results}

    def _loop(self) -> None:
        while not self._stop.is_set():
            now = datetime.now(VN_TZ)
            today = now.date().isoformat()
            if (now.hour, now.minute) >= (self.hour, self.minute) and self._last_attempt_date != today:
                self._last_attempt_date = today
                self.run_once(now)
            self._stop.wait(30.0)


class Handler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"
    server_version = "QPort"
    sys_version = ""

    def log_message(self, fmt, *args):
        pass

    @staticmethod
    def _parts(path):
        return [unquote(p) for p in path.split("/") if p]

    def _locale(self):
        return resolve_locale(cookie_header=self.headers.get("Cookie"), accept_language=self.headers.get("Accept-Language"))

    def _write(self, body):
        try:
            self.wfile.write(body)
            self.wfile.flush()
        except (BrokenPipeError, ConnectionAbortedError, ConnectionResetError, OSError):
            pass

    def _security_headers(self):
        for key, value in SECURITY_HEADERS.items():
            self.send_header(key, value)

    def _json(self, status, payload, headers: dict | None = None):
        body = json.dumps(payload, ensure_ascii=False).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self._security_headers()
        for key, value in (headers or {}).items():
            self.send_header(key, value)
        self.end_headers()
        self._write(body)

    def _bytes(self, status, body, content_type, headers: dict | None = None):
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        if str(content_type).startswith("text/html"):
            self.send_header("Cache-Control", "no-store")
        self._security_headers()
        for key, value in (headers or {}).items():
            self.send_header(key, value)
        self.end_headers()
        self._write(body)

    def _body(self):
        try:
            n = int(self.headers.get("Content-Length", 0) or 0)
        except ValueError:
            self._json(400, {"error":"Invalid Content-Length.", "code":"INVALID_CONTENT_LENGTH", "field":None})
            return None
        if n < 0 or n > MAX_REQUEST_BODY:
            self._json(413, {"error":"Request body is too large.", "code":"REQUEST_TOO_LARGE", "field":None})
            return None
        raw = self.rfile.read(n) if n else b"{}"
        try:
            data = json.loads(raw.decode() or "{}")
        except Exception:
            self._json(400, {"error":"Request body must be valid JSON.", "code":"INVALID_JSON", "field":None})
            return None
        if not isinstance(data, dict):
            self._json(400, {"error":"Request body must be a JSON object.", "code":"INVALID_JSON_OBJECT", "field":None})
            return None
        return data

    def _require_same_origin_request(self) -> bool:
        if self.headers.get("X-QPort-Request") != "1":
            self._json(403, {"error":"Same-origin request marker is required.", "code":"CROSS_ORIGIN_REQUEST_BLOCKED", "field":None})
            return False
        fetch_site = str(self.headers.get("Sec-Fetch-Site") or "").lower()
        if fetch_site and fetch_site not in {"same-origin", "none"}:
            self._json(403, {"error":"Cross-site request blocked.", "code":"CROSS_ORIGIN_REQUEST_BLOCKED", "field":None})
            return False
        origin = self.headers.get("Origin")
        if origin:
            parsed = urlparse(origin)
            request_host = str(self.headers.get("Host") or "").lower()
            if parsed.scheme not in {"http", "https"} or parsed.netloc.lower() != request_host:
                self._json(403, {"error":"Request origin does not match QPort.", "code":"CROSS_ORIGIN_REQUEST_BLOCKED", "field":None})
                return False
        return True

    def _session_token(self) -> str | None:
        cookie = SimpleCookie()
        try:
            cookie.load(self.headers.get("Cookie") or "")
        except Exception:
            return None
        morsel = cookie.get(SESSION_COOKIE)
        return morsel.value if morsel else None

    def _current_user(self) -> dict | None:
        return _auth().authenticate(self._session_token())

    @staticmethod
    def _session_cookie(token: str) -> str:
        max_age = SESSION_DAYS * 24 * 60 * 60
        secure = "; Secure" if _secure_cookie_enabled() else ""
        return f"{SESSION_COOKIE}={token}; Path=/; Max-Age={max_age}; HttpOnly; SameSite=Lax{secure}"

    @staticmethod
    def _clear_session_cookie() -> str:
        secure = "; Secure" if _secure_cookie_enabled() else ""
        return f"{SESSION_COOKIE}=; Path=/; Max-Age=0; HttpOnly; SameSite=Lax{secure}"

    def _require_user(self) -> dict | None:
        user = self._current_user()
        if user is None:
            self._json(401, {"error":"Authentication required.", "code":"AUTH_REQUIRED", "field":None})
            return None
        return user

    def _require_admin(self) -> dict | None:
        user = self._require_user()
        if user is None:
            return None
        if user.get("role") != "ADMIN":
            self._json(403, {"error":"Admin access is required.", "code":"ADMIN_REQUIRED", "field":None})
            return None
        return user

    def _auth_page(self):
        locale = self._locale()
        props = {"locale": locale}
        title = "Đăng nhập · QPort" if locale == "vi" else "Sign in · QPort"
        return self._bytes(200, _build_document("auth", props, title), "text/html; charset=utf-8")

    def _page(self, page, user: dict):
        svc = _portfolio(user)
        locale = self._locale()
        data = {
            "portfolio":({"dashboard":svc.dashboard()},"Portfolio · QPort","Danh mục · QPort"),
            "transactions":({"transactions":svc.transactions(),"corrections":svc.transaction_audit(),"today":svc.today_vn()},"Transactions · QPort","Giao dịch · QPort"),
            "performance":({"performance":svc.performance()},"Performance · QPort","Hiệu suất · QPort"),
            "risk":({"risk":svc.risk()},"Risk · QPort","Rủi ro · QPort"),
            "snapshots":({"snapshots":svc.snapshots()},"Snapshots · QPort","Snapshot · QPort"),
            "operations":({"operations":svc.institutional_overview(),"today":svc.today_vn()},"Operations · QPort","Vận hành · QPort"),
            "logs":({"activity":svc.activity_log(limit=1000)},"Activity Log · QPort","Nhật ký hoạt động · QPort"),
            "settings":({"dashboard":svc.dashboard()},"Settings · QPort","Cài đặt · QPort"),
            "guide":({},"Guide · QPort","Hướng dẫn · QPort"),
            "admin":({},"Admin · QPort","Admin · QPort"),
        }
        if page not in data:
            return self._json(404, {"error":"Page not found."})
        if page == "admin" and user.get("role") != "ADMIN":
            return self._json(403, {"error":"Admin access is required.", "code":"ADMIN_REQUIRED"})
        props, en, vi = data[page]
        props = {**props, "locale":locale, "currentUser":user}
        return self._bytes(200, _build_document(page, props, vi if locale == "vi" else en), "text/html; charset=utf-8")

    def _api_auth_get(self, parts):
        if tuple(parts) == ("me",):
            user = self._current_user()
            if user is None:
                return self._json(401, {"error":"Not signed in.", "code":"AUTH_REQUIRED", "field":None})
            return self._json(200, {"ok":True, "user":user})
        if tuple(parts) == ("users",):
            admin = self._require_admin()
            if admin is None:
                return
            return self._json(200, {"ok":True, "users":_auth().list_users()})
        return self._json(404, {"error":"Auth endpoint not found."})

    def _api_auth_post(self, path, parts, body):
        try:
            if path == "/api/auth/login":
                username = str(body.get("username") or "").strip()
                rate_key = _admin_rate_key(self.client_address)
                if username.lower() == "admin" and _admin_rate_limited(rate_key):
                    return self._json(429, {"error":"Too many failed admin login attempts. Try again later.", "code":"ADMIN_RATE_LIMITED", "field":"password"})
                try:
                    user, token = _auth().login(username, body.get("password"))
                except AuthError as exc:
                    if username.lower() == "admin" and exc.code == "INVALID_ADMIN_PASSWORD":
                        _record_admin_failure(rate_key)
                    raise
                if user.get("role") == "ADMIN":
                    _clear_admin_failures(rate_key)
                return self._json(200, {"ok":True, "user":user}, {"Set-Cookie":self._session_cookie(token)})
            if path == "/api/auth/register":
                user = _auth().register(body.get("username"))
                token = _auth().create_session(user["id"])
                return self._json(201, {"ok":True, "user":user}, {"Set-Cookie":self._session_cookie(token)})
            if path == "/api/auth/logout":
                token = self._session_token()
                _auth().logout(token)
                return self._json(200, {"ok":True}, {"Set-Cookie":self._clear_session_cookie()})
            if path == "/api/auth/admin/password":
                admin = self._require_admin()
                if admin is None:
                    return
                result = _auth().change_admin_password(admin["id"], body.get("current_password"), body.get("new_password"))
                return self._json(200, result, {"Set-Cookie":self._clear_session_cookie()})
        except AuthError as exc:
            status = 404 if exc.code == "USER_NOT_REGISTERED" else 400
            if exc.code in {"INVALID_ADMIN_PASSWORD"}:
                status = 401
            if exc.code == "ADMIN_NOT_CONFIGURED":
                status = 503
            return self._json(status, exc.as_dict())
        return self._json(404, {"error":"Auth endpoint not found."})

    def _api_auth_delete(self, parts):
        admin = self._require_admin()
        if admin is None:
            return
        if len(parts) == 2 and parts[0] == "users":
            try:
                user_id = int(parts[1])
                _drop_user_runtime(user_id)
                result = _auth().delete_user(user_id)
                return self._json(200, result)
            except (ValueError, AuthError) as exc:
                if isinstance(exc, AuthError):
                    return self._json(400, exc.as_dict())
                return self._json(400, {"error":"Invalid user id.", "code":"INVALID_USER_ID", "field":"user_id"})
        return self._json(404, {"error":"Auth endpoint not found."})

    def _api_get(self, parts, query, user: dict):
        svc = _portfolio(user)
        if tuple(parts) == ("dividends", "health"):
            return self._json(200, _dividends(user).health())
        if len(parts) == 3 and parts[:2] == ["dividends", "latest"]:
            symbol = parts[2].upper().strip()
            refresh = str((parse_qs(query).get("refresh") or ["0"])[0]).lower() in {"1","true","yes"}
            if refresh and not self._require_same_origin_request():
                return
            try:
                result = _dividends(user).latest(symbol, force_refresh=refresh)
                svc._log(
                    "USER", user["username"], "CORPORATE_ACTION", "DIVIDEND_HISTORY_LOOKUP",
                    f"Loaded dividend history for {symbol}: {'FOUND' if result.get('found') else 'NOT_FOUND'} ({result.get('data_origin')}).",
                    entity_type="SECURITY", entity_id=symbol,
                    details={
                        "found":result.get("found"), "event_count":result.get("event_count"),
                        "latest":result.get("latest"), "data_origin":result.get("data_origin"),
                        "source_counts":result.get("source_counts"), "errors":result.get("errors"),
                    },
                    status="SUCCESS" if result.get("found") else "PARTIAL",
                )
                return self._json(200, result)
            except DividendLookupError as exc:
                svc.log_failure(method="GET", path=f"/api/portfolio/dividends/latest/{symbol}", error=str(exc), code="INVALID_TICKER")
                return self._json(400, {"error":str(exc), "code":"INVALID_TICKER", "field":"symbol"})
            except Exception as exc:
                svc.log_failure(method="GET", path=f"/api/portfolio/dividends/latest/{symbol}", error=str(exc), code="DIVIDEND_LOOKUP_FAILED")
                return self._json(502, {"error":str(exc), "code":"DIVIDEND_LOOKUP_FAILED", "field":None})
        routes = {
            (): svc.dashboard,
            ("transactions",): lambda: {"transactions":svc.transactions()},
            ("transaction-audit",): lambda: {"corrections":svc.transaction_audit()},
            ("performance",): svc.performance,
            ("risk",): svc.risk,
            ("snapshots",): lambda: {"snapshots":svc.snapshots()},
            ("market",): lambda: svc.dashboard().get("market_data") or {},
            ("preferences",): svc.preferences,
            ("operations",): svc.institutional_overview,
            ("logs",): lambda: svc.activity_log(limit=1000),
        }
        fn = routes.get(tuple(parts))
        return self._json(200, fn()) if fn else self._json(404, {"error":"Portfolio endpoint not found."})

    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path
        if path.startswith("/assets/"):
            target = os.path.realpath(os.path.join(DIST_DIR, path.lstrip("/")))
            root = os.path.realpath(DIST_DIR)
            if not (target == root or target.startswith(root + os.sep)) or not os.path.isfile(target):
                return self._json(404, {"error":"Asset not found."})
            with open(target, "rb") as fh:
                body = fh.read()
            return self._bytes(200, body, MIME.get(os.path.splitext(target)[1].lower(), "application/octet-stream"))
        if path.startswith("/api/auth"):
            return self._api_auth_get(self._parts(path)[2:])
        if path.startswith("/api/portfolio"):
            user = self._require_user()
            if user is None:
                return
            return self._api_get(self._parts(path)[2:], parsed.query, user)

        user = self._current_user()
        if user is None:
            return self._auth_page()
        if path in {"", "/", "/login"}:
            return self._page("portfolio", user)
        routes = {f"/{p}":p for p in ("transactions","performance","risk","snapshots","operations","logs","settings","guide","admin")}
        return self._page(routes[path], user) if path in routes else self._json(404, {"error":"Not found."})

    do_HEAD = do_GET

    def _fail(self, svc, path, exc, code="PORTFOLIO_ERROR"):
        svc.log_failure(method=self.command, path=path, error=str(exc), code=code)
        if isinstance(exc, InputValidationError):
            return self._json(400, exc.as_dict())
        return self._json(400, {"error":str(exc), "code":code, "field":None})

    def do_POST(self):
        path = urlparse(self.path).path
        if not self._require_same_origin_request():
            return
        parts = self._parts(path)
        body = self._body()
        if body is None:
            return
        if path.startswith("/api/auth"):
            return self._api_auth_post(path, parts[2:], body)

        user = self._require_user()
        if user is None:
            return
        svc = _portfolio(user)
        actor = user["username"]
        try:
            if path == "/api/portfolio/transactions":
                return self._json(201, svc.append_event(body, created_by=actor))
            if path == "/api/portfolio/sync":
                return self._json(200, svc.sync_daily(actor_type="USER", actor_id=actor))
            if path == "/api/portfolio/reference-weights":
                return self._json(200, svc.set_reference_weights(body.get("weights") or {}))
            if path == "/api/portfolio/cash-reserve":
                return self._json(200, svc.set_cash_reserve(body.get("amount")))
            if path == "/api/portfolio/reconciliation":
                return self._json(201, svc.reconcile_broker(body, created_by=actor))
            if path == "/api/portfolio/corporate-actions/sync":
                return self._json(200, svc.sync_corporate_actions(body.get("start"), body.get("end")))
            if path == "/api/portfolio/corporate-actions/post":
                return self._json(200, svc.post_corporate_action_receipt(int(body.get("action_id")), created_by=actor))
            if path == "/api/portfolio/securities/resolve":
                return self._json(200, svc.resolve_all_securities())
            if path == "/api/portfolio/activity":
                return self._json(201, svc.log_client_activity(body.get("action"), body.get("details") or {}))
            if len(parts) == 5 and parts[:3] == ["api","portfolio","corporate-actions"] and parts[4] == "verify":
                return self._json(200, svc.verify_corporate_action(int(parts[3]), body.get("source_url"), verified_by=actor))
            if len(parts) == 5 and parts[:3] == ["api","portfolio","corporate-actions"] and parts[4] == "receipt":
                return self._json(200, svc.record_corporate_action_receipt(int(parts[3]), body, created_by=actor))
            if len(parts) == 5 and parts[:3] == ["api","portfolio","settlements"] and parts[4] == "confirm":
                return self._json(200, svc.confirm_settlement(int(parts[3]), body.get("note") or ""))
            if len(parts) == 5 and parts[:3] == ["api","portfolio","nav"] and parts[4] == "lock":
                return self._json(200, svc.lock_nav(parts[3]))
            if len(parts) == 5 and parts[:3] == ["api","portfolio","restatements"] and parts[4] == "resolve":
                return self._json(200, svc.resolve_restatement(int(parts[3])))
            if len(parts) == 5 and parts[:3] == ["api","portfolio","securities"] and parts[4] == "resolve":
                return self._json(200, svc.resolve_security(parts[3]))
            if len(parts) == 4 and parts[:3] == ["api","portfolio","securities"]:
                return self._json(200, svc.update_security(parts[3], body))
        except Exception as exc:
            return self._fail(svc, path, exc, getattr(exc, "code", "PORTFOLIO_ERROR"))
        return self._json(404, {"error":"Not found."})

    @staticmethod
    def _tx_id(path):
        p = Handler._parts(path)
        if len(p) == 4 and p[:3] == ["api","portfolio","transactions"]:
            try:
                return int(p[3])
            except ValueError:
                return None
        return None

    def do_PATCH(self):
        path = urlparse(self.path).path
        if not self._require_same_origin_request():
            return
        user = self._require_user()
        if user is None:
            return
        body = self._body()
        if body is None:
            return
        eid = self._tx_id(path)
        svc = _portfolio(user)
        if eid is None:
            return self._json(404, {"error":"Transaction endpoint not found."})
        try:
            return self._json(200, svc.update_event(eid, body, created_by=user["username"]))
        except Exception as exc:
            return self._fail(svc, path, exc, getattr(exc, "code", "PORTFOLIO_ERROR"))

    def do_DELETE(self):
        path = urlparse(self.path).path
        if not self._require_same_origin_request():
            return
        if path.startswith("/api/auth"):
            body = self._body()
            if body is None:
                return
            return self._api_auth_delete(self._parts(path)[2:])
        user = self._require_user()
        if user is None:
            return
        body = self._body()
        if body is None:
            return
        eid = self._tx_id(path)
        svc = _portfolio(user)
        if eid is None:
            return self._json(404, {"error":"Transaction endpoint not found."})
        try:
            return self._json(200, svc.delete_event(eid, body.get("reason"), created_by=user["username"]))
        except Exception as exc:
            return self._fail(svc, path, exc, getattr(exc, "code", "PORTFOLIO_ERROR"))


def main():
    parser = argparse.ArgumentParser(description="Serve authenticated QPort Buy & Hold portfolio book")
    parser.add_argument("--port", type=int, default=8080)
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--no-daily-sync", action="store_true")
    parser.add_argument(
        "--allow-trusted-network",
        action="store_true",
        help="Allow a non-loopback bind. Username-only normal-user login is intended only for a trusted network.",
    )
    args = parser.parse_args()

    if not _is_loopback_host(args.host) and not args.allow_trusted_network:
        raise SystemExit(
            "Refusing non-loopback bind: normal users authenticate by username only. "
            "Keep QPort on localhost, or explicitly pass --allow-trusted-network behind appropriate network/TLS controls."
        )

    removed = _cleanup_legacy_database()
    auth = _auth()
    _ensure_ssr_worker()
    scheduler = None
    if not args.no_daily_sync:
        scheduler = MultiUserDailySyncScheduler()
        scheduler.start()

    print(f"SSR renderer : {SSR_URL}", flush=True)
    print(f"Auth DB      : {auth.path}", flush=True)
    print(f"User DBs     : {auth.user_data_dir}", flush=True)
    if removed:
        print(f"Legacy DB    : removed {len(removed)} file(s); fresh authenticated storage active", flush=True)
    print(f"Daily sync   : {'disabled' if args.no_daily_sync else scheduler.hhmm+' Asia/Ho_Chi_Minh'}", flush=True)
    print(f"Admin auth   : {'configured' if auth.admin_configured() else 'NOT CONFIGURED — run python -m portfolio.cli setup-admin'}", flush=True)
    if not _is_loopback_host(args.host):
        print("SECURITY     : trusted-network override enabled; use HTTPS and QPORT_SECURE_COOKIES=1", flush=True)
    port, server = _bind_with_fallback(args.host, args.port, Handler)
    print(f"Open http://{args.host}:{port}\nMode: AUTHENTICATED BUY & HOLD portfolio book", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down.")
    finally:
        if scheduler:
            scheduler.stop()
        if _ssr_proc:
            _ssr_proc.terminate()


if __name__ == "__main__":
    main()
