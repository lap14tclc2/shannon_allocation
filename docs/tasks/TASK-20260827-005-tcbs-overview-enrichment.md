---
id: TASK-20260827-005
title: Use Vnstock bulk metadata for the Finance universe
status: implemented
priority: high
created: 2026-08-27
updated: 2026-08-27
tags: [finance, vnstock, universe, metadata]
related: [TASK-20260827-003, TASK-20260827-004]
---

## Requirement

Populate the Finance Data symbol universe without TCBS authentication or per-symbol TCBS requests. Use the Vnstock APIs already available on the local worker for exchange, company name and ICB industry metadata.

## Context

The Vnstock all_symbols function intentionally returns only the symbol and company name. Local verification of symbols_by_exchange returned symbol, organ_name, exchange, and type. TCBS overview enrichment is therefore unnecessary and fails with HTTP 403.

## Acceptance Criteria

- [x] Do not read TCBS_BEARER_TOKEN or call a TCBS overview endpoint during symbol sync.
- [x] Use Listing.symbols_by_exchange as the bulk source for symbol, company and exchange.
- [x] Use Listing.symbols_by_industries as a best-effort bulk source for ICB industry.
- [x] Merge metadata by symbol and keep level-1 ICB industry for the universe table.
- [x] Continue syncing exchange/name metadata if the industry bulk call fails.
- [x] Preserve progress, quality and mapping-sample logs.
- [x] Add regression tests for the Vnstock merge and TCBS removal.

## Constraints and Invariants

- Vnstock is used only by the local/worker runtime.
- TCBS and CafeF remain the separate document providers for financial-statement crawling.
- A later incomplete source must not overwrite known exchange/industry values with UNKNOWN.
- No token or provider response payload is logged.

## Validation Evidence

- Local worker output on 2026-08-27 showed symbols_by_exchange returning valid HOSE/HNX/UPCOM metadata.
- Run the targeted pytest test and one local universe sync after pulling this commit.

## Result

The universe sync uses Vnstock bulk metadata APIs only. TCBS authentication is no longer part of the symbol-loading path.
