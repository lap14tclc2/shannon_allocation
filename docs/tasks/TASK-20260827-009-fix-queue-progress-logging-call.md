---
id: TASK-20260827-009
title: Fix queue progress logging call
status: implemented
priority: high
created: 2026-08-27
updated: 2026-08-27
tags: [finance, crawl, queue, bugfix]
related: [TASK-20260827-008]
---

## Requirement

Fix the crawl-all endpoint runtime error introduced by queue observability logging.

## Context

The queue response enhancement called _crawl_progress with only the message argument, while the helper contract requires a symbol/category and a message.

## Acceptance Criteria

- [x] Call _crawl_progress with both required arguments.
- [x] Keep eligible, already_queued and queued diagnostics.
- [x] Add a regression test for the call shape.
- [x] Do not change queue idempotency or security filtering.

## Validation Evidence

- Local FastAPI traceback on 2026-08-27:
  TypeError: _crawl_progress() missing 1 required positional argument: message

## Result

The crawl-all endpoint no longer fails while emitting queue diagnostics.
