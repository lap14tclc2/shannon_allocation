---
id: TASK-20260826-004
title: Finance DB-first valuation, dividend reconciliation, and scalable admin logs
status: in_progress
priority: P0
created: 2026-08-26
updated: 2026-08-26
tags: [finance-data, valuation, dividend, reconciliation, observability, postgres, vercel]
related:
  - docs/finance-data-sync.md
  - docs/dividend-cache-reconciliation.md
  - docs/tasks/TASK-20260826-001-admin-finance-data.md
  - docs/tasks/TASK-20260826-003-admin-logs-pagination.md
---

## Requirement

Finish the audited Finance Data architecture on branch `dev`.

Users must never crawl financial statements or valuation providers from Vercel. They must read only validated, database-backed records. If data is missing or insufficient, the UI must clearly say `contact admin`.

Admin crawling remains local/external-worker only. Logs must scale without loading every portfolio log into application memory.

## Audit Baseline

Audited branch: `dev`, ahead of `main` by:

- `a14374a` — finance periods and readiness filtering
- `fe4a1aa` — valuation reload error handling

Verified improvements:

- Current incomplete FY is no longer generated.
- Current-year completed quarters are generated.
- Dividend documents are no longer generated per quarter.
- User Finance Data read rejects records unless at least one document is `SUCCESS`.
- Valuation initial load and manual reload both clear loading state after an error.

## Confirmed Remaining Problems

### 1. Valuation still depends on live provider crawling

`app/main.py::portfolio_symbol_valuation` calls `run_valuation_snapshot()`.

On Vercel this intentionally returns `VALUATION_CRAWL_DISABLED_ON_VERCEL`, before Finance DB records can be consumed. The frontend also describes data as being loaded directly and calls the endpoint with `fresh=<timestamp>`.

### 2. Finance documents are raw payloads, not valuation-ready canonical data

`qport_finance.documents` stores payload/source metadata, but no parser/normalizer turns successful balance sheet, income statement, cash-flow and dividend records into canonical facts usable by `ValuationEngine`.

### 3. Dividend crawl duplicates the same history request

The TCBS/CafeF dividend endpoints return history. Current code requests the same all-history endpoint once for every prior FY placeholder. This duplicates provider traffic and stores equivalent payloads under several annual periods.

### 4. Reconciliation pipeline is not connected to ingestion/read paths

`python/portfolio/dividend_reconciliation.py` defines normalize/reconcile/conflict tables, but Finance Data ingestion and normal user dividend reads do not invoke it. Canonical/conflict records therefore cannot govern user output.

### 5. Admin log pagination is still in memory

`app/main.py::admin_logs` loops through every user and portfolio, calls `list_activity(..., limit=5000)`, appends rows to a Python list, then filters/sorts/paginates. This will not scale and can exhaust serverless time/memory.

### 6. Production Admin UI exposes local-only crawling actions

Finance Data UI should state the current runtime capability. On Vercel, crawl/universe/retry controls must be disabled with an explanation rather than letting users click and receive a runtime exception.

## Constraints and Invariants

- Do not use hard-coded financial profile, price, share-count, sector, DCF input, or fallback valuation values.
- Do not call TCBS, CafeF, Vnstock, VPS, or any crawler from a normal user request in production.
- Vercel is database read-only for finance ingestion.
- Ledger events remain the only source of changes to holdings/cash.
- Raw market price remains separate from adjusted return/corporate-action data.
- Missing/stale/conflicted data must be exposed as unavailable; never fabricate a valuation.
- A normal user cannot access admin logs, crawl queues, provider errors, or raw admin-only evidence.
- Never treat `PENDING` or `FAILED` as usable financial data.
- All admin endpoints require `require_admin`.

## Implementation Tasks

### A. Define a database-backed financial-read contract

1. Add a canonical finance-facts table in `qport_finance` with:
   - symbol, statement type, period type/end/year/quarter;
   - line-item code and normalized VND value;
   - source document ID/provider;
   - quality status, provenance and observed/fetched time;
   - uniqueness/indexes for symbol + identity key.
2. Add document parsing/normalization adapters for TCBS and CafeF.
3. Persist only parseable facts; retain raw payload as evidence.
4. Record parse failure separately from crawl failure.
5. Produce a data-readiness result per symbol covering required valuation inputs:
   - market price;
   - net income;
   - shares outstanding;
   - cash/debt;
   - depreciation/CAPEX when available.
6. Return `FINANCE_DATA_MISSING` / `FINANCE_DATA_INCOMPLETE` with user-safe `contact admin` messaging.

### B. Replace live valuation with Finance DB valuation

1. Remove live-provider calls from `/api/portfolio/valuation/{symbol}`.
2. Load canonical facts from `qport_finance` plus the portfolio's stored market price.
3. Build `ValuationEngine` input only from validated facts.
4. Return:
   - report + factual provider/fetched-at metadata when ready;
   - an explicit unavailable/incomplete response when not ready;
   - no fallback values.
