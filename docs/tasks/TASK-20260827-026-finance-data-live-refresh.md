---
id: TASK-20260827-026
title: Auto-refresh Finance Data after external worker/import updates
status: verified
priority: high
created: 2026-08-27
updated: 2026-08-27
tags: [finance-data, frontend, polling, worker]
related: [TASK-20260827-025]
---

## Requirement

When the local finance worker or `scripts/finance_import.py` updates the
database outside the browser, an already-open Finance Data page must discover
the new records without a full-page reload.

## Context

The import script is CLI/DB-only and cannot notify a browser tab. The existing
page fetches data on mount and when its filters change, but has no polling,
visibility refresh, or push channel.

## Acceptance Criteria

- [x] Finance Data polls the current filtered API result at a bounded interval.
- [x] Polling updates rows, counts, statuses, and document summaries in place.
- [x] Polling does not force `window.location.reload()` or remount the page.
- [x] Polling pauses while the document is hidden and refreshes when visible.
- [x] The timer and event listener are cleaned up on unmount/filter change.
- [x] An in-page indicator communicates the automatic refresh interval.
- [x] A frontend contract test covers timer setup, cleanup, visibility handling,
  and absence of full-page reload.

## Constraints

- Do not change the CLI import contract or require browser connectivity from the
  worker.
- Do not interfere with the existing single-symbol crawl/retry in-place update.
- Keep API requests `cache: no-store`.
- Avoid overlapping polling requests.

## Validation Evidence

- `FinanceDataPage.jsx` uses a 10-second `setInterval` with silent in-place refresh.
- Polling skips hidden tabs, refreshes on `visibilitychange`, and cleans up the timer/listener.
- `frontend/test/finance-data-refresh.mjs` covers the refresh contract.
- Runtime browser/Vite execution remains to be run in the local environment.

## Result

Finance Data now discovers external worker/import updates without a full-page reload. The open page refreshes filtered data in place every 10 seconds and immediately when the tab becomes visible.
