import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "python"))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from portfolio.postgres import PostgresAuthStore, PostgresPortfolioStore
from portfolio.automated_service import AutomatedPortfolioService

PORTFOLIO_NAME = "Audit 34 Archetypes Universe"
USERNAME = "alice"
EVENT_DATE = "2026-08-29"
CASH_DEPOSIT = 10_000_000_000.0  # 10B VND
PRICE = 10_000.0
QUANTITY = 100.0
BROKER = "tcbs"

SYMBOLS = [
    # 34 archetypes, 2 symbols each = 68
    "VCB", "MBB", "SSI", "VCI", "BVH", "PVI", "VEA", "REE", "VHM", "NLG",
    "IDC", "KBC", "CTD", "FCN", "HHV", "CII", "HPG", "HSG", "DGC", "DCM",
    "HT1", "BCC", "KSV", "MSR", "PVD", "PVS", "GAS", "CNG", "BSR", "PLX",
    "PPC", "NT2", "VSH", "CHP", "GEG", "PC1", "BWE", "TDM", "VNM", "MCH",
    "MWG", "FRT", "PNJ", "HAX", "FPT", "CMG", "CTR", "VGI", "DHG", "TNH",
    "GMD", "VSC", "SCS", "VTP", "HAH", "VOS", "VJC", "HVN", "ACV", "AST",
    "BAF", "HAG", "GVR", "PHR", "VHC", "FMC", "MSH", "TCM",
]


def main():
    auth = PostgresAuthStore()
    user = auth.user_by_username(USERNAME)
    if user is None:
        raise SystemExit(f"user {USERNAME} not found")

    # 1. Create the audit portfolio (idempotent by name)
    existing = [p for p in auth.list_portfolios(user["id"]) if p["name"] == PORTFOLIO_NAME]
    if existing:
        portfolio = existing[0]
        print(f"portfolio exists id={portfolio['id']} schema={portfolio['schema_name']}")
    else:
        portfolio = auth.create_portfolio(user["id"], PORTFOLIO_NAME)
        print(f"created portfolio id={portfolio['id']} schema={portfolio['schema_name']}")

    svc = AutomatedPortfolioService(store=PostgresPortfolioStore(user["id"], portfolio["schema_name"]))

    # 2. Check existing events to avoid double-seeding
    existing_events = svc.transactions()
    if existing_events:
        print(f"WARNING: portfolio already has {len(existing_events)} events; aborting to avoid duplicates.")
        raise SystemExit(1)

    # 3. Cash deposit first (ledger invariant: cash >= 0)
    svc.append_event({
        "event_type": "CASH_DEPOSIT",
        "event_date": EVENT_DATE,
        "amount": CASH_DEPOSIT,
        "broker_code": BROKER,
        "note": "Seed capital for 34-archetype audit portfolio",
    }, created_by=USERNAME)
    print(f"deposited {CASH_DEPOSIT:,.0f} VND")

    # 4. 68 BUY transactions
    for idx, symbol in enumerate(SYMBOLS, start=1):
        svc.append_event({
            "event_type": "BUY",
            "event_date": EVENT_DATE,
            "symbol": symbol,
            "quantity": QUANTITY,
            "price": PRICE,
            "fee": 0,
            "tax": 0,
            "broker_code": BROKER,
            "note": f"Audit archetype seed #{idx}",
        }, created_by=USERNAME)
    print(f"added {len(SYMBOLS)} BUY transactions")

    # 5. Verify
    txns = svc.transactions()
    from portfolio.domain import EventType
    buys = [t for t in txns if t["event_type"] == "BUY"]
    symbols = sorted({t["symbol"] for t in buys})
    print(f"TOTAL EVENTS={len(txns)} BUYS={len(buys)} DISTINCT_SYMBOLS={len(symbols)}")
    state = svc.current_state()
    print(f"POSITIONS={len(state.positions)} CASH={float(state.cash):,.0f}")


if __name__ == "__main__":
    main()