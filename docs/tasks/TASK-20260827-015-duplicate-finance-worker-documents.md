---
id: TASK-20260827-015
title: Prevent duplicate finance workers and document rows
status: implemented
priority: high
created: 2026-08-27
updated: 2026-08-27
---

## Context

Multiple local finance workers can race while claiming queued symbols, and PostgreSQL treats NULL fiscal quarters as distinct values in a normal UNIQUE constraint. This produces repeated FY document rows for the same symbol/provider/type/year and makes the Finance Data detail view appear to crawl the same report repeatedly.

## Acceptance Criteria

- [x] A queued crawl job is claimed with row locking so concurrent workers cannot claim the same queue row.
- [x] The logical document key treats an FY row with NULL fiscal_quarter as one period.
- [x] Existing duplicate document rows are repaired once, preserving the best row (SUCCESS before FAILED before PENDING).
- [x] canonical_facts.source_document_id is remapped before duplicate documents are removed.
- [x] Future placeholder creation and document upserts remain idempotent for FY and QUARTER rows.
- [x] Add contract tests for locking, the logical unique index, and the repair migration.
- [ ] Run available tests and record runtime validation evidence.

## Implementation Tasks

- [x] Add a one-time documents deduplication migration and expression unique index.
- [x] Use the expression conflict target for document inserts/upserts.
- [x] Add FOR UPDATE SKIP LOCKED to worker claim selection.
- [x] Add regression contract tests.

## Invariants

- Never delete the selected/best document row.
- Preserve canonical traceability when remapping source document IDs.
- Keep active queue uniqueness and stale-job recovery behavior unchanged.

## Result

Implemented in `8de7f43`; runtime PostgreSQL validation remains pending.
