# TASK-20260830-068: Hide Empty UI Sections & Remove Operations Page

**Status**: completed
**Priority**: High
**Date**: 2026-08-30

## Requirement
1. **Hide Empty UI Sections**:
   - In `ValuationDetailOverlay.jsx`, `ValuationPage.jsx`, and other UI cards: dynamically check whether data exists before rendering any section or accordion.
   - If `owner_earnings_bridge` is missing or has no values, hide the Owner Earnings Bridge.
   - If `sotp_sensitivity_matrix` and `dcf_sensitivity_matrix` are missing, hide the Sensitivity Matrix section.
   - If both bridge and sensitivity matrix are empty, hide the entire "Chi tiết Kỹ thuật" accordion.
   - If `value_investor_pillars` is empty or missing, hide the "3 Trụ cột Sức khỏe Doanh nghiệp" accordion.
   - If `sector_conflict_warning` is empty, hide the warning box.
   - If `financial_resilience_diagnosis` is empty, hide the financial health box.
2. **Remove Operations Page (`/operations`)**:
   - Remove "Vận hành" (`/operations`) from `AppNav.jsx` links.
   - Remove `/operations` from `entry-vercel.jsx`, `entry-client.jsx`, `ssr-entry.jsx`, and `vercel.json` (or map/redirect to dashboard).

## Validation Evidence
- `npm run build` completed in 1.40s (`dist/assets/index-DLE7wq2m.js`).
- 4/4 valuation contract tests passed.

## Decisions
- Conditionally omit entire accordion containers if their inner child sections have no data.

## Result
- Added strict data existence checks across all valuation sub-sections (multiples grid, 3-scenario progressive track, value health pillars, owner earnings bridge, and SOTP sensitivity matrix).
- Completely removed the Operations page (`/operations`) from navigation menus, entry routes, and server configuration.
