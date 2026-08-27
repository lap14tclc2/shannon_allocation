---
id: TASK-20260827-023
title: Retry one finance document without full catalog reload
status: in_progress
priority: high
created: 2026-08-27
updated: 2026-08-27
tags: [finance-data, dividends, retry, frontend]
related: [TASK-20260827-022]
---

## Requirement

Retry must target one selected finance document, especially the CafeF dividend
history document, and crawling one symbol/document must not reload the full
Finance Data catalog page.

## Acceptance Criteria

- [x] Retry sends the selected provider/document/period identity.
- [x] Backend fetches only that document and returns its updated status.
- [x] Existing documents and other symbols are not refetched.
- [x] Frontend updates the affected row/document in local state without full catalog refresh.
- [x] Add regression/contract tests.

## Constraints and Invariants

- Preserve incremental success-skip behavior and provider scope (CafeF only).
- Do not retry all failed documents when one Retry button is clicked.
- Do not reload or reset pagination/search/filter state.
- Keep raw document provenance and crawl logs.

## Implementation

- Retry API now requires a document identity and targets one active CafeF
  document instead of retrying every failed document for the symbol.
- Crawl/retry returns the updated catalog row.
- Finance Data updates only the affected row in React state; search, filters,
  pagination, and expanded state are preserved.
- Added contract coverage and runbook guidance.

## Remaining Validation

- [ ] Restart local API/worker and verify one failed CafeF dividend document can
  be retried without a full catalog request.
- [ ] Run the full Python suite and Vite build.

## Result

Implementation complete; runtime validation pending.
