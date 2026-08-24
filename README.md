# QPort — Vercel / PostgreSQL Edition

This branch is the Vercel-native implementation of **QPort — Buy & Hold Portfolio Information System**.

> Branch boundary: `vercel-migration` is Vite SPA + FastAPI + PostgreSQL + Vercel Cron. The long-running Python/SQLite/Node-SSR runtime remains on `main` and is not the production architecture of this branch.

QPort is bilingual (EN/VI), rule-based, and designed for Vietnamese cash-equity portfolio tracking. It is an information/accounting system, **not** an optimizer, allocation timer, stock selector or automatic trading engine.

```text
Browser
  │
  ▼
Vite / React SPA
  │ same-origin /api/*
  ▼
FastAPI
  │
  ├── Windows local → native PostgreSQL
  │
  └── Vercel → Neon PostgreSQL

Vercel Cron (daily after VN market close)
  └── /api/cron/daily-sync
```

## Why this branch exists

The previous runtime depended on a long-running Python HTTP server, local SQLite files, a spawned Node SSR worker and an in-process scheduler. Those assumptions are a poor fit for serverless hosting.

The Vercel version changes the infrastructure boundary while preserving QPort's deterministic Python business engine:

- **React UI:** normal Vite SPA; no runtime Node SSR worker.
- **HTTP/API:** FastAPI at `api/index.py`.
- **Persistence:** PostgreSQL through `DATABASE_URL`.
- **Isolation:** one PostgreSQL schema per normal user, preserving the old one-database-per-user isolation model.
- **Scheduling:** one Vercel Cron invocation per day; no forever-running scheduler thread.
- **Windows local development:** native PostgreSQL only.
- **Vercel preview/production:** Neon PostgreSQL through `DATABASE_URL`.

## Non-negotiable portfolio invariants

- Price movement never changes shares.
- Risk calculations never create BUY/SELL events.
- Calendar time/year-end never changes the portfolio.
- Only explicit effective ledger events change holdings/cash.
- Provider failure cannot mutate historical holdings.
- Holdings and Transactions share one effective ledger; there is no second holdings source of truth.
- Risk is diagnostic/informational only. ERC is an advanced reference, not a target allocation.
- Portfolio performance is built from actual tracked snapshots/ledger history, not backdated from market history before ownership.
- Dividend/corporate-action posting remains idempotent and auditable.

## PostgreSQL model

Authentication is stored in:

```text
qport_auth.users
qport_auth.sessions
```

Each normal user owns an isolated portfolio schema:

```text
qport_user_<user-id>
```

That schema contains the existing QPort ledger, prices, snapshots, tax lots, dividends, reconciliation, security master, activity chain and other institutional-lite tables.

This design intentionally mirrors the old `user-<id>.sqlite3` isolation model, so the accounting/domain layer does not need a cross-cutting `user_id` column added to every table.

## Authentication

- Normal users register/sign in with a unique username only.
- Admin remains administration-only and cannot access portfolio APIs.
- Admin password is stored as PBKDF2 hash.
- On the first Vercel deployment, set `QPORT_ADMIN_PASSWORD`; the application never renders that value.
- Session cookie is HttpOnly + SameSite=Lax and Secure on Vercel.

## Runtime routes

Primary UI:

```text
/               Portfolio
/transactions
/performance
/guide
```

Advanced normal-user routes remain available but are not primary navigation:

```text
/risk
/snapshots
/operations
/logs
/settings
```

Admin:

```text
/admin
```

API:

```text
/api/*
```

Health check:

```text
GET /api/health
```

## Local development — Windows native PostgreSQL

Requirements:

- Python 3.12+
- Node.js 22+
- PostgreSQL 16+ installed natively on Windows

Install application dependencies once:

```powershell
pip install -r python/requirements.txt
cd frontend
npm ci
cd ..
```

Install PostgreSQL for Windows and ensure the PostgreSQL service and `psql` are available.

Initialize the QPort development role/database once from the repository root:

```powershell
psql -U postgres -f scripts/setup-postgres-native.sql
```

The bootstrap creates the local development database:

```text
user:     qport
password: qport
database: qport
host:     127.0.0.1
port:     5432
```

Start QPort:

```powershell
.\scripts\dev-vercel.ps1
```

The launcher defaults to:

```text
postgresql://qport:qport@127.0.0.1:5432/qport
```

It performs a PostgreSQL connectivity check before starting FastAPI and Vite, so a stopped PostgreSQL service or missing QPort database fails early with setup guidance.

To use another native/local PostgreSQL instance:

```powershell
.\scripts\dev-vercel.ps1 -DatabaseUrl "postgresql://USER:PASSWORD@HOST/DB"
```

Open:

```text
http://localhost:3000
```

The Vite dev server proxies `/api/*` to FastAPI on `127.0.0.1:8000`.

## Environment variables

Copy `.env.vercel.example` as a reference. Vercel needs at least:

```text
DATABASE_URL=<Neon PostgreSQL URL>
QPORT_ADMIN_PASSWORD=<strong first-deploy password>
CRON_SECRET=<long random value>
```

