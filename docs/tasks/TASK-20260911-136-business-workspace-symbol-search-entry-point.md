# TASK-20260911-136: Business Workspace Symbol & Company Search Entry Point

- **Status**: draft
- **Priority**: high
- **Date**: 2026-09-11
- **Target Branch**: `feature/buffett-munger-refactor`

---

## Requirement
Redesign `/business` workspace as the primary research entry point by introducing a prominent user-facing ticker and company search interface.
Allow users to search and research ANY company in the Finance DB / canonical symbol universe (e.g. `ACB`, `DGC`, `FPT`, `VIX`) regardless of whether the stock is currently held in the user's portfolio.
Add a quick company search entry point to Terminal navigation header (desktop & mobile).

---

## Context
A product gap was discovered: the `/business` workspace previously lacked a user-facing search entry point, forcing users to manually edit the URL (e.g. `/business/FPT`) or only click on existing portfolio holdings.
Business analysis for candidate companies and existing portfolio holdings must use the EXACT same underlying research engine (`canonical_facts` -> `build_canonical_valuation` -> `ValueTrap` -> `BusinessReview` -> `InvestmentDecisionContext`). Portfolio holding status may affect position capacity and action semantics (e.g. `HOLD` vs `WAIT_FOR_MOS`), but must NOT alter fundamental business valuation.

---

## Acceptance Criteria
- [ ] `/business` has a prominent ticker/company search input component.
- [ ] User can type `ACB` and navigate to `/business/ACB`.
- [ ] User can type `FPT` and navigate to `/business/FPT`.
- [ ] Non-held candidate companies can be discovered and researched.
- [ ] Search query executes against the Finance DB symbol catalog (`/api/portfolio/screener/symbols` or canonical symbol universe).
- [ ] No hardcoded ticker lists in the frontend.
- [ ] No external crawl/HTTP fetch triggered by searching (search is discovery-only).
- [ ] Keyboard navigation (Arrow Up/Down, Enter, Esc) works seamlessly in search results dropdown.
- [ ] Pressing Enter on search input opens exact or currently highlighted symbol.
- [ ] Proper UI states implemented: Loading state, Empty query state, No-results state.
- [ ] Fully responsive layout for both Desktop and Mobile devices.
- [ ] Terminal header exposes quick company search shortcut navigating to `/business/:symbol`.
- [ ] Candidate companies and portfolio holdings use the identical Business research pipeline.

---

## Constraints and Invariants
1. Do NOT hardcode symbol lists in frontend components.
2. Search query MUST search Finance DB canonical symbol catalog, not portfolio holdings only.
3. Search is discovery only; does NOT trigger external downloads or network crawl.
4. Candidate companies and portfolio holdings MUST use the exact same Business research engine.
5. Holding status affects action semantics (e.g., `HOLD` vs `WAIT_FOR_MOS`), but does NOT alter underlying intrinsic valuation.
6. Do NOT merge into `main`.

---

## Implementation Tasks
- [ ] Backend API: Verify or add `/api/portfolio/search/symbols?q=...` endpoint returning canonical symbols and company names from `qport_finance`.
- [ ] Frontend Component: Build reusable `SymbolSearchModal` or `SymbolSearchInput` component with keyboard navigation, debounce, loading, empty, and no-results states.
- [ ] Frontend Page: Integrate search component prominently into `/business` main page (`BusinessWorkspacePage.jsx`).
- [ ] Frontend Header: Add quick search bar to Terminal header (`TerminalHeader.jsx` or main navigation header) on Desktop and a compact search icon modal trigger on Mobile.
- [ ] Routing: Ensure selecting a search result navigates cleanly to `/business/:symbol`.
- [ ] Tests: Add frontend/backend tests verifying search API contract, non-held candidate research, and keyboard navigation.

---

## Related Notes
- [docs/tasks/TASK-20260911-135-runtime-valuation-evidence-propagation.md](file:///c:/workspace/shannon_allocation/docs/tasks/TASK-20260911-135-runtime-valuation-evidence-propagation.md)

---

## Validation Evidence
*(Will be populated during verification)*

---

## Decisions
*(Will be populated during execution)*

---

## Result
*(Will be populated upon completion)*
