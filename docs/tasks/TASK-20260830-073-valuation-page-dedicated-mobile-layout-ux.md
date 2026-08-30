# TASK-20260830-073: Dedicated Mobile Layout & Laws of UX Responsiveness for Valuation Page

**Status**: in-progress
**Priority**: High
**Date**: 2026-08-30

## Requirement
Create a dedicated, high-polish Mobile layout for the Valuation Page (`/valuation`) that strictly follows the Laws of UX:
1. **Mobile Overview Cards (< 720px)**:
   - Replace the cramped 12-column table on mobile with sleek, tap-friendly **Mobile Overview Cards** (Fitts's Law: min 48px touch targets; Miller's Law: 3 key metrics grouped cleanly).
   - Desktop (>= 720px) retains the full financial data table.
2. **Mobile Detail Card Layout**:
   - Stack Price Hero, Multiples (2x2 grid), 3 Pillars (1 column vertical stack), and 3 Scenarios cleanly.
   - Touch-friendly pagination controls (44px min height).
   - Horizontal scrolling containers for 2D sensitivity matrix with smooth inertia scrolling (`-webkit-overflow-scrolling: touch`).
3. **Zero Horizontal Layout Break / Overflow**:
   - `box-sizing: border-box`, prevent text clipping, clean padding for iPhone safe areas.

## Acceptance Criteria
- [ ] Dedicated mobile card overview renders on screen widths < 720px.
- [ ] Desktop table renders on screen widths >= 720px.
- [ ] Clicking any mobile card selects the stock and smooth scrolls to `#valuation-detail-section`.
- [ ] Detail cards, 3 pillars, and scenario boxes wrap cleanly on mobile with zero horizontal overflow.
- [ ] Pagination controls are large and touch-friendly on mobile.
- [ ] `npm run build` succeeds on both `F:\` and `C:\`.
- [ ] Contract tests pass.

## Constraints and Invariants
- `BUY_AND_HOLD_INFORMATION_SYSTEM` invariant.
- Theme tokens synchronization.

## Validation Evidence
*To be filled after implementation.*

## Decisions
- Render both `<div className="valuation-overview-desktop">` and `<div className="valuation-overview-mobile">` toggled via media query CSS for instant, flicker-free responsive layout transitions.

## Result
*To be filled upon completion.*
