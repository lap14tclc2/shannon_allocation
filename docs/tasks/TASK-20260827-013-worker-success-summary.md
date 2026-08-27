---
id: TASK-20260827-013
title: Report finance worker success symbols
status: implemented
priority: high
created: 2026-08-27
updated: 2026-08-27
tags: [finance, crawl, worker, queue, logging]
related: [TASK-20260827-010, TASK-20260827-009]
---

## Requirement

Run the local finance worker until the queue is empty and make the terminal output identify which symbols completed successfully.

## Context

The UI can enqueue a large batch, but the current worker output only reports each job as `COMPLETED` or `FAILED`. Operators need an explicit success/failure signal and a final summary to verify the batch without inspecting the database.

## Acceptance Criteria

- [x] Print `SUCCESS` with the symbol when a job has zero provider failures.
- [x] Print `FAILED` with the symbol when a job has provider failures or an exception.
- [x] Continue processing later queue jobs after one job fails.
- [x] Print final processed/success/failed counts when the worker stops.
- [x] Print successful and failed symbol lists in the final summary.
- [x] Keep `--once`, `--limit`, stale-job recovery, and Vercel refusal behavior unchanged.
- [x] Do not log tokens, database URLs, or provider payloads.
- [x] Add contract tests for success/failure summary behavior.

## Constraints and Invariants

- The worker remains local/worker-only.
- Database job status remains `COMPLETED` only when all provider requests succeed; terminal label `SUCCESS` is an operator-facing label.
- One symbol failure must not stop the queue consumer.
- Output must be flushed so PowerShell shows progress immediately.

## Implementation Tasks

- [x] Track successful and failed symbols during one worker invocation.
- [x] Add explicit per-symbol terminal result lines.
- [x] Add a deterministic final summary.
- [x] Add source-level contract tests for the new output paths.
- [ ] Run available tests and record validation evidence.

## Validation Evidence

Static review completed. Runtime tests require the user's local repository environment and PostgreSQL/provider configuration.

## Decisions

Use a per-run in-memory summary. Do not add a new database table or change the finance schema.

## Result

The worker now reports each symbol as `SUCCESS` or `FAILED`, prints both symbol lists, and continues until the queue is empty unless `--once` or `--limit` is supplied.
