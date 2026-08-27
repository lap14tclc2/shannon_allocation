---
id: TASK-20260827-023
title: Retry one finance document without full catalog reload
status: ready
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

- [ ] Retry sends the selected provider/document/period identity.
- [ ] Backend fetches only that document and returns its updated status.
- [ ] Existing documents and other symbols are not refetched.
- [ ] Frontend updates the affected row/document in local state without full catalog refresh.
- [ ] Add regression/contract tests.

## Constraints and Invariants

- Preserve incremental success-skip behavior and provider scope (CafeF only).
- Do not retry all failed documents when one Retry button is clicked.
- Do not reload or reset pagination/search/filter state.
- Keep raw document provenance and crawl logs.

## Result

Pending implementation.
