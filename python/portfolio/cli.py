from __future__ import annotations

import argparse
import getpass
import json

from .auth import AuthError, AuthStore
from .service import PortfolioService
from .storage import PortfolioStore


def _prompt_new_admin_password(auth: AuthStore, parser: argparse.ArgumentParser) -> None:
    first = getpass.getpass("New admin password: ")
    second = getpass.getpass("Confirm admin password: ")
    if first != second:
        parser.error("Admin passwords do not match.")
    try:
        result = auth.bootstrap_admin_password(first)
    except AuthError as exc:
        parser.error(str(exc))
    print(result["message"])


def main() -> None:
    parser = argparse.ArgumentParser(description="Authenticated buy-and-hold portfolio operations")
    parser.add_argument("--username", help="Registered QPort username")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("setup-admin", help="Securely configure the admin password on first use")
    sub.add_parser("sync", help="Fetch daily prices and create a portfolio snapshot")
    sub.add_parser("status", help="Print current portfolio dashboard JSON")
    sub.add_parser("performance", help="Print performance JSON")
    args = parser.parse_args()

    auth = AuthStore()
    if args.command == "setup-admin":
        return _prompt_new_admin_password(auth, parser)

    if not args.username:
        parser.error("--username is required for portfolio commands.")

    password = getpass.getpass("Admin password: ") if args.username.strip().lower() == "admin" else ""
    try:
        user, temporary_token = auth.login(args.username, password)
    except AuthError as exc:
        parser.error(str(exc))
    else:
        # CLI verifies the same identity as the web app but never persists a
        # browser-style session or accepts admin passwords via command-line args.
        auth.logout(temporary_token)

    store = PortfolioStore(auth.portfolio_db_path(user["id"]))
    service = PortfolioService(store=store)
    if args.command == "sync":
        result = service.sync_daily()
    elif args.command == "performance":
        result = service.performance()
    else:
        result = service.dashboard()
    print(json.dumps(result, indent=2, ensure_ascii=False, default=str))


if __name__ == "__main__":
    main()
