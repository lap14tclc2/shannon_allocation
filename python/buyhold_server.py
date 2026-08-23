#!/usr/bin/env python3
"""Buy-and-hold portfolio web application with an isolated research boundary."""

from __future__ import annotations

import argparse
import json
import os
from datetime import datetime
from urllib.parse import unquote, urlparse

import research_legacy_server as legacy
from portfolio.service import PortfolioService

_service: PortfolioService | None = None


def _portfolio() -> PortfolioService:
    global _service
    if _service is None:
        _service = PortfolioService()
    return _service


class Handler(legacy.Handler):
    """Operational handler.

    Portfolio APIs are first-class. Legacy optimizer/backtest handlers are only
    reachable through the explicit research boundary (plus compatibility aliases
    for old saved URLs).
    """

    def _portfolio_api(self, parts):
        svc = _portfolio()
        if not parts:
            return self._send_json(200, svc.dashboard())
        if parts == ["transactions"]:
            return self._send_json(200, {"transactions": svc.transactions()})
        if parts == ["performance"]:
            return self._send_json(200, svc.performance())
        if parts == ["risk"]:
            return self._send_json(200, svc.risk())
        if parts == ["snapshots"]:
            return self._send_json(200, {"snapshots": svc.snapshots()})
        if parts == ["market"]:
            dashboard = svc.dashboard()
            return self._send_json(200, dashboard.get("market_data") or {})
        return self._send_json(404, {"error": "Portfolio endpoint not found."})

    def _handle_api(self, parts):
        if len(parts) >= 2 and parts[1] == "portfolio":
            return self._portfolio_api(parts[2:])
        if len(parts) >= 3 and parts[1] == "research" and parts[2] == "optimizer":
            return self._handle_optimizer(parts[3:])
        if len(parts) >= 3 and parts[1] == "research" and parts[2] == "runs":
            return self._handle_runs(parts[3:])
        return super()._handle_api(parts)

    def _research_page(self, parts):
        if not parts:
            return self._send_page(
                "research",
                {
                    "experiments": self._list_optimizer_experiments(),
                    "runs": self._runs(),
                },
                "Research Lab · QPort",
            )
        if parts[0] == "optimizer":
            if len(parts) == 1:
                return self._send_page(
                    "optimizer_list",
                    {"experiments": self._list_optimizer_experiments()},
                    "Research Optimizer · QPort",
                )
            eid = parts[1]
            base = self._safe_join(legacy.OPTIMIZER_DIR, eid)
            exp = None
            if base and os.path.isfile(os.path.join(base, "experiment.json")):
                with open(os.path.join(base, "experiment.json"), "r", encoding="utf-8") as fh:
                    exp = json.load(fh)
            if exp is None:
                return self._send_json(404, {"error": f"Experiment not found: {eid}"})
            return self._send_page("optimizer_detail", {"experiment": exp}, f"Research {eid}")
        if parts[0] == "runs":
            return super()._handle_page(parts[1:])
        return self._send_json(404, {"error": "Research page not found."})

    def _operational_page(self, page: str):
        svc = _portfolio()
        if page == "portfolio":
            return self._send_page("portfolio", {"dashboard": svc.dashboard()}, "Portfolio · QPort")
        if page == "transactions":
            return self._send_page(
                "transactions",
                {"transactions": svc.transactions(), "today": svc.today_vn()},
                "Transactions · QPort",
            )
        if page == "performance":
            return self._send_page("performance", {"performance": svc.performance()}, "Performance · QPort")
        if page == "risk":
            return self._send_page("risk", {"risk": svc.risk()}, "Risk · QPort")
        if page == "snapshots":
            return self._send_page("snapshots", {"snapshots": svc.snapshots()}, "Snapshots · QPort")
        return self._send_json(404, {"error": "Page not found."})

    def do_GET(self):
        path = urlparse(self.path).path
        if path.startswith("/api/"):
            return self._handle_api([unquote(p) for p in path.split("/") if p])
        if path.startswith("/assets/"):
            target = self._safe_join(legacy.DIST_DIR, path.lstrip("/"))
            if target and os.path.isfile(target):
                return self._send_file(target)
            return self._send_json(404, {"error": "Asset not found."})

        if path in {"", "/"}:
            return self._operational_page("portfolio")
        operational = {
            "/transactions": "transactions",
            "/performance": "performance",
            "/risk": "risk",
            "/snapshots": "snapshots",
        }
        if path in operational:
            return self._operational_page(operational[path])
        if path == "/research" or path.startswith("/research/"):
            parts = [unquote(p) for p in path.split("/") if p][1:]
            return self._research_page(parts)

        # Compatibility: old optimizer URLs now render the same Research pages.
        if path == "/optimizer" or path.startswith("/optimizer/"):
            parts = ["optimizer", *[unquote(p) for p in path.split("/") if p][1:]]
            return self._research_page(parts)
        if path.startswith("/runs/"):
            parts = [unquote(p) for p in path.split("/") if p]
            return super()._handle_page(parts[1:])
        return self._send_json(404, {"error": "Not found."})

    do_HEAD = do_GET

    def _read_body_json(self):
        length = int(self.headers.get("Content-Length", 0) or 0)
        raw = self.rfile.read(length) if length else b"{}"
        try:
            return json.loads(raw.decode("utf-8") or "{}")
        except Exception:
            return {}

    def do_POST(self):
        path = urlparse(self.path).path
        body = self._read_body_json()
        svc = _portfolio()
        try:
            if path == "/api/portfolio/transactions":
                return self._send_json(201, svc.append_event(body))
            if path == "/api/portfolio/sync":
                return self._send_json(200, svc.sync_daily())
            if path == "/api/portfolio/reference-weights":
                return self._send_json(200, svc.set_reference_weights(body.get("weights") or {}))
            if path in {"/api/research/optimizer/run", "/api/optimizer/run"}:
                return self._handle_optimizer_run(body)
            if path == "/api/combination/health":
                return self._handle_combination_health(body)
        except Exception as exc:
            return self._send_json(400, {"error": str(exc)})
        return self._send_json(404, {"error": "Not found."})

    def do_DELETE(self):
        path = urlparse(self.path).path
        if path.startswith("/api/research/optimizer/"):
            parts = [unquote(p) for p in path.split("/") if p]
            if len(parts) == 4:
                return self._handle_delete_optimizer(parts[3])
        return super().do_DELETE()


def main():
    parser = argparse.ArgumentParser(description="Serve QPort buy-and-hold portfolio information system")
    parser.add_argument("--port", type=int, default=8080)
    parser.add_argument("--host", default="127.0.0.1")
    args = parser.parse_args()

    legacy._ensure_ssr_worker()
    print(f"SSR renderer : {legacy.SSR_URL}", flush=True)
    print(f"Portfolio DB : {_portfolio().store.path}", flush=True)
    print(f"Research dir : {legacy.RESULTS_DIR}", flush=True)

    port, server = legacy._bind_with_fallback(args.host, args.port, Handler)
    print(f"Open http://{args.host}:{port}", flush=True)
    print("Mode: BUY & HOLD portfolio information system", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down.")
    finally:
        if legacy._ssr_proc:
            legacy._ssr_proc.terminate()


if __name__ == "__main__":
    main()
