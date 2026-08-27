---
id: TASK-20260827-021
title: Hide retired TCBS worker records from active finance catalog
status: ready
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

- [ ] Active catalog document lists and status counts use CafeF only.
- [ ] Legacy TCBS rows do not appear as newly pending worker work.
- [ ] Existing TCBS records remain preserved for audit/rollback.
- [ ] Add a regression contract test.

## Constraints and Invariants

- Do not issue provider requests or create new TCBS placeholders.
- Do not delete historical TCBS documents or canonical facts in this change.
- Keep provider scope explicit and reversible.

## Result

Pending implementation.
