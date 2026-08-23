# QPort Python Architecture

The Python application now has two intentionally separate domains.

## 1. Operational core — `portfolio/`

This is the production Buy & Hold information system.

```text
portfolio/
  domain.py        immutable event/state contracts
  storage.py       SQLite ledger, market prices, snapshots
  accounting.py    deterministic event replay
  market_data.py   Vnstock/VNDIRECT provider adapters
  analytics.py     TWR, XIRR, drawdown helpers
  risk.py          informational volatility/concentration/ERC diagnostics
  service.py       application use cases
  scheduler.py     daily EOD market sync
  cli.py           sync/status/performance CLI
```

The operational invariant is:

```text
only explicit ledger events change holdings or cash
```

Market data, risk calculations, year-end and research output cannot change the
portfolio.

Primary commands:

```bash
python main.py status
python main.py sync
python main.py performance
python serve.py
```

`serve.py` launches the Buy & Hold web product and an optional 15:30 Vietnam EOD
sync scheduler.

Operational database:

```text
python/data/portfolio.sqlite3
```

Override with `PORTFOLIO_DB`.

### Market-data dependencies

Base install:

```bash
pip install -r requirements.txt
```

This includes VNDIRECT support.

Optional Vnstock:

```bash
pip install -r requirements-vnstock.txt
```

Vnstock is loaded lazily. Its absence cannot prevent portfolio accounting from
running.

## 2. Research Lab — `backtest/` and research entrypoints

The previous optimizer architecture is retained for research only:

```text
backtest/
optimize_main.py
research_main.py
research_legacy_server.py
```

It contains ERC/Shannon simulations, Dynamic Alpha, candidate search, NSGA-II,
surrogate ranking, walk-forward validation and holdout reports.

Research may produce evidence or proposals, but there is no code path that writes
a research winner directly into the operational ledger.

Web research routes:

```text
/research
/research/optimizer
```

Old `/optimizer` URLs are compatibility aliases only.

## 3. Operational API

```text
GET  /api/portfolio
GET  /api/portfolio/transactions
POST /api/portfolio/transactions
POST /api/portfolio/sync
GET  /api/portfolio/performance
GET  /api/portfolio/risk
GET  /api/portfolio/snapshots
POST /api/portfolio/reference-weights
```

There is no auto-rebalance or optimizer-apply endpoint.

## 4. Ledger events

Supported operational events:

```text
POSITION_IMPORT
BUY
SELL
CASH_DEPOSIT
CASH_WITHDRAW
CASH_DIVIDEND
STOCK_DIVIDEND
SPLIT
FEE
```

The store deliberately has no update/delete method for ledger events. Use
compensating events for corrections.

## 5. Testing

Operational tests are dataset-independent:

```bash
python -m pytest portfolio/tests -q
python -m compileall -q portfolio buyhold_server.py serve.py main.py
```

Frontend:

```bash
cd ../frontend
npm ci
npm run build
npm run build:ssr
node test/smoke.mjs
```

Heavy research regressions are separate and can be run manually when research
code changes.

## 6. Canonical documentation

Read:

- `../BUY_AND_HOLD_SYSTEM_SPEC.md`
- `../user-guide.md`

The old allocation implementation specification is deprecated for operational
development.
