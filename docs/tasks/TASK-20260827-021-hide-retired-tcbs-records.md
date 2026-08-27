---
id: TASK-20260827-021
title: Hide retired TCBS worker records from active finance catalog
status: in_progress
priority: high
created: 2026-08-27
updated: 2026-08-27
tags: [finance-data, crawler, tcbs, cleanup]
related: [TASK-20260827-020]
---

## Requirement

After TCBS is removed from the worker scope, the active Finance Data catalog must
not show legacy TCBS PENDING placeholders or count them in crawl status.

## Acceptance Criteria

- [x] Active catalog document lists and status counts use CafeF only.
- [x] Legacy TCBS rows do not appear as newly pending worker work.
- [x] Existing TCBS records remain preserved for audit/rollback.
- [x] Add a regression contract test.

## Constraints and Invariants

- Do not issue provider requests or create new TCBS placeholders.
- Do not delete historical TCBS documents or canonical facts in this change.
- Keep provider scope explicit and reversible.

## Implementation

- Active Finance Data document summaries and document lists now filter by
  WORKER_PROVIDERS, currently CafeF only.
- Legacy TCBS database rows are preserved but are not counted as pending active
  worker work or shown in the active catalog.
- Added regression coverage for the provider-scope filter.

## Remaining Validation

- [ ] Run the local API/UI and confirm old TCBS PENDING rows are no longer shown.
- [ ] Run the full Python test suite and Vite build.

## Result

Implementation complete; runtime validation pending.
