---
id: TASK-20260827-025
title: Replace CafeF worker with authenticated TCBS financial provider
status: in_progress
priority: critical
created: 2026-08-27
updated: 2026-08-27
tags: [finance-data, tcbs, value-engine, provider]
related: [TASK-20260827-024]
---

## Requirement

Remove CafeF from the active finance worker, clear existing CafeF crawl data
safely, and ingest the authenticated TCBS financial statement endpoints into
the canonical facts required by Value Engine.

## Acceptance Criteria

- [x] Worker has TCBS as its only active provider and uses the configured
  `apiextaws.tcbs.com.vn/tcanalysis/v1/finance` endpoint family.
- [x] A `clear-cafef --confirm` command removes CafeF raw documents, derived
  facts, parse errors, and dividend observations without deleting TCBS data.
- [x] A token-safe probe checks cashflow, balancesheet, and incomestatement for
  one symbol and reports status/record shape without printing the token.
- [x] The TCBS history response is narrowed to the requested year/quarter before
  persistence; a document is never canonicalized from a different period.
- [x] Reliable TCBS fields map to canonical Value Engine facts, while absent
  fields remain missing and block valuation safely.
- [x] Contract tests cover endpoint selection, period selection, mapping, and
  provider cleanup.

## Constraints

- Bearer credentials remain environment variables only; never commit or log them.
- Do not use TLS fingerprint evasion, CAPTCHA bypass, or browser challenge bypass.
- Vercel remains read-only and never calls TCBS.
- Preserve only standard authenticated HTTP behavior with bounded retries.

## Prepared crawler JSON ingestion

- [ ] Load one JSON file per symbol from `docs/crawler/*.json` without any
  provider request.
- [ ] Support the combined TCBS envelope containing the six
  `incomestatement/balancesheet/cashflow` quarter/year arrays.
- [ ] Reuse exact period selection and canonical mappings for all files, with
  incremental success-preserving behavior.

## Validation

- [ ] Run the local probe with an active TCBS token.
- [ ] Clear CafeF data locally and re-crawl one symbol.
- [ ] Run Value Engine readiness audit for that symbol.
- [x] Static source review completed against the FPT TCBS fixture.

## Result

The parser and worker implementation are complete. Runtime probe, database
cleanup, and end-to-end Value Engine verification remain environment-dependent.
