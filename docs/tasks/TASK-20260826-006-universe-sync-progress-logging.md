# TASK-20260826-006 — Universe sync progress logging

- Status: in_progress
- Branch: dev
- Scope: keep Vnstock as the universe/symbol-list provider for local worker sync.

## Problem

The local `POST /api/admin/finance-data/universe` request can appear frozen while
Vnstock is fetching the symbol list. The worker must emit flush-safe progress
messages so operators can distinguish provider wait time from persistence work.

## Acceptance criteria

- [ ] Log sync start and local runtime/provider.
- [ ] Log before and after each Vnstock listing method call.
- [ ] Emit a heartbeat while a provider call is still running.
- [ ] Log received row count, persistence checkpoints, completion and elapsed time.
- [ ] Log exception type/message without credentials or request secrets.
- [ ] Add a regression test for the progress-log contract.
- [ ] Update operator documentation with the expected log sequence.

## Implementation notes

Vnstock remains responsible only for obtaining the symbol universe. Finance
document crawling continues to use the configured local providers separately.
