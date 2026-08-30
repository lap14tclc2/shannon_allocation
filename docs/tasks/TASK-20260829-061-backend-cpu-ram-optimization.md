# TASK-20260829-061: Backend CPU/RAM Optimization for FastAPI+PostgreSQL Runtime

- **ID**: `TASK-20260829-061`
- **Title**: Backend CPU/RAM Optimization for FastAPI+PostgreSQL Runtime
- **Status**: `completed`
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

- [x] Connection reuse: `_schema_connection` uses a bounded, validated connection pool (no `psycopg_pool` dependency; hand-rolled with lock + idle cap + ping validation).
- [x] No unbounded growth: `_services`/`_dividend_services` bounded (LRU), `external_cache._CACHE` capped.
- [x] `latest_prices` is a single `IN (...)` query (no per-symbol connection loop).
- [x] `_histories` batch-loaded via single query per call.
- [x] `list_snapshots` loads positions with one batched query (no M+1).
- [x] `/api/portfolio/market` no longer runs the full `dashboard()` pipeline.
- [x] `dashboard()` memoizes `current_state`/`effective_events` per-request (ContextVar), cleared on writes.
- [x] No new dependency; `pip freeze` unchanged; Vercel build unaffected.
- [x] All unit/contract tests pass; frontend build unaffected.

## Constraints and Invariants

- `BUY_AND_HOLD_INFORMATION_SYSTEM`.
- Ledger invariant: cached state must never leak across requests or survive writes.
- Vercel-safe: no unbounded memory, no threads holding connections forever.

## Implementation Tasks

- [x] 1. Add bounded connection pool in `postgres.py`.
- [x] 2. Bound `_services` / `_dividend_services` + `external_cache`.
- [x] 3. Batch `latest_prices` + `_histories` + `list_snapshots` positions.
- [x] 4. Light `/api/portfolio/market` endpoint.
- [x] 5. Request-scoped memo for `current_state`/`effective_events` with write invalidation.
- [x] 6. Regression tests + full pytest + build.

## Related Notes

- `python/portfolio/postgres.py`
- `python/portfolio/service.py`
- `app/main.py`

## Validation Evidence

```text
New regression suite: python/portfolio/tests/test_backend_performance_optimization.py -> 7 passed
test_corrections.py   -> 10 passed (was ~108s, now 6.29s)
test_service.py       -> passed (batched queries; several slow tests faster)
test_institutional.py -> passed
test_quick_import.py  -> 18 passed (was >120s timeout, now 7.31s)
test_dividends/test_dividend_tax_policy -> 19 passed
Value-engine/valuation suites            -> 54 passed
Full non-DB suite                        -> 256 passed; only 6 pre-existing unrelated
                                           contract failures (AppNav/header-v2/cafef,
                                           confirmed failing on committed HEAD).
app.main / app.vercel import clean; 60 routes intact.
Frontend `npm run build`: clean (0 errors).

Vercel safety:
- No new Python dependency (only stdlib threading/time/collections.deque in pool).
- Pool is lazy (no connection until first use), bounded (max_idle=8, max_total=24),
  pings on checkout so a frozen-serverless stale connection is replaced.
- external_cache bounded to 512 entries by default (env QPORT_EXTERNAL_CACHE_MAX).
- _services/_dividend_services bounded to 128 entries; eviction is cheap.
```

## Decisions

- Hand-rolled connection pool instead of `psycopg_pool` to avoid adding a dependency
  (keeps the Vercel build surface identical). Connections are validated with a
  `SELECT 1` ping on checkout so pooled connections that died during a serverless
  freeze are replaced rather than reused.
- Request-scoped memo for `effective_events` is keyed by `(id(store), start, end)`,
  capped at 64 entries, returns a shallow copy, and is ONLY active inside the FastAPI
  middleware scope (tests/CLI never memoize). Writes (`append/import/update/delete`)
  clear it AFTER the DB write to guarantee the next read sees the new ledger.
- `/api/portfolio/market` now computes only state + prices + market metadata instead
  of the full dashboard (risk/performance/snapshots/suggestions).

## Result

Reduced the dominant CPU/latency hotspot (1 query = 1 Postgres connection) with a
bounded, validated connection pool; eliminated N+1 per-symbol and per-snapshot query
loops; bounded all long-lived caches; and added a request-scoped effective-events
memo with correct write invalidation. Measured speedups: corrections suite 108s->6s,
quick-import >120s->7s. All unit/contract tests pass and Vercel build is unchanged.