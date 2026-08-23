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
from urllib.parse import parse_qs, unquote, urlparse

from portfolio.correctable_service import CorrectablePortfolioService
from portfolio.dividend_store import SqliteDividendService
from portfolio.dividends import DividendLookupError
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
MIME = {".html":"text/html; charset=utf-8",".js":"application/javascript; charset=utf-8",".mjs":"application/javascript; charset=utf-8",".css":"text/css; charset=utf-8",".json":"application/json; charset=utf-8",".png":"image/png",".svg":"image/svg+xml",".ico":"image/x-icon"}
_css_url = None
_ssr_proc: subprocess.Popen | None = None
_service: CorrectablePortfolioService | None = None
_dividend_service: SqliteDividendService | None = None


def _portfolio() -> CorrectablePortfolioService:
    global _service
    if _service is None:
        _service = CorrectablePortfolioService()
    return _service


def _dividends() -> SqliteDividendService:
    global _dividend_service
    if _dividend_service is None:
        _dividend_service = SqliteDividendService(_portfolio().store, stop_on_first_data=False)
    return _dividend_service


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
        with urllib.request.urlopen(f"{SSR_URL}/health", timeout=1.5): return True
    except Exception: return False


def _ensure_ssr_worker() -> None:
    global _ssr_proc
    if _ssr_health(): return
    if not os.path.isfile(os.path.join(FRONTEND_DIR, "dist-ssr", "ssr-entry.mjs")):
        raise RuntimeError("SSR bundle not built. Run: cd frontend && npm run build && npm run build:ssr")
    if not os.path.isfile(os.path.join(DIST_DIR, "assets", "client.js")):
        raise RuntimeError("Client bundle not built. Run: cd frontend && npm run build")
    env = dict(os.environ, SSR_PORT=str(SSR_PORT), SSR_HOST=SSR_HOST)
    _ssr_proc = subprocess.Popen(["node", NODE_SSR], cwd=FRONTEND_DIR, env=env, stdout=sys.stdout, stderr=sys.stderr)
    for _ in range(50):
        if _ssr_health(): return
        time.sleep(.1)
    raise RuntimeError("Node SSR worker failed to start.")


def _ssr_render(page: str, props: dict) -> str:
    body = json.dumps({"page":page,"props":props}).encode()
    req = urllib.request.Request(f"{SSR_URL}/render", data=body, headers={"Content-Type":"application/json"}, method="POST")
    with urllib.request.urlopen(req, timeout=10) as resp: return json.loads(resp.read().decode())["html"]


def _build_document(page: str, props: dict, title: str) -> bytes:
    html = _ssr_render(page, props)
    serialized = json.dumps({"page":page,"props":props}, ensure_ascii=False).replace("<", "\\u003c")
    lang = "vi" if props.get("locale") == "vi" else "en"
    return (f"<!doctype html><html lang='{lang}'><head><meta charset='utf-8'><meta name='viewport' content='width=device-width, initial-scale=1'><title>{title}</title><link rel='stylesheet' href='{_client_css_url()}'></head><body><div id='root'>{html}</div><script>window.__PAGE__={serialized};</script><script type='module' crossorigin src='{CLIENT_JS}'></script></body></html>").encode()


def _bind_with_fallback(host, port, handler, attempts=20):
    for offset in range(attempts):
        try: return port + offset, ThreadingHTTPServer((host, port + offset), handler)
        except OSError as exc:
            if offset == 0: print(f"Port {port} unavailable: {exc}", flush=True)
    raise SystemExit("Could not bind server port.")


