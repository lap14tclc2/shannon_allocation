---
id: TASK-20260906-099
title: Open Valuation Overlay from Allocation Opportunities
status: in-progress
priority: medium
created: 2026-09-06
updated: 2026-09-06
tags: [allocation, valuation, overlay, ux]
related: [TASK-20260830-065-valuation-detail-overlay-modal-ux.md, TASK-20260830-066-finance-data-filter-valuation-overlay.md, TASK-20260906-095-buffett-thorp-allocation.md]
---

## Requirement

On `/allocation`, clicking `Xem định giá` in a New Opportunity card must open the existing in-place valuation detail overlay instead of navigating away to `/valuation?s=...`.

The interaction should match the existing Screener/Start-page valuation detail experience.

## Context

`AllocationPage.jsx` previously called `navigate(`/valuation?s=${symbol}`)`. QPort already has a reusable `ValuationDetailOverlay` component used by Screener, with `symbol`, `crawlEnabled`, and `onClose` props.

## Acceptance Criteria

- [x] Clicking `Xem định giá` on an Allocation opportunity keeps the user on `/allocation` at source-code level.
- [x] Reuse existing `ValuationDetailOverlay`; do not duplicate valuation UI.
- [x] Overlay receives the selected opportunity symbol and `onClose` clears the selection.
- [x] Existing `/valuation`, `/screener`, and allocation business logic remain unchanged.
- [x] Reuse existing valuation overlay stylesheet for responsive/mobile behavior.

## Constraints and Invariants

- Reuse existing canonical valuation UI/API behavior.
- No change to allocation recommendations or portfolio state.
- No ledger mutation.
- No new valuation engine or duplicate overlay implementation.

## Implementation Tasks

- [x] Import `ValuationDetailOverlay` and valuation overlay styles in `AllocationPage.jsx`.
- [x] Add local `selectedSymbol` state.
- [x] Replace valuation navigation callback with in-place symbol selection.
- [x] Render overlay with `onClose` clearing the selection.
- [ ] Run frontend production build in a checkout/runtime environment.

## Related Notes

- Existing Screener pattern: `selectedSymbol && <ValuationDetailOverlay symbol={selectedSymbol} ... />`.

## Validation Evidence

Source verification on branch `feature/buffett-thorp-allocation` confirms:

- `AllocationPage.jsx` imports `ValuationDetailOverlay`.
- `navigate('/valuation?s=...')` was removed from the opportunity action.
- opportunity cards now call `setSelectedSymbol`.
- selected symbol renders `ValuationDetailOverlay` with `locale` and `onClose`.
- existing overlay stylesheet is imported.

Commit: `8b2717d7d1401c0ba0746648346217a7be3a248e` (`fix(allocation): open valuation detail in overlay`).

Frontend build was not executed in the connector-only environment, so the task remains `in-progress` until build evidence is recorded.

## Decisions

Reuse the exact existing `ValuationDetailOverlay` component so the UX remains consistent across Screener and Allocation.

## Result

Source change implemented and pushed. Pending frontend build verification before marking verified/completed.
