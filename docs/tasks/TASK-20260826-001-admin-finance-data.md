---
id: TASK-20260826-001
title: Admin finance data catalog and database-first financial statements
status: in-progress
priority: high
created: 2026-08-26
updated: 2026-08-26
tags: [admin, finance-data, tcbs, cafef, postgres, qport]
related: []
---

## Requirement

Build an admin-only finance-data page for crawling and monitoring Vietnamese listed-company financial documents. Persist normalized crawl metadata and payloads in PostgreSQL. User pages must read database snapshots only and show `contact admin` when data is missing. Temporarily disable automatic Vercel deployments.

## Context

Vercel live crawling is disabled because serverless filesystem/provider failures caused crashes. Crawling must be initiated by an admin and stored centrally. The universe covers up to 1,500 Vietnamese tickers with HOSE, HNX, and UPCOM filters.

## Acceptance Criteria

- [ ] `git.deploymentEnabled` is false.
- [ ] Only ADMIN can access finance-data APIs and page.
- [ ] Finance-data page has crawl button, pagination, exchange filters, and expand/collapse rows.
- [ ] Expanded rows list required documents per source (TCBS/CafeF), with success/failure and retry.
- [ ] Required document types include annual/quarterly financial statements, cash flow, income statement, and annual dividends.
- [ ] Current year includes all completed quarters through the latest available quarter.
- [ ] Financial data is persisted in a normalized, source-aware PostgreSQL schema.
- [ ] User-facing data reads DB only and returns `contact admin` when unavailable.
- [ ] No live crawl is triggered by normal user routes.

## Constraints and Invariants

- Preserve immutable portfolio ledger and buy-and-hold boundaries.
- Never mix symbols or provider documents.
- Keep raw payload, source, period, status, error, checksum, and timestamps for audit.
- Crawling is best-effort and idempotent; retry must not duplicate documents.
- Vercel runtime must not write to the filesystem.
- Admin authorization is mandatory on every crawl/status/retry endpoint.

## Implementation Tasks

- [ ] Add database tables and repository service for security universe, crawl jobs, and financial documents.
- [ ] Add TCBS/CafeF provider adapters with symbol-scoped requests and failure capture.
- [ ] Add admin list/crawl/retry APIs with pagination and exchange filter.
- [ ] Add database-only user read path with missing-data message.
- [ ] Add finance-data admin page and navigation.
- [ ] Add tests for authorization, idempotency, quarter selection, and source isolation.
- [ ] Validate frontend build and backend tests.

## Related Notes

- `python/portfolio/financial_data/models.py`
- `python/portfolio/financial_data/connectors.py`
- `python/portfolio/postgres.py`
- `vercel.json`

## Validation Evidence

Pending implementation.

## Decisions

- Use one shared `qport_finance` schema in PostgreSQL; portfolio schemas remain user-isolated.
- Store one document row per symbol/source/document type/period with content hash uniqueness.
- Keep crawl execution behind an explicit admin action; user routes never call providers.

## Result

Pending.
