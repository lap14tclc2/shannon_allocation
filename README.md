# QPort — Buy & Hold Portfolio Information System

QPort is a bilingual (EN/VI), rule-based portfolio tracker for Vietnamese cash equities.

QPort is intentionally a **portfolio information system**, not a stock-selection,
optimization, allocation-timing or automatic-trading engine.

```text
authenticated user
        ↓
private SQLite portfolio book
        ↓
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

## Authentication and data isolation

QPort uses a deliberately small local authentication model:

- Normal users register a **unique username** and sign in with username only.
- The built-in admin account requires a password; QPort never displays that credential in the UI, docs or startup output.
- Admin can update the password from `/admin`.
- Admin can remove a normal user; removal also deletes that user's sessions and entire portfolio database.
- Every normal user gets a separate SQLite portfolio file. Transactions, prices, snapshots, dividends, operations, logs and settings are therefore isolated by authenticated user.
- Admin is an administration-only identity. It is always routed to `/admin`, cannot open portfolio pages, and cannot call `/api/portfolio/**`.

Default runtime storage:

```text
python/data/auth-v1/auth.sqlite3
python/data/auth-v1/users/user-<id>.sqlite3
```

The pre-auth single-user `python/data/portfolio.sqlite3` is removed when the authenticated server starts. The authenticated namespace therefore starts clean instead of silently inheriting old single-user data.

## Core invariants

- Price movement never changes shares.
- Risk calculations never create BUY/SELL events.
- Calendar time/year-end never changes the portfolio.
- Only explicit ledger events change shares or cash.
- Market-data failures are visible as `STALE` / `MISSING` rather than fabricated fresh values.
- Vietnamese equity prices are stored as canonical **full VND per share**.
- A portfolio API request must have an authenticated normal-user session before any user portfolio database is opened.

## What the system provides

### Portfolio

- Current NAV, equity and available cash.
- Cost value and market value per holding.
- Live unrealized P/L and total portfolio P/L.
- Position weights.
- Concise portfolio-level risk/health assessment.
- Dividend latest event with expandable stored history for every current holding.
- Expandable holding rows with broker/account source breakdown from open tax lots.

### Performance

After the first market sync QPort reconstructs daily history from the immutable
ledger and stored D1 prices. It provides:

- NAV history;
- YTD and since-inception performance in the normal view;
- TWR / XIRR and detailed methodology behind progressive disclosure;
- current/max drawdown;
- realized/unrealized P/L, dividends, fees/taxes and contributions.

### Risk

Risk is information only. The advanced route includes:

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

## Market data

Provider policy:

```text
optional Vnstock
      ↓ fallback
VNDIRECT public D1 data
      ↓ failure
last stored value + STALE/MISSING status
```

Dividend provider results are persisted in the logged-in user's SQLite DB. Normal page loads use SQLite first; providers are contacted only on cache miss or explicit refresh.

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

The start page asks for username. If the username is unknown, QPort shows the registration field. Normal users need no password. Entering the admin username reveals the admin password field, but QPort never prints or renders the password value.

Normal-user primary navigation:

```text
Portfolio | Transactions | Performance | Guide
```

Advanced routes remain available for normal-user operational diagnostics. Admin has an administration-only page and is always routed to `/admin`.

The server runs an idempotent EOD sync at **15:30 Asia/Ho_Chi_Minh** on weekdays for normal-user databases that exist. You can also sync manually from the portfolio UI.

## CLI

CLI operations are authenticated and use the same per-user database mapping as the web app.

Normal user:

```bash
python -m portfolio.cli --username alice sync
python -m portfolio.cli --username alice status
```

Do not put admin passwords in documentation, scripts or shell examples.

## First-use workflow

1. Open QPort and register a unique username, or sign in if already registered.
2. Open **Transactions** and import each existing position with the real share count and cost basis.
3. Record existing available cash with **Cash deposit**.
4. Return to **Portfolio** and refresh market data once.
5. Verify Cost Value, Market Value, P/L and NAV against your broker.
6. Review the Portfolio assessment and Performance only after accounting values match.
7. Admin signs in separately and remains on `/admin` for user management and password changes only.

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
