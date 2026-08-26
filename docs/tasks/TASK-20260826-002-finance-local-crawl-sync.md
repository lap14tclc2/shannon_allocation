---
id: TASK-20260826-002
title: Local-only finance crawling with validated Vercel database sync
status: in-progress
priority: high
created: 2026-08-26
updated: 2026-08-26
tags: [finance-data, crawl, sync, local, vercel, validation]
related: [TASK-20260826-001]
---

## Requirement

Investigate and optimize the finance-data crawl flow. Crawling must run only on a local/external worker. Vercel must never call providers. Validated crawled data must be synced from the local PostgreSQL database to the Vercel PostgreSQL database.

## Acceptance Criteria

- [ ] Provider crawling is rejected when runtime is Vercel or not explicitly local-worker mode.
- [ ] Crawl requests have bounded timeouts, retries, and symbol/provider isolation.
- [ ] A sync command validates source/target URLs, schema, row counts, and checksums.
- [ ] Sync is transactional and idempotent; failed validation rolls back.
- [ ] Vercel remains database-read-only for user finance data.
- [ ] Admin can continue to queue work without executing provider calls in Vercel.

## Constraints and Invariants

- Never use hard-coded financial values or shared symbol payloads.
- Preserve source provider, period, document type, status, hash, and fetched timestamp.
- Do not overwrite successful target documents with older source data.
- No filesystem writes are required by Vercel runtime.
- Sync must not modify portfolio ledger data.

## Implementation Tasks

- [ ] Add explicit local-worker crawl runtime validation.
- [ ] Add retry/backoff and response validation for provider requests.
- [ ] Add `finance_sync.py` for local-to-Vercel database sync.
- [ ] Add dry-run and post-sync verification.
- [ ] Document the operational flow and required environment variables.

## Validation Evidence

Pending.

## Result

Pending.
