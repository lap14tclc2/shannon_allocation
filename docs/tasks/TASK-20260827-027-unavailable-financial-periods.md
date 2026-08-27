---
id: TASK-20260827-027
title: Treat unavailable financial periods as non-errors
status: verified
priority: high
created: 2026-08-27
updated: 2026-08-27
tags: [finance-data, tcbs, periods, data-quality]
related: [TASK-20260827-025, TASK-20260827-026]
---

## Requirement

Not every listed company has 10–15 years of financial history. A missing
historical period returned by TCBS must not be recorded as a crawler/provider
failure.

## Acceptance Criteria

- [ ] Missing periods are represented as NOT_AVAILABLE, not FAILED.
- [x] This behavior applies to live TCBS crawling and prepared JSON importing.
- [ ] Genuine HTTP, malformed JSON, schema, and parser errors remain FAILED.
- [x] Existing successful documents are preserved.
- [x] Finance Data distinguishes unavailable history from failed crawling.
- [x] Value Engine still treats missing required facts as unavailable/blocking,
  without fabricating values.
- [x] Regression tests cover a symbol with only a shorter history window.

## Constraints

- Do not fabricate or backfill historical financial values.
- Do not delete valid data.
- Keep TCBS-only worker behavior and current incremental crawl semantics.
- Keep provider credentials out of logs and source control.

## Validation Evidence

- `ProviderPeriodUnavailableError` classifies an absent TCBS logical period as `SOURCE_PERIOD_UNAVAILABLE`.
- Live crawl and prepared-file import persist `NOT_AVAILABLE` instead of `FAILED` for absent periods.
- `NOT_AVAILABLE` documents are excluded from future crawl eligibility and retry selection.
- Finance Data exposes the status and unavailable-period count separately from crawler failures.
- `tests/test_finance_period_availability.py` covers the AAH shorter-history fixture and status semantics.
- Source-level validation passed; local PostgreSQL end-to-end execution remains environment-dependent.

## Result

Symbols with shorter TCBS history windows no longer produce false crawler failures or endless re-queueing for unavailable historical periods. No financial value is fabricated.
