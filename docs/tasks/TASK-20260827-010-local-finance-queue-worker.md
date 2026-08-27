---
id: TASK-20260827-010
title: Add local finance queue worker
status: implemented
priority: critical
created: 2026-08-27
updated: 2026-08-27
tags: [finance, crawl, worker, queue, local]
related: [TASK-20260826-002, TASK-20260827-008, TASK-20260827-009]
---

## Requirement

Consume the finance crawl queue on the local worker. Queue insertion must lead to actual bounded TCBS/CafeF document crawling outside Vercel.

## Context

The UI showed 1,523 eligible symbols already in QUEUED/RUNNING but no crawl progress. The repository had queue insertion and single-symbol crawl functions, but no process that claimed queue jobs and called crawl_symbol.

## Acceptance Criteria

- [x] Add a runnable local worker entrypoint.
- [x] Atomically claim one QUEUED job at a time.
- [x] Recover stale RUNNING jobs after a bounded timeout.
- [x] Reject legacy invalid symbols before provider calls.
- [x] Mark jobs COMPLETED only when all provider requests succeeded; otherwise mark FAILED.
- [x] Continue after one symbol/provider failure and log queue_id, symbol and result counts.
- [x] Refuse execution in Vercel runtime.
- [x] Document the PowerShell command.

## Constraints and Invariants

- Provider crawling remains local/worker-only.
- Existing SUCCESS documents remain skipped by crawl_symbol incremental logic.
- TCBS/CafeF are still the document providers; TCBS overview is not used for universe metadata.
- No token, database URL or provider payload is logged.

## Validation Evidence

- UI screenshot on 2026-08-27 showed 1,523 QUEUED/RUNNING jobs and no worker progress.
- Run python scripts/finance_worker.py --once locally and inspect [finance-worker] plus [finance-crawl] logs.

## Result

The local worker now consumes queued active equities and writes document results to the local finance catalog.
