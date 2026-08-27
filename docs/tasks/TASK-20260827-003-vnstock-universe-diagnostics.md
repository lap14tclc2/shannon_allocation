---
id: TASK-20260827-003
title: Diagnose and improve Vnstock universe metadata
status: implemented
priority: high
created: 2026-08-27
updated: 2026-08-27
tags: [finance, vnstock, logging, crawler]
related: [TASK-20260827-001, TASK-20260827-002]
---

## Requirement

Keep Vnstock as the first universe provider, improve exchange/industry mapping, and emit enough local logs to diagnose source schema and finance-crawl progress.

## Acceptance Criteria

- [x] Normalize common Vnstock exchange aliases to HOSE, HNX and UPCOM.
- [x] Distinguish a missing exchange from an unrecognized exchange value.
- [x] Include expanded industry aliases.
- [x] Log Vnstock source columns and safe mapping samples.
- [x] Log each finance document fetch, success, failure and skip.
- [x] Do not log payloads, tokens, or credentials.
- [x] Add unit tests for new Vnstock mappings.

## Validation Evidence

Source-level tests added. Local Vnstock execution will print the actual returned columns and mapping samples for verification.

## Result

Implemented on dev. The next local universe sync will expose whether Vnstock supplies usable exchange and industry fields before deciding to change provider.
