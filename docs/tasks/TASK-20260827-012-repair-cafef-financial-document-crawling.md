---
id: TASK-20260827-012
title: Repair CafeF financial-document crawling
status: implemented
priority: high
created: 2026-08-27
updated: 2026-08-27
tags: [finance, crawl, cafef, html, diagnostics]
related: [TASK-20260827-011]
---

## Requirement

Restore financial-document crawling when CafeF returns its current HTML financial-report pages.

## Context

The worker correctly claimed queue jobs, but every CafeF request used an obsolete URL under `s.cafef.vn/bao-cao-tai-chinh` and the parser accepted JSON only. Current CafeF report pages use `cafef.vn/du-lieu/bao-cao-tai-chinh` and return HTML tables.

## Acceptance Criteria

- [x] Use the current CafeF financial-report route.
- [x] Use the `BSheet` segment for balance sheet reports.
- [x] Parse label/value rows from CafeF HTML without adding a runtime dependency.
- [x] Preserve raw payload storage and canonicalization flow.
- [x] Keep TCBS status diagnostics separate.
- [x] Add regression tests for HTML parsing and route construction.

## Constraints and Invariants

- No provider response body or credential is written to logs.
- Existing successful documents are still skipped by incremental crawl logic.
- Vercel remains read-only; the worker runs locally.
- HTML scraping remains subject to CafeF layout/rate-limit changes.

## Validation Evidence

- Current CafeF report pages were verified to use `/du-lieu/bao-cao-tai-chinh` and HTML table rows.
- Runtime worker validation is pending on the user's local database.

## Result

The next worker run should report CafeF HTTP status and, when the route is available, persist HTML rows for normalization. TCBS may still report 404 and must not be treated as available until its route is replaced or confirmed.
