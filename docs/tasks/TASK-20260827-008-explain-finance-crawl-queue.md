---
id: TASK-20260827-008
title: Explain finance crawl queue state
status: implemented
priority: medium
created: 2026-08-27
updated: 2026-08-27
tags: [finance, crawl, queue, observability]
related: [TASK-20260827-007]
---

## Requirement

Make the crawl-all response distinguish eligible securities from jobs already present in the queue and jobs newly inserted.

## Context

The UI reported "Đã xếp hàng 0 mã" while the active-equity filter and the external-worker architecture made it ambiguous whether there were no eligible symbols or all symbols were already queued.

## Acceptance Criteria

- [x] Return eligible count, already queued/running count and newly queued count.
- [x] Log the same counts without secrets or provider payloads.
- [x] Apply the same active-equity predicate used by Finance Data listing.
- [x] Keep duplicate queue insertion idempotent.
- [x] Explain that queue insertion does not execute the external worker.

## Constraints and Invariants

- QUEUED/RUNNING jobs are not inserted again.
- FAILED/COMPLETED jobs can be queued again for a new run.
- Filtering does not delete historical documents.

## Validation Evidence

- Local UI response on 2026-08-27 reported queued=0 and needed queue-state diagnostics.
- Run the targeted universe tests and inspect the new response fields after pulling.

## Result

The UI/API can now distinguish zero eligible symbols from a queue that already contains all eligible symbols.
