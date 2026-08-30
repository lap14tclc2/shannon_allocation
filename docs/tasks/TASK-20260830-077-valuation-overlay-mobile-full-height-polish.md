# TASK-20260830-077: Valuation Detail Overlay Full-Height & Spacing Polish

**Status**: in-progress
**Priority**: High
**Date**: 2026-08-30

## Requirement
Transform `ValuationDetailOverlay` into a premium, full-height, ergonomic mobile experience and polish desktop spacing:
1. **Mobile Experience (< 720px)**:
   - Full-height / edge-to-edge modal (`height: 100dvh`, `width: 100%`, `max-height: 100dvh`).
   - Compact sticky top bar: Symbol + Status Badge on left, Close button (44px target) on right. No multi-line header crowding.
   - Scenario cards: Full-width clean 3-scenario card stack or grid without text wrapping issues.
   - Typography: No dangling currency symbols (e.g. `509.624 ₫` on single line with `white-space: nowrap`).
   - Safe-area-insets: `padding-bottom: calc(24px + env(safe-area-inset-bottom, 0px))`.
   - Pillar 2 fix: clean separation of number metric and subtitle.
2. **Desktop Overlay (>= 720px)**:
   - Polished 960px modal with consistent padding, backdrop blur, clean typography.

## Acceptance Criteria
- [ ] Mobile overlay occupies full height (`100dvh`) without background leaks.
- [ ] Compact header keeps close button at top-right without wrapping to new line.
- [ ] Currency values and numbers formatted with `white-space: nowrap`.
- [ ] Pillar cards and Scenarios formatted with balanced spacing.
- [ ] Builds and tests pass on both workspaces.

## Constraints and Invariants
- `BUY_AND_HOLD_INFORMATION_SYSTEM` invariant.
- Theme tokens synchronization.

## Validation Evidence
*To be filled.*

## Decisions
- Use full-screen mobile dialog pattern (`inset: 0; height: 100dvh`) for mobile viewports to maximize readability and eliminate awkward background gaps.

## Result
*To be filled.*
