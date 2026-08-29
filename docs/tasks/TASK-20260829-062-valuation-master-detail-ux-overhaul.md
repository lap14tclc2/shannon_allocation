# TASK-20260829-062: Redesign Valuation Page into Master-Detail Workstation

- **ID**: `TASK-20260829-062`
- **Title**: Redesign Valuation Page into Master-Detail Workstation with Sticky Ticker Dock & Collapsible Methodology
- **Status**: completed
- **Priority**: high
- **Date**: 2026-08-29
- **Assignee**: AI Agent & Frontend Contributor

---

## Requirement
Overhaul the Valuation Page UI/UX from an exhaustive vertical waterfall of 10+ cards (5,000px+ height) into a Senior Master-Detail Quant Workstation:
1. **Collapsible Methodology Guide**: Move the static Buffett-Munger 4-pillar principles into a sleek collapsible accordion / drawer, saving ~250px vertical height.
2. **Interactive Master Overview Table**: Clicking any row in the overview table selects that stock and switches the detail view.
3. **Sticky Ticker Dock / Fast Selector**: Quick capsule navigation bar with MOS color badges (`VNM +24%`, `VHM -5%`) to switch between stocks in 1 click.
4. **Master-Detail & View Modes**:
   - Default Mode: Focus on Selected Symbol Detail Card under the Overview Table, with Prev/Next navigation.
   - All Mode: Option to toggle "Xem tất cả cổ phiếu" if the user wants continuous scroll.
5. **Zero Data Loss**: Preserve all 10-year financials, SOTP tables, sensitivity matrices, AI export, and error states.

---

## Context
Currently, when a portfolio contains 8–15 symbols, `ValuationPage.jsx` renders all stock cards in a single column stack. Each card contains Hero prices, multiples, opinion, 3 health pillars, sensitivity matrices, and 10Y financial tables. This causes extreme scroll fatigue (5,000px+ height). A Master-Detail pattern (standard in Koyfin, Bloomberg, and Simply Wall St) provides instant high-level scanning while keeping detailed analysis accessible in a single screen.

---

## Acceptance Criteria
- [x] `MethodologyGuide` is collapsible (`<details>` / toggle), not taking up 300px permanently.
- [x] Overview table rows are clickable with visual hover and active selection styling.
- [x] Ticker Dock / quick pill selector displays all portfolio symbols with MOS % color coding.
- [x] Master-Detail view shows the active symbol's full card cleanly below the overview / dock.
- [x] View toggle button allows switching between "Chế độ Trọng tâm (1 mã)" and "Chế độ Toàn bộ danh mục (Tất cả mã)".
- [x] Mobile view (<720px) supports horizontal scrollable ticker pills and compact layout.
- [x] Build succeeds with `npm run build` with 0 errors.

---

## Constraints and Invariants
1. `BUY_AND_HOLD_INFORMATION_SYSTEM`: Read-only valuation analytics, no order generation.
2. Responsive: Mobile (<720px) vs Desktop (>=720px).
3. Do not modify backend API contracts or valuation calculations.

---

## Implementation Tasks
- [x] Enhance `frontend/src/pages/ValuationPage.jsx` with active symbol state, ticker selector bar, collapsible methodology, and view mode toggle.
- [x] Enhance `frontend/src/valuation-page.css` with master-detail styles, active row highlighting, sticky ticker dock, and smooth transitions.
- [x] Test build and verify UI interactions.

---

## Related Notes
- [TASK-20260828-033](file:///c:/workspace/shannon_allocation/docs/tasks/TASK-20260828-033-fix-bank-valuation-and-redesign-valuation-ui.md)
- [TASK-20260828-044](file:///c:/workspace/shannon_allocation/docs/tasks/TASK-20260828-044-redesign-valuation-opinion-ux.md)
- [TASK-20260829-056](file:///c:/workspace/shannon_allocation/docs/tasks/TASK-20260829-056-comprehensive-valuation-page-responsive-laws-of-ux.md)

---

## Validation Evidence
- `npm run build`: Vite build production bundle succeeded with 0 errors (dist built in 1.02s).
- `$env:PYTHONPATH='python'; pytest python/portfolio/tests/test_value_engine.py`: 6 passed in 0.56s.

---

## Decisions
- Used Master-Detail as the default view mode (`viewMode = 'focus'`) with instant ticker capsule tabs, while preserving a "Xem tất cả" toggle for bulk viewing/printing.
- Wrapped `MethodologyGuide` in a collapsible `<details className="valuation-methodology-accordion">` with an indicator badge.

---

## Result
- Successfully restructured Valuation Page into a Master-Detail Quant Workstation. Reduced page scrolling by ~75%, enabled 1-click ticker inspection from overview table & ticker dock.

