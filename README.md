# QPort — Buy & Hold Portfolio Information System

QPort is a bilingual (EN/VI), rule-based portfolio tracker for Vietnamese cash equities.

QPort is intentionally a **portfolio information system**, not a stock-selection,
optimization, allocation-timing or automatic-trading engine.

```text
explicit portfolio events
        ↓
immutable ledger
        ↓
holdings + available cash
        ↑
Vnstock / VNDIRECT D1 prices
        ↓
daily historical snapshots
        ↓
NAV · P/L · TWR · XIRR · drawdown · risk · portfolio health
        ↓
information for the user
```

## Core invariants

- Price movement never changes shares.
- Risk calculations never create BUY/SELL events.
- Calendar time/year-end never changes the portfolio.
- Only explicit ledger events change shares or cash.
- Market-data failures are visible as `STALE` / `MISSING` rather than fabricated fresh values.
- Vietnamese equity prices are stored as canonical **full VND per share**.

## What the system provides

### Portfolio

- Current NAV, equity and available cash.
- Cost value and market value per holding.
- Live unrealized P/L and total portfolio P/L.
- Position weights and risk contribution.
- Quick cash deposit/withdraw recording.
- Rich Portfolio Health diagnostics.

### Performance

After the first market sync QPort reconstructs daily history from the immutable
ledger and stored D1 prices. It provides:

- NAV history;
- daily / MTD / YTD return;
- TWR and annualized TWR;
- XIRR from actual dated investor cash flows;
- current/max drawdown;
- best/worst day and positive-day ratio;
- realized/unrealized P/L, dividends, fees/taxes and contributions.

### Risk

Risk is information only. The page includes:

- 63D / 252D realized volatility;
- concentration and HHI;
- effective number of positions;
- average/max correlation;
- diversification ratio;
- risk contribution and equal-risk (ERC) reference;
- historical daily VaR/CVaR 95%;
- downside volatility and worst observed day;
- data-history coverage.

### Daily snapshots

Snapshots are generated automatically from:

```text
ledger state + daily market prices
```

`OFFICIAL` means every active holding has a price for the same trading date.
Stale snapshots remain visible for diagnosis but are excluded from official
performance calculations.

## Ledger event types

```text
POSITION_IMPORT
CASH_DEPOSIT
CASH_WITHDRAW
BUY
SELL
CASH_DIVIDEND
STOCK_DIVIDEND
SPLIT
FEE
```

`POSITION_IMPORT` is for migrating an existing holding with shares and cost basis
without pretending that a historical cash BUY occurred inside QPort.

The application exposes no normal update/delete API for ledger history. Keep a
backup of the SQLite database before bulk migration.

## Market data

Provider policy:

```text
optional Vnstock
      ↓ fallback
VNDIRECT public D1 data
      ↓ failure
last stored value + STALE/MISSING status
```

Base installation:

```bash
cd python
pip install -r requirements.txt
```

Optional Vnstock:

```bash
pip install -r requirements-vnstock.txt
```

## Start

```bash
cd frontend
npm ci
npm run build
npm run build:ssr

cd ../python
python serve.py
```

Open:

```text
http://127.0.0.1:8080/
```

Navigation:

```text
Portfolio | Transactions | Performance | Risk | Snapshots | Settings | Guide
```

The server runs an idempotent EOD sync at **15:30 Asia/Ho_Chi_Minh** on weekdays.
You can also sync manually from Portfolio, Performance or Snapshots.

For Windows Task Scheduler / cron:

```bash
python -m portfolio.cli sync
```

## First-use workflow

1. Open **Transactions** and import each existing position with the real share count and cost basis.
2. Record existing available cash with **Cash deposit**, or use the cash box on **Portfolio**.
3. Return to **Portfolio** and click **Sync daily prices** once.
4. QPort fetches D1 history and rebuilds daily snapshots from the ledger dates.
5. Verify Cost Value, Market Value, P/L and NAV against your broker.
6. Review **Performance**, **Risk** and **Snapshots** only after the accounting values match.

## Languages

Operational UI:

```text
EN — English
VI — Tiếng Việt
```

The language is stored in the `qport_lang` browser cookie.

## Complete guides

- English: [`docs/USER_GUIDE_EN.md`](docs/USER_GUIDE_EN.md)
- Vietnamese: [`docs/USER_GUIDE_VI.md`](docs/USER_GUIDE_VI.md)
- In-app: `/guide`

See also [`BUY_AND_HOLD_SYSTEM_SPEC.md`](BUY_AND_HOLD_SYSTEM_SPEC.md).
