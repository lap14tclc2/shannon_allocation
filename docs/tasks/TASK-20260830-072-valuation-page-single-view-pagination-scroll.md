# TASK-20260830-072: Valuation Page Single-Symbol View, Pagination, and Smooth Scroll

**Status**: in-progress
**Priority**: High
**Date**: 2026-08-30

## Requirement
Refactor the Valuation Page (`/valuation`):
1. **Overview Table Pagination**: Add pagination (5 symbols per page) if portfolio has > 5 symbols.
2. **Remove Symbol Tab Strip**: Remove `SymbolTabStrip` above the table.
3. **No Overlay Modal on Valuation Page**: Clicking rows/actions in `/valuation` selects the symbol in-place instead of opening a popup modal.
4. **Single-Symbol Detail View**: Render detailed valuation for only 1 stock at a time (defaults to first symbol).
5. **Smooth Scroll**: Clicking a stock row in the table updates the selected stock and smoothly scrolls down to the detail section.

## Acceptance Criteria
- [ ] Table has 5 items/page pagination controls when total symbols > 5.
- [ ] No symbol tab strip rendered.
- [ ] No overlay modal popup on `/valuation`.
- [ ] Only 1 stock's detailed valuation card is rendered at any time (default: first symbol).
- [ ] Clicking any table row switches the active symbol and smoothly scrolls to `#valuation-detail-section`.
- [ ] `npm run build` succeeds on both `F:\` and `C:\`.
- [ ] Contract tests pass.

## Constraints and Invariants
- `BUY_AND_HOLD_INFORMATION_SYSTEM` invariant.
- Theme tokens synchronization.

## Validation Evidence
*To be recorded after implementation and testing.*

## Decisions
- Use `element.scrollIntoView({ behavior: 'smooth' })` when clicking a stock in the overview table.

## Result
*To be recorded upon completion.*
