# TASK-20260830-079: Fix Mobile Valuation Overlay Layout (Laws of UX)

**Status**: completed
**Priority**: high
**Date**: 2026-08-30

## Requirement
The valuation detail overlay (`ValuationDetailOverlay.jsx`) opened from the Screener page is broken on mobile (< 720px):
1. **Layer overlap**: Inconsistent `z-index` between desktop (`99999`) and mobile (`1000`) override risks overlay sitting under app chrome; layering must be predictable and always on top.
2. **Messy header**: `.v-header-title-row` uses `flex-wrap: nowrap` + `overflow-x: auto`, so ticker + tags get clipped / horizontally scrolled; status pill + close button crowd the same row (violates Hick's Law / Law of Proximity).
3. **Broken hero/card grid**: `.v-hero-value` and `.v-metric-value` use `white-space: nowrap` with no `min-width: 0` on grid/flex children, so long VND values overflow and cards break.
4. **Text clipping/overflow**: header sub-row `nowrap`, scenario base number `nowrap` cause clipped text on narrow screens; no `100vh` fallback for `100dvh` on older mobile browsers.

Fix all four on mobile while keeping the desktop (>= 720px) centered modal unchanged.

## Context
- `frontend/src/components/ValuationDetailOverlay.jsx` — all overlay styles are in an inline `<style>` tag; mobile block is inside `@media (max-width: 719px)`.
- `frontend/src/screener-page.css` — screener page styles (unchanged in this task).
- `frontend/src/mobile-iphone.css` — mobile app shell: tab bar `z-index: 400`, nav backdrop `500`, appearance overlay `700`; the overlay must stay above all of them.
- Relevant Laws of UX: Jakob's Law (standard full-screen sheet), Fitts's Law (44px close target), Hick's Law (decluttered header), Law of Proximity (verdict grouped with meta), Postel's Law (graceful wrap instead of clipping).

## Acceptance Criteria
- [x] Overlay backdrop/modal use a single consistent high `z-index` on both desktop and mobile so nothing in the app can cover it.
- [x] Mobile header is decluttered: ticker + tags wrap gracefully (no `overflow-x: auto`, no clipping), verdict pill gets its own row, and the close button is a pinned 44px touch target at top-right (Fitts's Law).
- [x] Hero + multiples cards never overflow: children get `min-width: 0`, and long VND values wrap (`overflow-wrap: anywhere`) on mobile instead of clipping.
- [x] `100vh` fallback is present before `100dvh` for older mobile browsers.
- [x] Desktop (>= 720px) overlay rendering is unchanged.
- [x] No existing tests broken; frontend contract tests pass.

## Constraints and Invariants
- `BUY_AND_HOLD_INFORMATION_SYSTEM` invariant (no buy/sell logic touched).
- Ledger invariant (no transaction logic touched).
- Mobile / Desktop UX split preserved at 720px breakpoint.
- Theme tokens synchronized (use `var(--...)` tokens only).

## Implementation Tasks
- [x] Create task note + register in `docs/tasks/README.md`.
- [x] In `ValuationDetailOverlay.jsx` mobile block: unify backdrop `z-index` to `99999` (drop the `1000` override).
- [x] Add `100vh` fallback before `100dvh` for modal height.
- [x] Restructure mobile header CSS: wrap-allowed title row, pill row (`order` + full width), absolutely-pinned 44px close button.
- [x] Add `min-width: 0` to hero/metric/meta/pillar/bridge children; allow hero value / metric value / meta value / scenario numbers to wrap instead of `nowrap`.
- [x] Run frontend contract tests and verify no regressions.

## Related Notes
- [TASK-20260830-077](file:///f:/workspace/shannon_allocation/docs/tasks/TASK-20260830-077-valuation-overlay-mobile-full-height-polish.md) — introduced the full-height mobile overlay (spacing/typo polish, still broken layout).
- [TASK-20260830-065](file:///f:/workspace/shannon_allocation/docs/tasks/TASK-20260830-065-valuation-detail-overlay-modal-ux.md) — overlay modal UX origin.
- [TASK-20260830-067](file:///f:/workspace/shannon_allocation/docs/tasks/TASK-20260830-067-valuation-overlay-modal-design-ux.md) — overlay modal design & responsiveness.

## Validation Evidence
- Frontend production build: `npx vite build` (in `frontend/`) → `✓ 105 modules transformed`, built successfully.
- Frontend contract tests (`pytest python/portfolio/tests/test_mobile_app_shell_contract.py test_mobile_iphone_shell_contract.py test_appearance_controls_contract.py`): 16 passed.
- 2 pre-existing failures confirmed unrelated to this change (verified by `git stash` on clean HEAD):
  - `test_mobile_app_shell_contract.py::test_mobile_navigation_is_portaled_outside_top_nav_containing_block` — asserts `className="app-nav-links desktop-nav-links"` no longer present in `AppNav.jsx` (from earlier nav refactor).
  - `test_mobile_iphone_shell_contract.py::test_mobile_navigation_is_portaled_to_real_viewport` — asserts `grid-template-columns: repeat(4` but `mobile-iphone.css` now uses `repeat(6` (6-tab bar from `db40d19`).
- Backend tests requiring the DB driver could not collect locally (`ModuleNotFoundError: psycopg`) — environment limitation, not code-related; this change is frontend-only.

## Decisions
- Keep all fixes inside the mobile `@media (max-width: 719px)` block in the inline `<style>` tag (no JSX/DOM restructure) so desktop stays untouched and blast radius is minimal.
- Use CSS-only header re-layout (flex `order`, absolute close button) instead of moving the verdict pill in JSX.

## Result
Fixed all 4 reported mobile (< 720px) overlay breakages in `ValuationDetailOverlay.jsx`:
1. **Chồng layer** — backdrop `z-index` unified to `99999` (removed the mobile `1000` override), so the overlay always layers above tab bar (400), nav (380/500) and appearance (700); added `overscroll-behavior: contain`.
2. **Header lộn xộn** — title row now wraps instead of horizontal-scrolling (`flex-wrap: wrap`), verdict pill moved to its own full-width row, close button pinned top-right as a 44px Fitts-friendly target.
3. **Hero/card vỡ grid** — grid/flex children get `min-width: 0`; hero/metric/meta/scenario values use `clamp()` + `white-space: normal` + `overflow-wrap: anywhere` so long VND numbers wrap instead of breaking cards.
4. **Text cắt/tràn** — added `100vh` fallback before `100dvh`, removed `nowrap` from header sub-row / scenario numbers / node prices.

Desktop (>= 720px) modal untouched. No JSX/DOM changes, CSS-only within the mobile media block.