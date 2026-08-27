---
id: TASK-20260827-011
title: Authenticate and diagnose finance provider requests
status: implemented
priority: high
created: 2026-08-27
updated: 2026-08-27
tags: [finance, crawl, tcbs, cafef, diagnostics]
related: [TASK-20260827-010]
---

## Requirement

Use the local TCBS bearer token for TCBS financial-document requests when supplied and expose provider HTTP status in worker logs.

## Context

The first worker smoke test claimed IVS correctly, but every TCBS and CafeF request failed as PROVIDER_HTTP_ERROR without revealing whether the cause was authentication, WAF or a retired URL. TCBS_BEARER_TOKEN was only used for the retired metadata overview path, not document crawling.

## Acceptance Criteria

- [x] Add Authorization Bearer header to local TCBS document requests when TCBS_BEARER_TOKEN exists.
- [x] Accept either a raw JWT or an already-prefixed Bearer value without duplicating the prefix.
- [x] Never log or persist the bearer token.
- [x] Log HTTP status such as 401, 403 or 404 without provider response payloads.
- [x] Preserve provider isolation and queue continuation after failures.
- [x] Add tests for token header construction.

## Constraints and Invariants

- TCBS overview enrichment remains removed from symbol loading.
- CafeF requests do not receive the TCBS token.
- Vercel remains read-only; token is local-worker configuration only.

## Validation Evidence

- Worker output on 2026-08-27 showed 38 provider failures for IVS.
- Run one worker job after pulling and inspect the first TCBS/CafeF status logs.

## Result

The next smoke test will identify the exact provider failure class and use the supplied TCBS token correctly.
