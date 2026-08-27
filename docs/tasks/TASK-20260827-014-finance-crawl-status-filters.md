---
id: TASK-20260827-014
title: Add finance crawl status filters
status: ready
priority: high
created: 2026-08-27
updated: 2026-08-27
tags: [finance, crawl, admin, frontend, status]
related: [TASK-20260827-006, TASK-20260827-010, TASK-20260827-013]
---

## Requirement

Add a status filter to the admin Finance Data catalog and show crawl status for each financial document type.

## Context

The catalog currently shows a generic row status and individual document results only after expanding a symbol. Operators need to find symbols that fully succeeded, partially succeeded, failed, are pending, or have not been crawled. Each document group must also summarize its own success/failure state.

## Acceptance Criteria

- [ ] The Finance Data API accepts a status filter and applies it before SQL pagination.
- [ ] The API returns aggregate document counts and a normalized symbol `crawl_status`.
- [ ] Supported symbol statuses are `SUCCESS`, `PARTIAL`, `FAILED`, `PENDING`, and `NOT_CRAWLED`.
- [ ] The Finance Data UI provides an all/status selector and reloads from page zero when it changes.
- [ ] Each table row shows the normalized symbol status and document counts.
- [ ] Each expanded document group shows its own success/partial/failed/pending status.
- [ ] Existing exchange filtering, pagination, crawl controls, and runtime guards remain functional.
- [ ] Add contract tests for backend status filtering and frontend rendering.

## Constraints and Invariants

- Status filtering must happen in the database query before LIMIT/OFFSET.
- `SUCCESS` means the symbol has document rows and no failed or pending document rows.
- `PARTIAL` means at least one document succeeded and at least one document failed or remains pending.
- `FAILED` means at least one document failed and none succeeded.
- `NOT_CRAWLED` means no document row exists; `PENDING` means rows exist but none succeeded or failed.
- Existing database statuses `SUCCESS`, `FAILED`, and `PENDING` are unchanged.
- No provider token, database URL, or payload is exposed in the UI.

## Implementation Tasks

- [ ] Add document aggregate SQL and status predicate to `list_securities`.
- [ ] Thread status query parameter through the FastAPI route and frontend API client.
- [ ] Add status selector and row/group summaries to `FinanceDataPage`.
- [ ] Add source-level contract tests.
- [ ] Run available tests/build and record evidence.

## Validation Evidence

Pending implementation and runtime validation.

## Decisions

Use derived status from existing `documents.status` rows; do not add a new status column or migration.

## Result

Pending.
