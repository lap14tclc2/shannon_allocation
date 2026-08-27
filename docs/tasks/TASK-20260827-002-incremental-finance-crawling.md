---
id: TASK-20260827-002
title: Incremental finance document crawling
status: implemented
priority: high
created: 2026-08-27
updated: 2026-08-27
tags: [finance, bctc, incremental, tcbs, cafef]
related: [TASK-20260826-004]
---

## Requirement

Fetch new completed quarters and fiscal years without reloading documents already marked SUCCESS.

## Acceptance Criteria

- [x] Existing SUCCESS documents are skipped during normal crawls.
- [x] New periods created by _periods() are fetched when PENDING.
- [x] FAILED documents are retried during normal crawls.
- [x] retry_failed_only fetches only FAILED documents.
- [x] A no-op crawl returns success with skipped_count.
- [x] Add unit tests for fetch decisions.

## Implementation Tasks

- [x] Add a single fetch-decision function.
- [x] Apply it to every provider/period crawl.
- [x] Track skipped documents.
- [x] Keep crawl run status COMPLETED for successful no-op runs.
- [x] Add regression tests.

## Validation Evidence

Unit tests added. Full PostgreSQL/provider execution remains environment-dependent.

## Result

Incremental crawling implemented on dev. Future completed periods are discovered by _periods(), inserted as PENDING, and fetched without reloading prior SUCCESS documents.