class Handler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"
    def log_message(self, fmt, *args): pass

    @staticmethod
    def _parts(path): return [unquote(p) for p in path.split("/") if p]
    def _locale(self): return resolve_locale(cookie_header=self.headers.get("Cookie"), accept_language=self.headers.get("Accept-Language"))
    def _write(self, body):
        try: self.wfile.write(body); self.wfile.flush()
        except (BrokenPipeError, ConnectionAbortedError, ConnectionResetError, OSError): pass
    def _json(self, status, payload):
        body = json.dumps(payload, ensure_ascii=False).encode(); self.send_response(status)
        self.send_header("Content-Type","application/json; charset=utf-8"); self.send_header("Content-Length",str(len(body))); self.send_header("Cache-Control","no-store"); self.end_headers(); self._write(body)
    def _bytes(self, status, body, content_type):
        self.send_response(status); self.send_header("Content-Type",content_type); self.send_header("Content-Length",str(len(body))); self.end_headers(); self._write(body)
    def _body(self):
        n = int(self.headers.get("Content-Length",0) or 0); raw = self.rfile.read(n) if n else b"{}"
        try: return json.loads(raw.decode() or "{}")
        except Exception: return {}

    def _page(self, page):
        svc = _portfolio(); locale = self._locale()
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
        }
        if page not in data: return self._json(404,{"error":"Page not found."})
        props,en,vi = data[page]; props={**props,"locale":locale}; return self._bytes(200,_build_document(page,props,vi if locale=="vi" else en),"text/html; charset=utf-8")

    def _api_get(self, parts, query=""):
        svc=_portfolio()
        if tuple(parts)==("dividends","health"):
            return self._json(200,_dividends().health())
        if len(parts)==3 and parts[:2]==["dividends","latest"]:
            symbol=parts[2].upper().strip()
            refresh=str((parse_qs(query).get("refresh") or ["0"])[0]).lower() in {"1","true","yes"}
            try:
                result=_dividends().latest(symbol,force_refresh=refresh)
                svc._log(
                    "USER","local","CORPORATE_ACTION","DIVIDEND_HISTORY_LOOKUP",
                    f"Loaded dividend history for {symbol}: {'FOUND' if result.get('found') else 'NOT_FOUND'} ({result.get('data_origin')}).",
                    entity_type="SECURITY",entity_id=symbol,
                    details={
                        "found":result.get("found"),"event_count":result.get("event_count"),
                        "latest":result.get("latest"),"data_origin":result.get("data_origin"),
                        "source_counts":result.get("source_counts"),"errors":result.get("errors")
                    },
                    status="SUCCESS" if result.get("found") else "PARTIAL",
                )
                return self._json(200,result)
            except DividendLookupError as exc:
                svc.log_failure(method="GET",path=f"/api/portfolio/dividends/latest/{symbol}",error=str(exc),code="INVALID_TICKER")
                return self._json(400,{"error":str(exc),"code":"INVALID_TICKER","field":"symbol"})
            except Exception as exc:
                svc.log_failure(method="GET",path=f"/api/portfolio/dividends/latest/{symbol}",error=str(exc),code="DIVIDEND_LOOKUP_FAILED")
                return self._json(502,{"error":str(exc),"code":"DIVIDEND_LOOKUP_FAILED","field":None})
        routes={
            ():svc.dashboard,
            ("transactions",):lambda:{"transactions":svc.transactions()},
            ("transaction-audit",):lambda:{"corrections":svc.transaction_audit()},
            ("performance",):svc.performance,
            ("risk",):svc.risk,
            ("snapshots",):lambda:{"snapshots":svc.snapshots()},
            ("market",):lambda:svc.dashboard().get("market_data") or {},
            ("preferences",):svc.preferences,
            ("operations",):svc.institutional_overview,
            ("logs",):lambda:svc.activity_log(limit=1000),
        }
        fn=routes.get(tuple(parts)); return self._json(200,fn()) if fn else self._json(404,{"error":"Portfolio endpoint not found."})

    def do_GET(self):
        parsed=urlparse(self.path); path=parsed.path
        if path.startswith("/api/portfolio"): return self._api_get(self._parts(path)[2:],parsed.query)
        if path.startswith("/assets/"):
            target=os.path.realpath(os.path.join(DIST_DIR,path.lstrip("/"))); root=os.path.realpath(DIST_DIR)
            if not (target==root or target.startswith(root+os.sep)) or not os.path.isfile(target): return self._json(404,{"error":"Asset not found."})
            with open(target,"rb") as fh: body=fh.read()
            return self._bytes(200,body,MIME.get(os.path.splitext(target)[1].lower(),"application/octet-stream"))
        if path in {"","/"}: return self._page("portfolio")
        routes={f"/{p}":p for p in ("transactions","performance","risk","snapshots","operations","logs","settings","guide")}
        return self._page(routes[path]) if path in routes else self._json(404,{"error":"Not found."})
    do_HEAD=do_GET

    def _fail(self, svc, path, exc, code="PORTFOLIO_ERROR"):
        svc.log_failure(method=self.command, path=path, error=str(exc), code=code)
        if isinstance(exc, InputValidationError): return self._json(400,exc.as_dict())
        return self._json(400,{"error":str(exc),"code":code,"field":None})

    def do_POST(self):
        path=urlparse(self.path).path; parts=self._parts(path); body=self._body(); svc=_portfolio()
        try:
            if path=="/api/portfolio/transactions": return self._json(201,svc.append_event(body))
            if path=="/api/portfolio/sync": return self._json(200,svc.sync_daily(actor_type="USER",actor_id="local"))
            if path=="/api/portfolio/reference-weights": return self._json(200,svc.set_reference_weights(body.get("weights") or {}))
            if path=="/api/portfolio/cash-reserve": return self._json(200,svc.set_cash_reserve(body.get("amount")))
            if path=="/api/portfolio/reconciliation": return self._json(201,svc.reconcile_broker(body))
            if path=="/api/portfolio/corporate-actions/sync": return self._json(200,svc.sync_corporate_actions(body.get("start"),body.get("end")))
            if path=="/api/portfolio/corporate-actions/post": return self._json(200,svc.post_corporate_action_receipt(int(body.get("action_id"))))
            if path=="/api/portfolio/securities/resolve": return self._json(200,svc.resolve_all_securities())
            if path=="/api/portfolio/activity": return self._json(201,svc.log_client_activity(body.get("action"),body.get("details") or {}))
            if len(parts)==5 and parts[:3]==["api","portfolio","corporate-actions"] and parts[4]=="verify": return self._json(200,svc.verify_corporate_action(int(parts[3]),body.get("source_url")))
            if len(parts)==5 and parts[:3]==["api","portfolio","corporate-actions"] and parts[4]=="receipt": return self._json(200,svc.record_corporate_action_receipt(int(parts[3]),body))
            if len(parts)==5 and parts[:3]==["api","portfolio","settlements"] and parts[4]=="confirm": return self._json(200,svc.confirm_settlement(int(parts[3]),body.get("note") or ""))
            if len(parts)==5 and parts[:3]==["api","portfolio","nav"] and parts[4]=="lock": return self._json(200,svc.lock_nav(parts[3]))
            if len(parts)==5 and parts[:3]==["api","portfolio","restatements"] and parts[4]=="resolve": return self._json(200,svc.resolve_restatement(int(parts[3])))
            if len(parts)==5 and parts[:3]==["api","portfolio","securities"] and parts[4]=="resolve": return self._json(200,svc.resolve_security(parts[3]))
            if len(parts)==4 and parts[:3]==["api","portfolio","securities"]: return self._json(200,svc.update_security(parts[3],body))
        except Exception as exc: return self._fail(svc,path,exc,getattr(exc,"code","PORTFOLIO_ERROR"))
        return self._json(404,{"error":"Not found."})

    @staticmethod
    def _tx_id(path):
        p=Handler._parts(path)
        if len(p)==4 and p[:3]==["api","portfolio","transactions"]:
            try:return int(p[3])
            except ValueError:return None
        return None

    def do_PATCH(self):
        path=urlparse(self.path).path; eid=self._tx_id(path); svc=_portfolio()
        if eid is None:return self._json(404,{"error":"Transaction endpoint not found."})
        try:return self._json(200,svc.update_event(eid,self._body()))
        except Exception as exc:return self._fail(svc,path,exc,getattr(exc,"code","PORTFOLIO_ERROR"))

    def do_DELETE(self):
        path=urlparse(self.path).path; eid=self._tx_id(path); svc=_portfolio()
        if eid is None:return self._json(404,{"error":"Transaction endpoint not found."})
        try:return self._json(200,svc.delete_event(eid,self._body().get("reason")))
        except Exception as exc:return self._fail(svc,path,exc,getattr(exc,"code","PORTFOLIO_ERROR"))


def main():
    parser=argparse.ArgumentParser(description="Serve QPort institutional-lite Buy & Hold portfolio book"); parser.add_argument("--port",type=int,default=8080); parser.add_argument("--host",default="127.0.0.1"); parser.add_argument("--no-daily-sync",action="store_true"); args=parser.parse_args()
    _ensure_ssr_worker(); service=_portfolio(); scheduler=None
    if not args.no_daily_sync: scheduler=DailySyncScheduler(service); scheduler.start()
    print(f"SSR renderer : {SSR_URL}\nPortfolio DB : {service.store.path}",flush=True); print(f"Daily sync   : {'disabled' if args.no_daily_sync else scheduler.hhmm+' Asia/Ho_Chi_Minh'}",flush=True)
    port,server=_bind_with_fallback(args.host,args.port,Handler); print(f"Open http://{args.host}:{port}\nMode: BUY & HOLD institutional-lite portfolio book",flush=True)
    try:server.serve_forever()
    except KeyboardInterrupt:print("\nShutting down.")
    finally:
        if scheduler:scheduler.stop()
        if _ssr_proc:_ssr_proc.terminate()

if __name__=="__main__":main()
