# TASK-20260901-079: Valuation Narrative Minor Section 04 - Formula & Quantitative Breakdown

**Status**: in-progress
**Priority**: High
**Date**: 2026-09-01

## Requirement
Add minor section **04 · Công thức Tính toán & Chi tiết Định lượng Giá trị Thực** inside the major section *"Vì sao Giá trị Thực cơ sở = ... ₫?"*:
1. **Mathematical Formula**:
   - Clear mathematical formulas for Enterprise Value (EV), Equity Value, and Intrinsic Value Per Share (IV).
   - Specialized formula display for Banking (Residual Income / P/B Model) vs Operating Businesses (Owner Earnings DCF).
2. **Quantitative Concrete Step-by-Step Substitution**:
   - Step 1 (EV calculation): PV(5Y Cash Flows) + PV(Terminal Value) = EV.
   - Step 2 (Equity Value calculation): EV + (Cash - Debt) = Equity.
   - Step 3 (Per-Share Intrinsic Value): Equity / Shares Outstanding = Intrinsic Value / Share.
3. **Responsive Mobile UX**:
   - Fully responsive for mobile (`< 720px`) with adaptive flex/grid stacks.
4. **Theme Synchronization**:
   - Seamless compatibility with both Washi Retro (Light mode) and Cyber (Dark mode).

## Acceptance Criteria
- [ ] Section 04 renders below Section 03 in the major valuation narrative section.
- [ ] Displays exact formula and actual substituted numerical figures.
- [ ] Responsive layout adapts cleanly on mobile without horizontal scrolling or wrapping issues.
- [ ] Fully styled with theme tokens (`var(--surface-soft)`, `var(--panel)`, `var(--border)`, `var(--accent)`).
- [ ] Tests and builds pass on both workspaces.

## Constraints and Invariants
- `BUY_AND_HOLD_INFORMATION_SYSTEM` invariant.
- Theme tokens synchronization.

## Validation Evidence
*To be filled.*

## Decisions
- Encapsulate the 4-step explanation into a dedicated, reusable component `IntrinsicValueExplanationSection` used by both `ValuationPage.jsx` and `ValuationDetailOverlay.jsx`.

## Result
*To be filled.*
