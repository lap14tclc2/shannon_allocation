---
id: TASK-20260827-016
title: Incremental finance worker resume and database inspection
status: ready
priority: high
created: 2026-08-27
updated: 2026-08-27
---

## Requirement

When the local finance worker is restarted, it must crawl only symbols with no finance documents or with missing/incomplete documents. Existing successful documents must not be fetched again.

## Context

The queue may already contain many symbols from an earlier full enqueue. The documents table contains successful, pending, and failed rows. New completed reporting periods must also be detected as missing without recrawling older successful periods.

## Acceptance Criteria

- [ ] A symbol with all currently required documents in SUCCESS is not enqueued for a new crawl.
- [ ] A symbol with no documents, a missing required period/provider/type, or a PENDING/FAILED document remains eligible.
- [ ] Existing QUEUED rows for complete symbols are safely marked complete and are not crawled.
- [ ] Restarting a worker resumes incomplete symbols and preserves successful document rows.
- [ ] Existing records can be inspected with database status counts.
- [ ] Any clearing operation is explicit and does not silently delete successful documents.
- [ ] Add contract tests for incremental eligibility and database inspection/clear safeguards.
- [ ] Run available tests and record runtime PostgreSQL validation evidence.

## Constraints and Invariants

- Never refetch a SUCCESS document during an ordinary resume.
- Required periods are derived from the current completed-period policy; future quarters are not fabricated.
- Do not automatically delete successful raw documents, canonical facts, or reconciliation evidence.
- Keep queue locking, stale-job recovery, and active queue uniqueness unchanged.

## Implementation Tasks

- [ ] Add symbol-level missing/incomplete document eligibility.
- [ ] Filter enqueue and claim paths using that eligibility.
- [ ] Add a safe database status/clear command for local operations.
- [ ] Add regression contract tests.

## Result

Pending implementation.
