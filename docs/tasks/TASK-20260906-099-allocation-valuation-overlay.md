---
id: TASK-20260906-099
title: Open Valuation Overlay from Allocation Opportunities
status: in-progress
priority: medium
created: 2026-09-06
updated: 2026-09-06
tags: [allocation, valuation, overlay, ux]
related: [TASK-20260906-065-valuation-detail-overlay-modal-ux.md, TASK-20260906-066-finance-data-filter-valuation-overlay.md, TASK-20260906-095-buffett-thorp-allocation.md]
---

## Requirement

On `/allocation`, clicking `Xem định giá` in a New Opportunity card must open the existing in-place valuation detail overlay instead of navigating away to `/valuation?s=...`.

The interaction should match the existing Screener/Start-page valuation detail experience.

## Context

`AllocationPage.jsx` currently calls `navigate(`/valuation?s=${symbol}`)`. QPort already has a reusable `ValuationDetailOverlay` component used by Screener, with `symbol`, `crawlEnabled`, and `onClose` props.

## Acceptance Criteria

- [ ] Clicking `Xem định giá` on an Allocation opportunity keeps the user on `/allocation`.
- [ ] Reuse existing `ValuationDetailOverlay`; do not duplicate valuation UI.
- [ ] Overlay loads the selected opportunity symbol and can be closed back to the unchanged Allocation page.
- [ ] Existing `/valuation`, `/screener`, and allocation business logic remain unchanged.
- [ ] Preserve responsive/mobile behavior and existing valuation overlay styling.

## Constraints and Invariants

- Reuse existing canonical valuation UI/API behavior.
- No change to allocation recommendations or portfolio state.
- No ledger mutation.
- No new valuation engine or duplicate overlay implementation.

## Implementation Tasks

- [ ] Import `ValuationDetailOverlay` and valuation overlay styles in `AllocationPage.jsx`.
- [ ] Add local `selectedSymbol` state.
- [ ] Replace valuation navigation callback with in-place symbol selection.
- [ ] Render overlay with `onClose` clearing the selection.
- [ ] Verify source contract and frontend build if environment is available.

## Related Notes

- Existing Screener pattern: `selectedSymbol && <ValuationDetailOverlay symbol={selectedSymbol} ... />`.

## Validation Evidence

Pending.

## Decisions

Reuse the exact existing `ValuationDetailOverlay` component so the UX remains consistent across Screener and Allocation.

## Result

In progress.
