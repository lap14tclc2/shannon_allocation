# QPort — Buy & Hold Portfolio Information System

QPort is a bilingual (EN/VI), rule-based portfolio tracker for Vietnamese cash equities.

QPort is intentionally a **portfolio information system**, not a stock-selection,
optimization, allocation-timing or automatic-trading engine.

```text
authenticated user
        ↓
private SQLite portfolio book
        ↓
validated user/system portfolio events
        ↓
immutable/correctable ledger
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
- Only validated ledger events change shares or cash. This includes user transactions and due corporate-action events posted by the dividend automation.
- Market-data failures are visible as `STALE` / `MISSING` rather than fabricated fresh values.
- Vietnamese equity prices are stored as canonical **full VND per share**.
- A portfolio API request must have an authenticated normal-user session before any user portfolio database is opened.
- Holdings, Transactions and derived history share one effective ledger; a transaction create/edit/delete is reflected in Holdings on the next render without a second holdings source of truth.

## What the system provides

### Portfolio

- Current NAV, equity and available cash.
- Cost value and market value per holding.
- Live unrealized P/L and total portfolio P/L.
- Position weights.
- Concise portfolio-level risk/health assessment with explicit data-readiness messages.
- Dividend announcement/history tracking for every current holding.
- A separate expandable **Dividends received** ledger view with gross cash, withholding tax, net cash and stock shares received.
- Expandable holding rows with broker/account source breakdown from open tax lots.
- Full-width working tables on tablet/desktop while retaining horizontal scrolling on narrow mobile screens.

### Performance

After the first market sync QPort reconstructs daily history from the immutable
ledger and stored D1 prices. It provides:

- NAV history;
- daily, MTD, YTD and since-inception performance;
- TWR / annualized TWR / XIRR and cash-flow-quality status;
- current/max drawdown, best/worst day and positive-day ratio;
- realized/unrealized P/L, dividends, fees/taxes and contributions;
- gross cash-dividend income, 5% withholding, net cash-dividend income and stock-dividend tax paid on sale;
- history-readiness milestones so missing statistics are not mistaken for zero risk/return.

### Risk

Risk is information only. The advanced route includes:

- 63D / 252D realized volatility and short-vs-long volatility regime;
- concentration and HHI;
- effective number of positions;
- average/max correlation and interpretation;
- diversification ratio;
- risk contribution and equal-risk (ERC) diagnostic reference;
- historical daily VaR/CVaR 95%;
- downside volatility and worst observed day;
- data-history coverage, eligible/missing symbols and explicit readiness messaging.

Initial market sync backfills roughly **550 calendar days** of D1 history when needed so risk analytics are not limited to only a few days around the first portfolio import. Once a symbol has enough stored history, later syncs are incremental.

### Dividend automation and tax

Corporate-action discovery remains provider-driven and idempotent. For a supported cash/stock dividend with a known `payment_date`, QPort automatically creates the matching ledger event when the payment date is due. A mixed event such as cash + stock creates separate `CASH_DIVIDEND` and `STOCK_DIVIDEND` transactions.

Entitlement quantity is calculated from the portfolio state before the ex-date (record date is the fallback when ex-date is unavailable). Automatic posting is protected by `corporate_action_postings`, so the same component is not posted twice.

QPort applies the configured Vietnamese individual dividend-tax policy used by this system:

- cash dividend: record the **gross** entitlement, withhold **5%**, add only the **net** amount to cash, and keep the withholding in `fees_and_taxes`;
- stock dividend: no investment-income tax is charged when shares are received;
- when taxable stock-dividend shares are later sold, QPort adds **5% investment-income tax** using VND 10,000 par value per taxable share, or the lower transfer price when the share is sold below par;
- ordinary securities-transfer tax is a separate tax. Any user-entered SELL tax remains additive to the stock-dividend tax.

The stock-dividend tax engine tracks an outstanding taxable-share pool and consumes it on later transfers until the dividend-share quantity has been exhausted.

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

The scheduler runs at **15:30 Asia/Ho_Chi_Minh**. D1 market sync/rebuild is performed on weekdays; corporate-action discovery and due-dividend posting are checked every calendar day for normal-user databases. You can also sync manually from the portfolio UI.

## CLI

CLI operations are authenticated, use the same per-user database mapping as the web app, and use the same dividend-aware service/tax policy.

Normal user:

```bash
python -m portfolio.cli --username alice sync
python -m portfolio.cli --username alice status
```

Do not put admin passwords in documentation, scripts or shell examples.

## First-use workflow

1. Open QPort and register a unique username, or sign in if already registered.
2. Open **Transactions** and import each existing position with the real share count and cost basis; include broker/account when known.
3. Record existing available cash with **Cash deposit**.
4. Return to **Portfolio** and refresh market data once. QPort backfills enough D1 history for meaningful risk diagnostics where the provider can supply it.
5. Verify Cost Value, Market Value, P/L and NAV against your broker.
6. Review the Portfolio assessment, advanced Risk and Performance only after accounting values match.
7. Keep the server/scheduler running so market data and due dividend events remain current.
8. Admin signs in separately and remains on `/admin` for user management and password changes only.

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
