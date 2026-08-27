---
id: TASK-20260827-027
title: Treat unavailable financial periods as non-errors
status: in_progress
priority: high
created: 2026-08-27
updated: 2026-08-27
tags: [finance-data, tcbs, periods, data-quality]
related: [TASK-20260827-025, TASK-20260827-026]
---

## Requirement

Not every listed company has 10–15 years of financial history. A missing
historical period returned by TCBS must not be recorded as a crawler/provider
failure.

## Acceptance Criteria

- [ ] Missing periods are represented as NOT_AVAILABLE, not FAILED.
- [ ] This behavior applies to live TCBS crawling and prepared JSON importing.
- [ ] Genuine HTTP, malformed JSON, schema, and parser errors remain FAILED.
- [ ] Existing successful documents are preserved.
- [ ] Finance Data distinguishes unavailable history from failed crawling.
- [ ] Value Engine still treats missing required facts as unavailable/blocking,
  without fabricating values.
- [ ] Regression tests cover a symbol with only a shorter history window.

## Constraints

- Do not fabricate or backfill historical financial values.
- Do not delete valid data.
- Keep TCBS-only worker behavior and current incremental crawl semantics.
- Keep provider credentials out of logs and source control.

## Validation Evidence

Pending implementation and tests.

## Result

Pending.
