---
id: TASK-20260826-005
title: Sync complete Finance DB catalog from local crawler to Vercel
status: in-progress
priority: P0
created: 2026-08-26
updated: 2026-08-26
tags: [finance-data, sync, postgres, vercel, crawler]
related:
  - docs/finance-data-sync.md
  - docs/tasks/TASK-20260826-004-finance-db-first-valuation-and-log-scalability.md
---

## Requirement

Allow the local finance worker to crawl TCBS/CafeF, normalize and reconcile data locally, then safely synchronize the complete qport_finance catalog to the Vercel/Neon PostgreSQL database.

## Acceptance Criteria

- [x] Sync securities and documents.
- [x] Sync canonical_facts and parse_errors.
- [x] Sync dividend_observations, dividend_canonical and dividend_conflicts.
- [x] Validate symbols, providers, statuses, payload checksums, cross-table references and row limits before target mutation.
- [x] Preserve repeated sync safety through idempotent upserts and stable source IDs.
- [x] Run the target catalog update in one transaction.
- [ ] Never expose or commit database URLs.
- [ ] Provide Windows PowerShell and shell usage instructions.
- [x] Add tests for table coverage and validation behavior.

## Constraints and Invariants

- Local crawler is the only component allowed to call providers.
- Vercel remains database-read-only for finance ingestion.
- Conflict dividend rows must remain excluded from user canonical reads.
- Source and target database URLs must be different.
- A failed validation must not mutate the target database.

## Implementation Tasks

1. Extend scripts/finance_sync.py to copy all Finance catalog tables required by valuation and dividend reads.
2. Preserve stable natural keys and canonical IDs; avoid destructive replacement.
3. Update documentation with the complete local-crawl → normalize → reconcile → sync workflow.
4. Add validation/test coverage and record evidence.

## Validation Evidence

Implementation complete; local PostgreSQL execution and integration evidence pending.

## Result

Implementation complete; verification pending.
