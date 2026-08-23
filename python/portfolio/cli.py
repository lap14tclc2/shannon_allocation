from __future__ import annotations

import argparse
import json

from .service import PortfolioService


def main() -> None:
    parser = argparse.ArgumentParser(description="Buy-and-hold portfolio operations")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("sync", help="Fetch daily prices and create a portfolio snapshot")
    sub.add_parser("status", help="Print current portfolio dashboard JSON")
    sub.add_parser("performance", help="Print performance JSON")
    args = parser.parse_args()

    service = PortfolioService()
    if args.command == "sync":
        result = service.sync_daily()
    elif args.command == "performance":
        result = service.performance()
    else:
        result = service.dashboard()
    print(json.dumps(result, indent=2, ensure_ascii=False, default=str))


if __name__ == "__main__":
    main()
