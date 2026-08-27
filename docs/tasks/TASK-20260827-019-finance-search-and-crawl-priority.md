---
id: TASK-20260827-019
title: Search finance catalog and prioritize listed exchange crawl jobs
status: in_progress
priority: high
created: 2026-08-27
updated: 2026-08-27
tags: [finance-data, crawler, admin-ui]
related: [TASK-20260827-018]
---

## Requirement

Allow an admin to search symbols and company names in Finance Data. Let the external worker claim only HOSE and HNX jobs, with HOSE before HNX. UPCOM jobs remain untouched for a later explicit scope.

## Acceptance Criteria

- [ ] Finance Data has a search field for symbol or company name.
- [ ] Search is server-side, combines with exchange and crawl-status filters, resets pagination, and is safely parameterized.
- [ ] Worker claim order is HOSE → HNX and does not claim UPCOM/unknown jobs.
- [ ] Existing RUNNING jobs are not reordered or modified.
- [ ] Add regression/contract tests.

## Constraints and Invariants

- Preserve active-equity filtering and existing queue deduplication.
- Do not change historical documents, active worker leases, or queued UPCOM rows.
- Search must not expose data beyond the admin finance catalog.
- Queue ordering is deterministic within the same exchange.

## Implementation

- Added parameterized symbol/company search to the catalog query, API client, and Finance Data filter bar.
- Default bulk queue scope is HOSE/HNX. The external worker claims only those exchanges and orders HOSE before HNX.
- Existing RUNNING and queued UPCOM rows are left unchanged; UPCOM bulk requests receive an explicit unsupported-scope response.
- Added contract tests and Python syntax validation.

## Remaining Validation

- [ ] Run PostgreSQL integration tests to verify actual search pagination and concurrent worker claim ordering.
- [ ] Run the full Python suite and Vite production build.