Optional:

```text
QPORT_API_DOCS=0
QPORT_COOKIE_SECURE=1
```

For local plain HTTP:

```text
QPORT_COOKIE_SECURE=0
```

For Vercel, use the Neon PostgreSQL connection string for `DATABASE_URL`; use the pooled connection string when Neon recommends it for serverless workloads.

Local native PostgreSQL is development-only. Do not point normal local development at the production Neon database.

## Migrate existing SQLite data

The old local data layout can be moved into PostgreSQL without fabricating portfolio events:

```text
python/data/auth-v1/auth.sqlite3
python/data/auth-v1/users/user-<id>.sqlite3
```

Run once from the repository root:

```bash
DATABASE_URL='postgresql://...' python scripts/migrate_sqlite_to_postgres.py
```

The migration maps:

```text
auth.sqlite3   → qport_auth
user-2.sqlite3 → qport_user_2
user-3.sqlite3 → qport_user_3
```

It preserves table rows/IDs where possible, resets PostgreSQL sequences and clears old browser sessions so users sign in again on the new domain.

If target QPort schemas already exist, migration aborts. `--replace` is intentionally destructive and should only be used when you explicitly want to replace a previous migration target.

## Deploy to Vercel

The root `vercel.json` builds `frontend/dist`, packages `api/index.py` as the Python function, rewrites application routes to the SPA, and registers the daily sync cron.

Production/preview deployment model:

```text
Vercel
  ├── Vite static SPA
  ├── FastAPI Python Function
  └── Vercel Cron
          │
          ▼
      Neon PostgreSQL
```

Typical flow:

1. Create a Neon PostgreSQL database/branch for the Vercel environment.
2. Add the Neon `DATABASE_URL`, `QPORT_ADMIN_PASSWORD`, and `CRON_SECRET` in Vercel project settings.
3. Import this GitHub repository into Vercel.
4. Deploy **`vercel-migration`** as a Preview branch first.
5. Verify `/api/health`, login, transaction create/edit/delete, Portfolio, Performance, Risk and mobile navigation.
6. If you want this branch to be production without merging, set the Vercel Production Branch to `vercel-migration`.

The Hobby cron is intentionally once per day. `0 9 * * *` means 09:00 UTC, approximately the 16:00 Vietnam hour after market close. Do not depend on minute-level precision on Vercel Hobby.

## Market data

Provider policy remains:

```text
optional Vnstock when available
      ↓ fallback
VNDIRECT D1 HTTP provider
      ↓ failure
stored history + explicit stale/missing status
```

The base Vercel dependency set intentionally does not require Vnstock. The direct VNDIRECT provider lets the serverless runtime continue fetching D1 data without a persistent child process. Vnstock remains optional for environments where its dependency/runtime constraints are acceptable.

Initial history sync still backfills roughly 550 calendar days when needed and treats >=260 stored bars as the primary D1 risk-readiness target.

## Performance and risk

Performance remains based on actual QPort ownership/accounting history:

- TWR / annualized TWR when evidence is mature;
- XIRR when supported;
- drawdown and daily return statistics;
- realized/unrealized P/L;
- contributions, fees/taxes and dividend income.

Risk remains based on stored D1 market returns and current equity weights:

- 63D / 252D realized volatility;
- covariance/correlation;
- HHI/effective positions;
- risk contribution;
- diversification ratio;
- historical VaR/CVaR;
- downside volatility;
- ERC diagnostic reference.

No risk result creates a trade.

## CLI

The branch CLI uses the same PostgreSQL authentication and per-user schema routing as the FastAPI runtime:

```bash
DATABASE_URL='postgresql://...' python -m portfolio.cli --username alice status
DATABASE_URL='postgresql://...' python -m portfolio.cli --username alice sync
```

Admin remains blocked from portfolio CLI operations.

## Tests

Branch CI runs:

- the existing deterministic portfolio/accounting regression suite;
- a real PostgreSQL 16 service on the GitHub Actions runner;
- PostgreSQL auth/user-schema/isolation smoke tests;
- frontend validation and AI-export contracts;
- Vite production build.

The CI PostgreSQL service is test infrastructure on GitHub Actions, not a supported local Docker runtime.

The migration is not considered validated merely because source files compile; PostgreSQL integration evidence is required.

## Guides

- English user guide: [`docs/USER_GUIDE_EN.md`](docs/USER_GUIDE_EN.md)
- Vietnamese user guide: [`docs/USER_GUIDE_VI.md`](docs/USER_GUIDE_VI.md)
- In-app guide: `/guide`
- System specification: [`BUY_AND_HOLD_SYSTEM_SPEC.md`](BUY_AND_HOLD_SYSTEM_SPEC.md)

For AI/developer handoff, read `AI_WORKING_CONTEXT.md` and then `AI_WORKING_CONTEXT_LATEST.md`. On this branch, the Vercel/PostgreSQL architecture in this README and latest handoff overrides historical SQLite/server-runtime notes.
