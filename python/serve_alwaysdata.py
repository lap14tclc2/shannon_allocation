#!/usr/bin/env python3
"""AlwaysData Free entrypoint for QPort.

AlwaysData User Program sites expose the required bind address and port through
IP/PORT. Public Cloud commonly uses IPv6, while Python's ThreadingHTTPServer is
IPv4 by default. This wrapper keeps the normal QPort runtime intact while
binding exactly to the platform-provided endpoint.
"""

from __future__ import annotations

import os
import socket
import sys
from http.server import ThreadingHTTPServer
from pathlib import Path


def _free_loopback_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


# Pick an internal-only SSR port before importing buyhold_server because that
# module resolves SSR_PORT at import time.
os.environ.setdefault("SSR_PORT", str(_free_loopback_port()))
os.environ.setdefault("QPORT_AUTH_NAMESPACE", str(Path.home() / "qport-data" / "auth-v1"))

import buyhold_server  # noqa: E402
from portfolio.automated_service import AutomatedPortfolioService  # noqa: E402


class IPv6ThreadingHTTPServer(ThreadingHTTPServer):
    address_family = socket.AF_INET6


def _bind_exact(host, port, handler, attempts=1):
    """AlwaysData requires the exact assigned PORT; never fall back to another."""
    server_cls = IPv6ThreadingHTTPServer if ":" in host else ThreadingHTTPServer
    return int(port), server_cls((host, int(port)), handler)


buyhold_server.CorrectablePortfolioService = AutomatedPortfolioService
buyhold_server._bind_with_fallback = _bind_exact


def main() -> None:
    host = os.environ.get("IP") or "::"
    port = int(os.environ.get("PORT") or "8080")
    argv = [sys.argv[0], "--host", host, "--port", str(port)]
    if os.environ.get("QPORT_DISABLE_DAILY_SYNC", "0").strip().lower() in {"1", "true", "yes", "on"}:
        argv.append("--no-daily-sync")
    sys.argv = argv
    buyhold_server.main()


if __name__ == "__main__":
    main()
