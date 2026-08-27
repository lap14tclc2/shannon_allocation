---
id: TASK-20260827-028
title: Batch prepared finance import for faster throughput
status: verified
priority: high
created: 2026-08-27
updated: 2026-08-27
tags: [finance-data, import, performance, postgres]
related: [TASK-20260827-027]
---

## Requirement

Importing prepared TCBS JSON files from docs/crawled is functionally correct but
too slow because each logical document period opens separate database work.

## Acceptance Criteria

- [x] Prepared import reduces database round trips by batching writes per symbol.
- [x] Existing SUCCESS and NOT_AVAILABLE rows are preserved.
- [x] Missing periods remain NOT_AVAILABLE and do not become failures.
- [x] Canonical facts remain synchronized with imported SUCCESS documents.
- [x] Import remains idempotent and file-only.
- [x] Terminal progress still reports per-symbol imported/failed/unavailable counts.
- [x] Regression coverage verifies batch import behavior and result counters.

## Constraints

- Do not change TCBS payload semantics or fabricate data.
- Do not affect the running worker process.
- Keep transaction boundaries safe and rollback-capable.
- Keep provider credentials out of logs and source control.

## Validation Evidence

- Prepared import reuses a database connection/transaction per symbol for document and canonical writes.
- Existing SUCCESS and NOT_AVAILABLE rows continue to be skipped by incremental selection.
- Import result and terminal progress expose imported, failed, unavailable, and skipped counts.
- `tests/test_finance_import_batch.py` covers the batch connection contract and AAH history shape.
- Source-level validation passed; local PostgreSQL throughput measurement remains environment-dependent.

## Result

Prepared TCBS JSON imports now batch writes per symbol, reducing database round trips while preserving idempotency, canonicalization, and unavailable-period semantics.
