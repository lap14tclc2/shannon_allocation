---
id: TASK-20260827-024
title: Clean finance catalog and validate CafeF payloads
status: in_progress
priority: high
created: 2026-08-27
updated: 2026-08-27
tags: [finance-data, cafef, cleanup, data-quality]
related: [TASK-20260827-022, TASK-20260827-023]
---

## Requirement

Provide a safe explicit command to clear the finance catalog before a clean
re-crawl, and prevent CafeF responses with the wrong page/payload shape from
being accepted as valid finance data.

## Acceptance Criteria

- [x] A destructive `clear-all` command clears finance rows while preserving
  the database schema and refuses to run while a worker is RUNNING.
- [ ] Clearing removes raw documents, canonical facts, parse errors, dividend
  reconciliation rows, queue history, run history, and securities.
- [x] CafeF document fetches validate that the response belongs to the requested
  symbol/document before marking the document SUCCESS.
- [x] Invalid or unexpected CafeF payloads are stored as FAILED with a
  deterministic provider/data-quality error.
- [x] Add regression tests for cleanup scope and CafeF payload validation.
- [x] Update the local runbook with stop, clear, and re-crawl commands.

## Constraints

- Do not execute destructive database operations from the application deploy.
- Keep the operation explicit and protected by `--confirm`.
- Preserve source URLs and raw payloads for successful documents.
- TCBS remains disabled in the worker.

## Result

Implementation complete; local PostgreSQL re-crawl validation is pending.
