# TASK-20260830-075: Redesign Buffett–Munger Opinion Section with Visual Executive Cards

**Status**: in-progress
**Priority**: High
**Date**: 2026-08-30

## Requirement
Transform the text-heavy Buffett–Munger opinion section into a clean, executive-level visual dashboard:
1. **Header**: Seal icon, title, and status pill tag.
2. **4-Card Executive Grid**:
   - Card 1: Economic Archetype & Model.
   - Card 2: Valuation Range (Bear – Bull) & Base IV.
   - Card 3: Actual Margin of Safety vs Required Margin of Safety.
   - Card 4: Quality Score & Tier.
3. **Strategic Insight Callout**:
   - Formatted callout box with 💡 icon for capital structure & financial resilience diagnosis.

## Acceptance Criteria
- [ ] Replace text wall in `.valuation-analyst-opinion` with 4-chip executive grid.
- [ ] Render clear, readable typography with no text clumping.
- [ ] Maintain pure Vietnamese terminology constraint.
- [ ] Build & contract tests pass on both `F:\` and `C:\`.

## Constraints and Invariants
- `BUY_AND_HOLD_INFORMATION_SYSTEM` invariant.
- Theme tokens synchronization.

## Validation Evidence
*To be filled.*

## Decisions
- Structure opinion data into `opinion-executive-grid` with `opinion-stat-item` cards.

## Result
*To be filled.*
