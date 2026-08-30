# TASK-20260830-065: Valuation Detail Overlay Modal UX

- **ID**: `TASK-20260830-065`
- **Title**: Open Valuation Detail Overlay Modal on Item Click instead of page navigation
- **Status**: `completed`
- **Priority**: `high`
- **Date**: `2026-08-30`

## Requirement

1. When clicking on an item/row in the valuation overview/forecast table (or symbol tab strip, or holding item), open an interactive **Valuation Detail Overlay (Modal)** showing the full Buffett-Munger valuation report of the selected stock instead of navigating away or scrolling to an unselected collapsed card.
2. Provide seamless interaction:
   - ESC key, backdrop click, or Close (✕) button to dismiss.
   - URL query/hash support (`/valuation?symbol=XYZ` or `#XYZ`) to automatically open the detail overlay for that symbol.
   - Responsive design: clean centered dialog on desktop, bottom sheet / full modal on mobile (<720px).
3. The detail modal presents the comprehensive report:
   - Header with Ticker, Archetype, Quality Tier & Score, Valuation Pill verdict, and Close button.
   - Market Price, Base IV, Real MOS, Required MOS, Multiples ribbon.
   - In-depth Buffett-Munger Analyst Opinion, 4 Pillars Scorecard, 3 DCF Scenarios, Owner Earnings Bridge, SOTP/Concession breakdown (if applicable), and Sensitivity Matrix.

## Context

Users reviewing the overview table or holdings list want to inspect individual stock valuation without losing context or page position. Opening a dedicated detail overlay modal gives immediate focus and retains the Laws of UX principles.

## Acceptance Criteria

- [x] Clicking any row or action in `ValuationOverviewTable` opens the Valuation Detail Overlay for that symbol.
- [x] Clicking any symbol in `SymbolTabStrip` opens the Valuation Detail Overlay for that symbol.
- [x] Overlay can be closed via ESC key, clicking the backdrop, or clicking the close button.
- [x] Overlay is fully responsive on desktop (>=720px) and mobile (<720px).
- [x] Direct deep linking (`/valuation?symbol=XYZ` or `/valuation#XYZ`) automatically opens the modal for `XYZ`.
- [x] All value-engine tests and frontend production build pass.

## Constraints and Invariants

- `BUY_AND_HOLD_INFORMATION_SYSTEM`.
- Maintain pure Vietnamese narrative and existing styling design tokens.

## Implementation Tasks

- [x] 1. Create `ValuationDetailOverlay` component with full report view and accessibility controls.
- [x] 2. Update `ValuationOverviewTable` and `SymbolTabStrip` in `frontend/src/pages/ValuationPage.jsx` to manage `selectedSymbol` and trigger the detail overlay.
- [x] 3. Add CSS for `.valuation-overlay-backdrop`, `.valuation-overlay-modal`, and mobile responsive styles in `frontend/src/valuation-page.css`.
- [x] 4. Support URL query/hash parameter sync for deep-linking.
- [x] 5. Verify unit tests and build.

## Decisions

- Use React Portal (`document.body`) with focus management, ESC listeners, and backdrop blur to guarantee proper layering and zero layout shift.

## Validation Evidence

```text
$ $env:PYTHONPATH='python'; .\.venv\Scripts\pytest.exe python/portfolio/tests/test_valuation_page_contract.py python/portfolio/tests/test_buffett_munger_rule_engine.py python/portfolio/tests/test_value_engine.py python/portfolio/tests/test_value_engine_audit_fixes.py python/portfolio/tests/test_value_engine_audit_68_symbols.py
-> 57 passed in 0.95s

$ cd frontend && npm run build
-> vite build clean in 1.21s (0 errors)
```

## Result

Completed implementation of `ValuationDetailOverlay` and interactive click handlers in `ValuationOverviewTable`, `SymbolTabStrip`, and `ValuationCard`. Clicking any item now opens the comprehensive Buffett-Munger valuation detail modal in-place without page disruption.
