# QPort Python Architecture

QPort has one production domain: the Buy & Hold portfolio information system.

```text
portfolio/
  domain.py        immutable ledger/state contracts
  storage.py       SQLite ledger, market prices, daily snapshots
  accounting.py    deterministic event replay and cost basis
  market_data.py   optional Vnstock + VNDIRECT D1 providers
  analytics.py     TWR, XIRR and return helpers
  risk.py          informational portfolio/risk diagnostics
  locale.py        EN/VI locale resolution
  service.py       portfolio use cases and historical rebuild
  scheduler.py     EOD data/snapshot sync
  cli.py           local status/sync/performance commands

buyhold_server.py  standalone operational HTTP/SSR server
serve.py            primary web entrypoint
main.py             primary CLI entrypoint
```

## Invariant

```text
only explicit ledger events change holdings or cash
```

Market prices, risk calculations, time and UI information cannot create trades.

## Commands

```bash
python main.py status
python main.py sync
python main.py performance
python serve.py
```

The web server starts an optional idempotent EOD sync at 15:30
`Asia/Ho_Chi_Minh`.

## Database

Default:

```text
python/data/portfolio.sqlite3
```

Override:

```text
PORTFOLIO_DB=/path/to/portfolio.sqlite3
```

The ledger is immutable from normal application APIs. Market prices and snapshots
are derived/rebuildable data.

## Market data

Base installation uses VNDIRECT:

```bash
pip install -r requirements.txt
```

Optional Vnstock:

```bash
pip install -r requirements-vnstock.txt
```

Provider failure never changes holdings. It produces explicit stale/missing data
quality instead.

## Historical rebuild

`PortfolioService.sync_daily()` performs two jobs:

1. sync D1 prices for every symbol that exists in the ledger;
2. rebuild derived daily portfolio snapshots from ledger dates and stored prices.

This means a user does not need to run QPort every day from the date of purchase.
After importing holdings with honest dates and syncing once, QPort reconstructs the
available daily history.

The rebuild calculates:

- NAV and equity/cash;
- external-flow-neutral daily return;
- TWR index;
- current/max drawdown;
- total P/L;
- snapshot data quality.

`OFFICIAL` snapshots require an exact price for every active holding on the same
trading date.

## Risk

`portfolio/risk.py` is information only. It calculates:

- 63D / 252D volatility;
- capital concentration / HHI / effective positions;
- average/max correlation;
- diversification ratio;
- portfolio risk contribution;
- equal-risk (ERC) reference weights;
- historical daily VaR/CVaR 95%;
- downside volatility;
- worst observed day and positive-day ratio;
- history coverage.

No risk function creates BUY/SELL events.

## Web routes

```text
/              Portfolio
/transactions  Immutable ledger
/performance   Return/P&L/drawdown history
/risk          Risk diagnostics
/snapshots     Derived daily checkpoints
/settings      Optional guidance preferences
/guide         EN/VI guide
```

## API

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

There is no optimizer, research, auto-rebalance or automatic-execution API.

## Locale

```text
en — English
vi — Tiếng Việt
```

The locale is presentation state stored in the `qport_lang` browser cookie and
cannot affect portfolio calculations.

## Testing

```bash
python -m compileall -q portfolio buyhold_server.py serve.py main.py
python -m pytest portfolio/tests -q

cd ../frontend
npm ci
npm run build
npm run build:ssr
node test/smoke.mjs
```

## Documentation

- `../BUY_AND_HOLD_SYSTEM_SPEC.md`
- `../docs/USER_GUIDE_EN.md`
- `../docs/USER_GUIDE_VI.md`
