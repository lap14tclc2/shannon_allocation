# TASK-20260829-061: Backend CPU/RAM Optimization for FastAPI+PostgreSQL Runtime

- **ID**: `TASK-20260829-061`
- **Title**: Backend CPU/RAM Optimization for FastAPI+PostgreSQL Runtime
- **Status**: `in-progress`
- **Priority**: `high`
- **Date**: `2026-08-29`

## Requirement

Reduce CPU/RAM usage of the running app. Audit found:

1. **Critical** — no Postgres connection pooling: `_schema_connection` (postgres.py:254) opens a fresh TCP+TLS connection per query. A dashboard request opens ~1,100 sequential connections (per-symbol loops + per-snapshot queries + ~6 ledger reloads).
2. **High** — `dashboard()` recomputes `effective_events`/`derive_state` ~6 times per request (service.py:376-417).
3. **High** — unbounded global caches: `_services`/`_dividend_services` (app/main.py:51-52) never evicted by age; `external_cache._CACHE` never capped.
4. **High** — N+1 queries: `latest_prices` (storage.py:315) = 1 query+connection per symbol; `list_snapshots` (storage.py:438) = M+1; `_histories` = S queries.
5. **Medium** — `/api/portfolio/market` calls the full `dashboard()` just to slice `market_data`.
6. **Medium** — `_rebuild_snapshot_history` O(days × events) on every sync/edit.

Must remain **safe to deploy on Vercel**: no new runtime dependency, bounded memory, no long-lived background threads, and no behavior change.

## Context

Runtime: FastAPI `app/main.py` + per-portfolio PostgreSQL schemas (`python/portfolio/postgres.py`). Vercel serverless instances can freeze, so pooled connections must be validated on checkout and capped.

## Acceptance Criteria

- [ ] Connection reuse: `_schema_connection` uses a bounded, validated connection pool (no `psycopg_pool` dependency; hand-rolled with lock + idle cap + ping validation).
- [ ] No unbounded growth: `_services`/`_dividend_services` bounded (LRU), `external_cache._CACHE` capped.
- [ ] `latest_prices` is a single `IN (...)` query (no per-symbol connection loop).
- [ ] `_histories` batch-loaded via single query per call.
- [ ] `list_snapshots` loads positions with one batched query (no M+1).
- [ ] `/api/portfolio/market` no longer runs the full `dashboard()` pipeline.
- [ ] `dashboard()` memoizes `current_state`/`effective_events` per-request (ContextVar), cleared on writes.
- [ ] No new dependency; `pip freeze` unchanged; Vercel build unaffected.
- [ ] All unit/contract tests pass; frontend build unaffected.

## Constraints and Invariants

- `BUY_AND_HOLD_INFORMATION_SYSTEM`.
- Ledger invariant: cached state must never leak across requests or survive writes.
- Vercel-safe: no unbounded memory, no threads holding connections forever.

## Implementation Tasks

- [ ] 1. Add bounded connection pool in `postgres.py`.
- [ ] 2. Bound `_services` / `_dividend_services` + `external_cache`.
- [ ] 3. Batch `latest_prices` + `_histories` + `list_snapshots` positions.
- [ ] 4. Light `/api/portfolio/market` endpoint.
- [ ] 5. Request-scoped memo for `current_state`/`effective_events` with write invalidation.
- [ ] 6. Regression tests + full pytest + build.

## Related Notes

- `python/portfolio/postgres.py`
- `python/portfolio/service.py`
- `app/main.py`

## Validation Evidence

_To be filled after running tests._

## Decisions

_To be recorded during implementation._

## Result

_To be filled on completion._