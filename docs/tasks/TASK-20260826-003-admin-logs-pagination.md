---
id: TASK-20260826-003
title: Admin logs server-side filtering and pagination
status: in-progress
priority: high
created: 2026-08-26
updated: 2026-08-26
tags: [admin, logs, observability, pagination, azure-style]
related: []
---

## Requirement

Fix admin logs where changing filters does not load the latest matching rows. Add server-side pagination and redesign the log table for fast scanning, inspired by Azure log viewers.

## Context

The current API returns a capped aggregate list and the browser filters the initial response. This causes stale or incomplete results and makes large log sets difficult to navigate.

## Acceptance Criteria

- [ ] API accepts page, page_size, filters, and search query.
- [ ] Filtering is applied before pagination and total counts are returned.
- [ ] Refresh/filter changes fetch the newest server result.
- [ ] Log table exposes timestamp, level/status, request/entity context, message and expandable details.
- [ ] Admin authorization remains mandatory.
- [ ] Empty/loading/error states are clear.

## Constraints and Invariants

- Preserve append-only activity records and integrity verification.
- Do not expose logs to normal users.
- Do not silently drop records before filtering.
- Keep API responses no-store.

## Implementation Tasks

- [ ] Add server-side log query and pagination.
- [ ] Update API client query parameters.
- [ ] Update LogsPage fetch lifecycle and pagination controls.
- [ ] Apply Azure-like dense visual hierarchy and readable details.
- [ ] Validate syntax/build contract.

## Validation Evidence

Pending.

## Result

Pending.
