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

## Authentication and security model

QPort uses a deliberately small local authentication model:

- Normal users register a **unique username** and sign in with username only.
- The admin username is `admin`, but **no admin password is embedded in source, UI, docs or logs**.
- Configure the admin password once, locally, with `python -m portfolio.cli setup-admin`.
- Admin passwords are stored only as salted PBKDF2-HMAC-SHA256 hashes.
- Admin can update the password from `/admin`; rotation invalidates active admin sessions.
- Admin can remove a normal user; removal also deletes that user's sessions and entire portfolio database.
- Every user gets a separate SQLite portfolio file. Transactions, prices, snapshots, dividends, operations, logs and settings are therefore isolated by authenticated user.

> **Important:** username-only normal-user login is intended for localhost or a trusted private network. It is not strong authentication for an untrusted/public network.

Default runtime storage:

```text
python/data/auth-v1/auth.sqlite3
python/data/auth-v1/users/user-<id>.sqlite3
```

The pre-auth single-user `python/data/portfolio.sqlite3` is removed when the authenticated server starts.

### HTTP protections

The authenticated server also applies:

- HttpOnly + SameSite session cookies;
- optional Secure cookies with `QPORT_SECURE_COOKIES=1` behind HTTPS;
- same-origin request markers and Origin/Sec-Fetch-Site checks for mutations;
- Content Security Policy and anti-clickjacking headers;
- request-body size limits;
- admin login throttling;
- localhost-only binding by default.

A non-loopback bind is refused unless `--allow-trusted-network` is explicitly supplied.

## Core invariants

- Price movement never changes shares.
- Risk calculations never create BUY/SELL events.
- Calendar time/year-end never changes the portfolio.
- Only explicit ledger events change shares or cash.
- Market-data failures are visible as `STALE` / `MISSING` rather than fabricated fresh values.
- Vietnamese equity prices are stored as canonical **full VND per share**.
- A portfolio API request must have an authenticated session before any user portfolio database is opened.

## What the system provides

### Portfolio

- Current NAV, equity and available cash.
- Cost value and market value per holding.
- Live unrealized P/L and total portfolio P/L.
- Position weights.
- Expandable broker/account breakdown for each consolidated holding.
- Concise portfolio-level risk/health assessment.
- Dividend latest event with expandable stored history for every current holding.

### Performance

After the first market sync QPort reconstructs daily history from the immutable ledger and stored D1 prices. It provides:

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

`POSITION_IMPORT` is for migrating an existing holding with shares and cost basis without pretending that a historical cash BUY occurred inside QPort.

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

## Install

```bash
cd python
pip install -r requirements.txt
```

Optional Vnstock:

```bash
pip install -r requirements-vnstock.txt
```

Frontend:

```bash
cd frontend
npm ci
npm run build
npm run build:ssr
```

## First secure start

Configure admin locally. The password is prompted without appearing in shell history or the process list:

```bash
cd python
python -m portfolio.cli setup-admin
```

Then start QPort:

```bash
python serve.py
```

Open:

```text
http://127.0.0.1:8080/
```

The start page asks for username. If the username is unknown, QPort shows the registration field. Normal users need no password. Entering `admin` reveals the admin password field.

Primary navigation:

```text
Portfolio | Transactions | Performance | Guide
```

Advanced routes remain available for operational diagnostics. Admin gets an additional **Admin** link after login.

The server runs an idempotent EOD sync at **15:30 Asia/Ho_Chi_Minh** on weekdays for every user database that exists.

## CLI

CLI operations use the same per-user database mapping as the web app.

Normal user:

```bash
python -m portfolio.cli --username alice sync
python -m portfolio.cli --username alice status
```

Admin commands prompt for the password interactively:

```bash
python -m portfolio.cli --username admin status
```

Do not pass admin passwords as command-line arguments.

## Trusted-network deployment

QPort defaults to loopback binding because normal users authenticate with username only. If you intentionally run it on a trusted private network:

```bash
python serve.py --host 192.168.1.10 --allow-trusted-network
```

When HTTPS is provided by a reverse proxy, also enable secure cookies:

```text
QPORT_SECURE_COOKIES=1
```

Do not expose the current username-only normal-user model directly to the public Internet.

## First-use portfolio workflow

1. Register/sign in with the intended username.
2. Open **Transactions** and import each existing position with the real share count, cost basis, broker and account where known.
3. Record existing available cash with **Cash deposit**.
4. Return to **Portfolio** and refresh market data once.
5. Verify Cost Value, Market Value, P/L and NAV against your broker.
6. Review the Portfolio assessment and Performance only after accounting values match.

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
