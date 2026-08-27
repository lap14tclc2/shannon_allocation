---
id: TASK-20260827-006
title: Filter crawlable equities from the Finance universe
status: implemented
priority: high
created: 2026-08-27
updated: 2026-08-27
tags: [finance, vnstock, universe, crawl, data-quality]
related: [TASK-20260827-005]
---

## Requirement

Before creating finance-document placeholders or crawl-queue entries, retain only ordinary listed equities. Exclude warrants and rows whose symbol, exchange or company name is invalid. Remove previously imported invalid instruments from the active universe after a successful refresh.

## Context

The direct Vnstock exchange feed includes multiple instrument types. The Finance Data screen showed warrant-style codes such as 41B5G9000 and rows with company name nan. Those must never be eligible for BCTC/dividend crawling.

## Acceptance Criteria

- [x] Accept only records whose Vnstock type is STOCK.
- [x] Require a non-empty symbol, a recognised HOSE/HNX/UPCOM exchange and a valid company name.
- [x] Filter before upserting securities, creating PENDING documents or enqueueing work.
- [x] Re-enable valid securities on a later successful sync.
- [x] Mark previously active symbols that are absent from the filtered universe inactive.
- [x] Cancel queued crawl jobs for newly inactive symbols, and reject direct crawl attempts for inactive symbols.
- [x] Log accepted/rejected/deactivated counts without printing source payloads.
- [x] Add regression coverage for warrants, nan names and unknown exchanges.

## Constraints and Invariants

- Industry is optional: lack of ICB data must not block a valid listed equity.
- Existing crawl documents are preserved for audit; inactive instruments are hidden from list and queue operations.
- A failed refresh must not deactivate the existing universe.

## Validation Evidence

- Screenshot on 2026-08-27 showed warrant-style symbols and nan company names in the previous active universe.
- Run the targeted pytest test, sync universe locally and confirm the active count excludes rejected instrument types.

## Result

Only active ordinary listed equities can be displayed, receive document placeholders, or be queued for crawling.
