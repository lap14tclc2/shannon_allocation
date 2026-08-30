# TASK-20260830-071: Revert & Restore Valuation Page Item Card Layout & CSS

**Status**: in-progress
**Priority**: High
**Date**: 2026-08-30

## Requirement
Revert the Valuation page (`/valuation`) items to the clean, rich inline card layout and CSS:
1. **Restore Full Item Card**:
   - `ValuationCard` displays all valuation sections directly and cleanly (Header, Price Hero 3-box grid, Multiples ribbon, Buffett-Munger opinion, 3 Health pillars, Technical details).
   - Keeps data presence checks (empty sections auto-hide).
   - Keeps the live VNDirect market price.
   - Keeps "Chi tiết ↗" action button to open the full overlay modal if user wants deep dive.
2. **Restore Card CSS**:
   - Revert `frontend/src/valuation-page.css` to the clean, spacious card styling.
   - Retain overlay modal CSS for the standalone modal.

## Acceptance Criteria
- [ ] Valuation page items render with spacious, elegant retro-financial cards.
- [ ] No unwanted accordion wrapping or broken item CSS on `/valuation`.
- [ ] `npm run build` succeeds.
- [ ] Contract tests pass.

## Constraints and Invariants
- `BUY_AND_HOLD_INFORMATION_SYSTEM` invariant.
- Pure Vietnamese localization.

## Implementation Tasks
- [ ] Update `frontend/src/pages/ValuationPage.jsx` with rich ValuationCard.
- [ ] Update `frontend/src/valuation-page.css` with clean card styles.
- [ ] Sync, build, and verify.

## Related Notes
- [TASK-20260830-070](file:///f:/workspace/shannon_allocation/docs/tasks/TASK-20260830-070-add-current-price-from-vndirect.md)

## Validation Evidence
*To be filled after implementation.*

## Decisions
- Retain the clean `ValuationDetailOverlay` portal for overlay modal when clicking "Chi tiết ↗" while rendering full rich cards in the page feed.

## Result
*To be filled upon completion.*