5. Update `ValuationPage` wording:
   - remove “tải mới trực tiếp”;
   - replace refresh with “Làm mới dữ liệu đã đồng bộ” or remove it;
   - show `contact admin` for missing finance data.
6. Keep valuation informational only; never emit BUY/SELL action.

### C. Make dividend ingestion canonical

1. Fetch each provider history endpoint at most once per symbol per crawl run.
2. Split/associate individual dividend events by their actual effective year after normalization.
3. Call `normalize_observation` / `persist_observations` / `reconcile_symbol` after successful source ingestion.
4. User dividend reads must use canonical, non-conflicted records.
5. If sources conflict, preserve evidence and show a safe “needs review” state; do not silently choose a value for accounting.
6. Keep the existing provider-fetch toggle so cache-aside can be disabled later for admin-only operation.

### D. Make Admin Logs database-paginated

1. Replace cross-schema load-all behavior with SQL-level filtering and pagination.
2. Implement stable ordering by `occurred_at DESC, id DESC`.
3. Add indexes needed for time, status, category, actor and portfolio/user filters.
4. Use a count query only where the UI needs total pages; consider cursor pagination for high-volume mode.
5. Preserve chain-integrity verification without verifying every historical row on each page request.
6. Retain admin-only authorization and never expose logs through user portfolio routes.

### E. Runtime-aware Finance Data UI

1. Expose a read-only runtime capability flag from admin Finance Data API.
2. On Vercel:
   - disable crawl, retry and universe-sync controls;
   - show “Crawl chạy bằng Local/Worker; production chỉ đọc database.”
3. On local worker runtime:
   - allow crawl/retry/universe sync;
   - surface queue/run status.
4. Ensure disabled UI is not the only protection: backend must continue to reject Vercel crawling.

## Acceptance Criteria

- [ ] No normal user route imports or calls provider crawler code.
- [ ] Valuation succeeds from Finance DB when required canonical facts exist.
- [ ] Valuation returns an explicit user-safe missing/incomplete result when facts do not exist.
- [ ] Vercel valuation never attempts Vnstock/TCBS/CafeF/VPS network crawling.
- [ ] No valuation result contains hard-coded profile/fallback values.
- [ ] Finance crawler creates no current incomplete FY document.
- [ ] Finance crawler creates no quarterly `DIVIDEND` document.
- [ ] One symbol/provider dividend history is fetched at most once per crawl run.
- [ ] Conflicting dividend values produce a conflict record and are excluded from automatic canonical consumption.
- [ ] `/api/admin/logs?page=2` does not load all portfolios' 5,000-row logs into Python memory.
- [ ] Non-admin access to logs/admin finance endpoints returns authorization failure.
- [ ] Vercel Finance Data UI disables crawler controls while local/worker allows them.
- [ ] Backend tests cover normalizer, readiness, valuation DB-only, dividend dedupe/conflict, and log SQL pagination.
- [ ] Frontend build passes.

## Validation Evidence Required

- Unit tests for TCBS and CafeF parser fixtures.
- Integration test: crawl/seed -> normalize -> reconcile -> valuation API returns report.
- Integration test: missing/incomplete DB -> valuation API returns safe unavailable code.
- Integration test: provider function mocked and asserted not called by user valuation route.
- Integration test: duplicate dividend history fetch does not create repeated requests/records.
- Query-level test proving log filter and pagination happen before records are materialized.
- Production Vite build.
- Manual admin/non-admin authorization smoke test.

## Decisions

- `FINANCIAL_STATEMENTS` currently represents the balance sheet document category for UI compatibility; its provider endpoint is `balancesheet` / `BalSheet`.
- The current branch correctly excludes incomplete FY and quarterly dividend placeholders.
- This task intentionally does not merge `dev` into `main`; merge only after validation is green.

## Implementation Notes

Implemented on branch `dev`:

- Valuation now reads canonical Finance DB facts and the portfolio's stored market price only; provider crawling is absent from the user route.
- Canonical facts accept TCBS/CafeF label/value payloads, record parse failures, expose reporting-period metadata, and reject material cross-provider conflicts.
- Dividend canonical tables are initialized on read, ingestion is normalized/reconciled, production fallback crawling is disabled, and worker-only crawling/queue endpoints reject Vercel.
- Finance Data admin API now exposes runtime capability; the UI disables crawl/retry/universe controls in read-only production and explains Local/Worker operation.
- Admin logs use SQL predicates, count, stable ordering, LIMIT/OFFSET, and filter indexes.
- Added provider/network-independent contract tests under `tests/test_finance_db_contract.py`.

Validation still required in the target environment: run the Python test suite and production Vite build, then perform the admin/non-admin smoke tests.

## Result

Status: implementation complete, validation pending.
