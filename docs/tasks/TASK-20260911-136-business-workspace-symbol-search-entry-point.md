# TASK-20260911-136: Business Workspace Symbol & Company Search Entry Point

- **Status**: completed
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
- [x] `/business` has a prominent ticker/company search input component (`SymbolSuggestInput`).
- [x] User can type `ACB` and navigate to `/business/ACB`.
- [x] User can type `FPT` and navigate to `/business/FPT`.
- [x] Non-held candidate companies can be discovered and researched.
- [x] Search query executes against the Finance DB symbol catalog (`/api/portfolio/search/symbols` & `/api/portfolio/securities/lookup`).
- [x] No hardcoded ticker lists in the frontend.
- [x] No external crawl/HTTP fetch triggered by searching (search is discovery-only).
- [x] Keyboard navigation (Arrow Up/Down, Enter, Esc) works seamlessly in search results dropdown.
- [x] Pressing Enter on search input opens exact or currently highlighted symbol.
- [x] Proper UI states implemented: Loading state, Empty query state, No-results state.
- [x] Fully responsive layout for both Desktop and Mobile devices.
- [x] Terminal header exposes quick company search shortcut navigating to `/business/:symbol`.
- [x] Candidate companies and portfolio holdings use the identical Business research pipeline.

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
- [x] Backend API: Added `@app.get("/api/portfolio/search/symbols")` alias routing to `search_securities_lookup` in `app/main.py`.
- [x] Frontend Component: Integrated `SymbolSuggestInput` with keyboard navigation, debounce, loading, empty, and no-results states.
- [x] Frontend Page: Integrated search component prominently into `/business` main page (`BusinessPage.jsx`) for landing and detail views.
- [x] Frontend Header: Added quick search bar to Desktop header and compact search icon button on Mobile in `AppNav.jsx`.
- [x] Routing: Ensured selecting a search result navigates cleanly to `/business/:symbol`.
- [x] Tests: Added `python/portfolio/tests/test_business_search_entry_point.py` verifying search API contract, non-held candidate research, and valuation equality.

---

## Related Notes
- [docs/tasks/TASK-20260911-135-runtime-valuation-evidence-propagation.md](file:///c:/workspace/shannon_allocation/docs/tasks/TASK-20260911-135-runtime-valuation-evidence-propagation.md)

---

## Validation Evidence
- **Pytest Suite**: `python/portfolio/tests/test_business_search_entry_point.py` (3/3 PASSED).
- **Search API**: Tested `search_securities_lookup("FPT")`, `search_securities_lookup("ACB")`, `search_securities_lookup("Ngân hàng")` returning canonical securities from `qport_finance.securities`.
- **Candidate Research**: Non-held candidate stocks (`ACB`, `DGC`, `FPT`, `VIX`) produce identical fundamental valuations whether requested directly or via portfolio service.

---

## Decisions
- **Unified Symbol Search Component**: Leveraged `SymbolSuggestInput.jsx` which handles debouncing, keyboard navigation, clear button, and candidate vs holding tags (`"Đang nắm giữ"`).
- **Header Integration**: Added `<SymbolSuggestInput>` to `AppNav.jsx` desktop header and mobile search button trigger navigating to `/business`.

---

## Result
Task 136 completed and verified. `/business` now serves as the primary research entry point with a user-facing Finance DB catalog search supporting both portfolio holdings and non-held candidate stocks.
