---
id: TASK-20260826-004
title: Database-first dividend cache with normalize reconcile conflict
status: in-progress
priority: high
created: 2026-08-26
updated: 2026-08-26
tags: [dividend, cache, normalize, reconcile, conflict, finance-data]
related: [TASK-20260826-001, TASK-20260826-002]
---

## Requirement

Fix dividend caching so user routes do not crawl providers. Extend the finance-data architecture with normalize, reconcile, and conflict stages for TCBS/CafeF dividend observations.

## Acceptance Criteria

- [ ] User dividend reads are database-only and never invoke provider calls.
- [ ] Cache misses return a clear pending/contact-admin state.
- [ ] External worker can still fetch provider data explicitly.
- [ ] Raw provider observations remain source-scoped and immutable.
- [ ] Normalization creates a stable economic event representation.
- [ ] Reconciliation produces canonical events with evidence from multiple sources.
- [ ] Conflicting dates/amounts/ratios are stored for admin review, not silently merged.
- [ ] Newer data does not get replaced by older cache data.

## Constraints and Invariants

- Portfolio ledger remains the only source of holdings/cash changes.
- Corporate-action data must never be double-counted.
- Preserve provider, source document, observed time, payload hash and parser version.
- User requests cannot call TCBS/CafeF or write provider payloads.

## Implementation Tasks

- [ ] Add explicit allow_provider_fetch switch to dividend service.
- [ ] Add normalized observation/canonical/conflict PostgreSQL tables.
- [ ] Add deterministic normalization and reconciliation functions.
- [ ] Add stale/cache metadata and operational documentation.
- [ ] Validate syntax and merge.

## Validation Evidence

Pending.

## Result

Pending.
