# TASK-20260830-074: Premium Visual Polish & Hierarchy for Valuation Cards

**Status**: in-progress
**Priority**: High
**Date**: 2026-08-30

## Requirement
Transform the Valuation Card layout into a world-class, premium editorial financial card design matching the Japanese Retro Ledger aesthetic:
1. **Hero Price Cards**:
   - Modernize the 3 price boxes with sleek card borders, background gradients/tints, and prominent monetary typography.
   - Highlight Intrinsic Value with accent cinnabar badge and Margin of Safety with high-contrast color pills.
2. **Multiples Stat Chips**:
   - Redesign P/E, P/B, EPS, ROE into sleek 2-line financial stat badges with crisp monospace numerals.
3. **Buffett–Munger Expert Opinion Box**:
   - Enhance the editorial card with a gold seal header, styled verdict callout, and formatted financial resilience notes.
4. **3 Health Pillars**:
   - Professional pillar cards with styled numbering, rounded status tags, prominent metric values, and elegant typography.
5. **3 Scenarios & Technical Collapsible**:
   - Color-coded scenario cards (Bear: slate/muted, Base: cinnabar/accent, Bull: emerald/green).
   - Polished details accordion with smooth transition.

## Acceptance Criteria
- [ ] Price hero cards have distinct visual hierarchy and elegant styling.
- [ ] Metric chips display clean 2-line stat badge layout.
- [ ] Analyst opinion has editorial callout styling.
- [ ] 3 Pillars have crisp badges, aligned metrics, and zero jagged text.
- [ ] 3 Scenarios are color-coded and distinct.
- [ ] Responsive on both Desktop and Mobile (< 720px).
- [ ] All tests pass & build succeeds.

## Constraints and Invariants
- Theme color synchronization (Retro Light & Cyber Dark).
- Pure Vietnamese terminology constraint.

## Validation Evidence
*To be filled.*

## Decisions
- Refine `.valuation-price-hero`, `.metric-chip`, `.pillar-card`, `.valuation-analyst-opinion`, and `.scenario-card` in `valuation-page.css`.

## Result
*To be filled.*
