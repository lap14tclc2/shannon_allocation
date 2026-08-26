# TASK-20260826-006 — Universe sync progress logging

- Status: implemented; validation pending
- Branch: dev
- Scope: keep Vnstock as the universe/symbol-list provider for local worker sync.

## Problem

The local `POST /api/admin/finance-data/universe` request can appear frozen while
Vnstock is fetching the symbol list. The worker must emit flush-safe progress
messages so operators can distinguish provider wait time from persistence work.

## Acceptance criteria

- [x] Log sync start and local runtime/provider.
- [x] Log before and after each Vnstock listing method call.
- [x] Emit a heartbeat while a provider call is still running.
- [x] Log received row count, persistence checkpoints, completion and elapsed time.
- [x] Log exception type/message without credentials or request secrets.
- [x] Add a regression test for the progress-log contract.
- [x] Update operator documentation with the expected log sequence.

## Implementation notes

Vnstock remains responsible only for obtaining the symbol universe. Finance
document crawling continues to use the configured local providers separately.


## Delivery

- Added flush-safe `[finance-universe]` logs and a 10-second heartbeat around Vnstock listing calls.
- Added a source contract test and operator documentation.
- Commits: `3f2fc60` (code), `b34b667` (test), `78f7ffb` (docs).
- Full test execution remains pending in this connected environment.
