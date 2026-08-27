---
id: TASK-20260827-022
title: Fix CafeF dividend history placeholders and retry semantics
status: in_progress
priority: high
created: 2026-08-27
updated: 2026-08-27
tags: [finance-data, dividends, cafef]
related: [TASK-20260827-020, TASK-20260827-021]
---

## Requirement

Represent CafeF dividend data as one history document per symbol/provider/run.
Do not create misleading annual PENDING placeholders for a provider endpoint that
returns the complete dividend history.

## Acceptance Criteria

- [x] Worker creates/fetches one CafeF dividend-history document per symbol.
- [x] Dividend history is not duplicated across FY 2016–2025 placeholders.
- [x] Existing legacy rows remain preserved and are excluded from the active view.
- [x] Retry/status logic reports the single history document accurately.
- [x] Add regression tests and update runbook.

## Constraints and Invariants

- Keep the existing dividend reconciliation and source provenance.
- Do not delete historical database records in the application code.
- Do not call CafeF once per historical year.
- TCBS remains disabled in the worker.

## Implementation

- Dividend placeholders are now created only for the latest completed FY, matching
  the CafeF endpoint's full-history response.
- Active catalog summaries and document lists hide legacy annual dividend rows.
- Existing database rows are preserved; no destructive cleanup is performed.
- Added regression coverage and updated the runbook.

## Remaining Validation

- [ ] Restart the local API and worker, then verify one CafeF dividend history row
  is shown per symbol.
- [ ] Run the full Python suite and Vite build.

## Result

Implementation complete; runtime validation pending.
