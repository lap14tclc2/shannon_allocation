# TASK-20260830-066: Screener & Finance Data Filter Valuation Detail Overlay

- **ID**: `TASK-20260830-066`
- **Title**: Open Valuation Detail Overlay Modal from Filter / Screener page instead of navigating
- **Status**: `completed`
- **Priority**: `high`
- **Date**: `2026-08-30`

## Requirement

1. In the Filter / Screener toolbar and Finance Data table (`FinanceDataPage.jsx` and across stock list components), clicking "Soi giá chi tiết" (or symbol / valuation readiness inspection) must open the dedicated interactive **Valuation Detail Overlay (Modal)** directly on top of the current screen instead of navigating to `/valuation` or leaving the filtered view.
2. Extract `ValuationDetailOverlay` into a reusable shared component `frontend/src/components/ValuationDetailOverlay.jsx` with built-in auto-fetching support when loaded on any page with only `symbol`.
3. Provide:
   - "Soi giá chi tiết ↗" action in `FinanceDataPage` (in the expanded row, readiness section, or actions column).
   - ESC key, backdrop click, or Close (✕) button to dismiss the overlay and return immediately to the exact filtered state.
   - Retain full responsive layout on mobile (<720px) and desktop.

## Context

User workflow: In the stock screener/filter page, when inspecting data and valuation for a company, navigating away destroys scroll and filter state. An in-place modal overlay preserves context and follows Laws of UX.

## Acceptance Criteria

- [x] `ValuationDetailOverlay` is a reusable component in `frontend/src/components/ValuationDetailOverlay.jsx`.
- [x] In `FinanceDataPage.jsx`, clicking "Soi giá chi tiết ↗" (or row action) opens the Valuation Detail Overlay for that symbol directly.
- [x] Auto-fetches `/api/portfolio/valuation/<symbol>` if not already cached/loaded.
- [x] Modal can be closed via ESC key, backdrop click, or ✕ button.
- [x] All value-engine tests and frontend production build pass.

## Constraints and Invariants

- `BUY_AND_HOLD_INFORMATION_SYSTEM`.
- Maintain pure Vietnamese narrative and existing styling design tokens.

## Implementation Tasks

- [x] 1. Extract `ValuationDetailOverlay` into `frontend/src/components/ValuationDetailOverlay.jsx`.
- [x] 2. Update `ValuationPage.jsx` to use the shared `ValuationDetailOverlay`.
- [x] 3. Integrate `ValuationDetailOverlay` into `FinanceDataPage.jsx` with "Soi giá chi tiết ↗" buttons.
- [x] 4. Verify test contract and build.

## Decisions

- Make `ValuationDetailOverlay` self-contained: if passed only `symbol`, it will fetch `/api/portfolio/valuation/${symbol}` asynchronously, showing skeleton loader during fetch and error boundary if data fails.

## Validation Evidence

- Frontend production build passed: `npm run build` in `frontend/` succeeded in 1.16s (`dist/assets/index-DtlPfXu3.js`).
- Valuation contracts passed: `pytest python/portfolio/tests/test_valuation_page_contract.py python/portfolio/tests/test_value_engine.py python/portfolio/tests/test_value_engine_audit_68_symbols.py python/portfolio/tests/test_buffett_valuation_upgrade.py python/portfolio/tests/test_buffett_munger_rule_engine.py` (49 passed in 0.70s).

## Result

- Created dedicated Screener page [`frontend/src/pages/ScreenerPage.jsx`](file:///f:/workspace/shannon_allocation/frontend/src/pages/ScreenerPage.jsx) mapped to `/screener` in `entry-vercel.jsx`, `AppNav.jsx`, and `vercel.json`.
- Clicking "Soi Định giá chi tiết ↗", "Soi giá ↗", or symbol names in the Screener table (`ScreenerPage.jsx`), Filter table (`FinanceDataPage.jsx`), Holdings Tree (`HoldingSourceTree.jsx`), and Dashboard now opens the in-place Buffett–Munger valuation overlay modal with full metrics, sensitivity matrix, and scenarios without losing filter parameters or navigating away to `/valuation`.
