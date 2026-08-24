from __future__ import annotations

import argparse
import json

from .auth import AuthError
from .automated_service import AutomatedPortfolioService
from .postgres import PostgresAuthStore, PostgresPortfolioStore


def main() -> None:
    parser = argparse.ArgumentParser(description="Authenticated QPort PostgreSQL portfolio operations")
    parser.add_argument("--username", required=True, help="Registered QPort username")
    parser.add_argument("--password", default="", help="Admin password; normal users leave this empty")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("sync", help="Fetch daily prices and create a portfolio snapshot")
    sub.add_parser("status", help="Print current portfolio dashboard JSON")
    sub.add_parser("performance", help="Print performance JSON")
    args = parser.parse_args()

    auth = PostgresAuthStore()
    try:
        user, temporary_token = auth.login(args.username, args.password)
    except AuthError as exc:
        parser.error(str(exc))
    else:
        auth.logout(temporary_token)

    if user.get("role") == "ADMIN":
        parser.error("Admin is administration-only. Use the /admin page instead of portfolio CLI commands.")

    service = AutomatedPortfolioService(store=PostgresPortfolioStore(user["id"]))
    if args.command == "sync":
        result = service.sync_daily(actor_type="USER", actor_id=user["username"])
    elif args.command == "performance":
        result = service.performance()
    else:
        result = service.dashboard()
    print(json.dumps(result, indent=2, ensure_ascii=False, default=str))


if __name__ == "__main__":
    main()
