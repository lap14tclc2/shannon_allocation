from __future__ import annotations

import argparse
import json

from .auth import AuthError, AuthStore
from .automated_service import AutomatedPortfolioService
from .storage import PortfolioStore


def main() -> None:
    parser = argparse.ArgumentParser(description="Authenticated buy-and-hold portfolio operations")
    parser.add_argument("--username", required=True, help="Registered QPort username")
    parser.add_argument("--password", default="", help="Admin password; normal users leave this empty")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("sync", help="Fetch daily prices and create a portfolio snapshot")
    sub.add_parser("status", help="Print current portfolio dashboard JSON")
    sub.add_parser("performance", help="Print performance JSON")
    args = parser.parse_args()

    auth = AuthStore()
    try:
        user, temporary_token = auth.login(args.username, args.password)
    except AuthError as exc:
        parser.error(str(exc))
    else:
        # CLI authentication verifies the same credentials as the web app but
        # does not keep a browser-style session alive.
        auth.logout(temporary_token)

    if user.get("role") == "ADMIN":
        parser.error("Admin is administration-only. Use the /admin page instead of portfolio CLI commands.")

    store = PortfolioStore(auth.portfolio_db_path(user["id"]))
    service = AutomatedPortfolioService(store=store)
    if args.command == "sync":
        result = service.sync_daily()
    elif args.command == "performance":
        result = service.performance()
    else:
        result = service.dashboard()
    print(json.dumps(result, indent=2, ensure_ascii=False, default=str))


if __name__ == "__main__":
    main()
