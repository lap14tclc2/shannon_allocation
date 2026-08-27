---
id: TASK-20260827-028
title: Batch prepared finance import for faster throughput
status: in_progress
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

- [ ] Prepared import reduces database round trips by batching writes per symbol.
- [ ] Existing SUCCESS and NOT_AVAILABLE rows are preserved.
- [ ] Missing periods remain NOT_AVAILABLE and do not become failures.
- [ ] Canonical facts remain synchronized with imported SUCCESS documents.
- [ ] Import remains idempotent and file-only.
- [ ] Terminal progress still reports per-symbol imported/failed/unavailable counts.
- [ ] Regression coverage verifies batch import behavior and result counters.

## Constraints

- Do not change TCBS payload semantics or fabricate data.
- Do not affect the running worker process.
- Keep transaction boundaries safe and rollback-capable.
- Keep provider credentials out of logs and source control.

## Validation Evidence

Pending implementation and tests.

## Result

Pending.
