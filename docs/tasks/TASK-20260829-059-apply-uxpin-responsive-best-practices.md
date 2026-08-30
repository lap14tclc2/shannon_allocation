# TASK-20260829-059: Apply UXPin Responsive Design Best Practices Across All Pages

- **ID**: `TASK-20260829-059`
- **Title**: Apply UXPin Responsive Design Best Practices Across All Pages
- **Status**: `in-progress`
- **Priority**: `high`
- **Date**: `2026-08-29`

## Requirement

Apply the responsive-design best practices from `https://www.uxpin.com/studio/blog/best-practices-examples-of-excellent-responsive-design/` across the whole QPort frontend. The article (2026 edition) names as the current standard:

1. **Fluid grids** — relative units, `minmax(0, 1fr)`, `auto-fit`.
2. **Container queries (`@container`)** — component adapts to its parent width, not the viewport. Fully supported in all modern browsers; safe in production.
3. **Fluid typography with `clamp()`** — `font-size: clamp(min, preferred, max)` so type scales smoothly instead of jumping at breakpoints.
4. **Flexible media** — `max-width: 100%; height: auto` plus `aspect-ratio` / `width`+`height` guards to prevent CLS.
5. **Breakpoints that follow content** — 360–480 / 481–767 / 768–1023 / 1024–1279 / 1280+.
6. **Mobile-first** — base styles target small viewports, `min-width` adds complexity.
7. **Touch targets ≥ 44×44px** with padding-extended hit area.
8. **Progressive disclosure** — accordions/drawers/sheets instead of hiding content.
9. **Data-table → card stacks on narrow widths** — each row becomes a labelled card (SaaS-dashboard pattern).

## Context

`python/portfolio/tests/` grep shows the current frontend already has a strong mobile-first base:
- `responsive.css` is the mobile-first contract (320 base → 480/720/1024/1280 `min-width`).
- `mobile-iphone.css` is the <720px iPhone shell (bottom tabs, safe-areas, 44/48px touch).
- `ui-polish.css` + `TransactionsPage.jsx` already implement a dual-render row→card table.
- `dividend-history.css` already transforms the dividend event table into cards at ≤720px.

**Gaps vs. the article:**
- Zero `@container` / `container-type` usage anywhere (article's headline 2026 technique).
- `clamp()` fluid type is used for hero h1/metric values only; section headings, card titles and body text still use fixed sizes.
- No global `img/video { max-width:100%; height:auto }` safety net and no `aspect-ratio` CLS guards on chart containers.
- No unified touch-target safety net for small inline controls that are not `.btn-*`.

## Acceptance Criteria

- [ ] A new layered `frontend/src/responsive-2026.css` is loaded after the theme CSS in both `entry-client.jsx` and `entry-vercel.jsx` so it can safely layer above existing rules.
- [ ] It uses container queries (`@container` / `container-type`) for at least the card-component surfaces (fund-manager lenses, guide steps, valuation pillars, assessment card, metric cards) so they reflow by available width.
- [ ] Fluid typography: `clamp()` added for section/card headings and body copy across the shared surfaces without breaking existing contract tests.
- [ ] Flexible media + CLS: global `img, video { max-width:100%; height:auto }` and `aspect-ratio` on `.chart`/`.equity-chart` containers.
- [ ] Touch targets: a shared `.tap-target`-style safety net guaranteeing ≥44px for small controls on mobile.
- [ ] Wide data tables keep their `.table-scroll` horizontal pattern (existing contract), while narrow-value tables may use card-stack transforms — without breaking `test_frontend_responsive.py`, `test_mobile_iphone_shell_contract.py`, `test_mobile_app_shell_contract.py`, `test_mobile_scroll_contract.py`.
- [ ] `npm run build` passes; all responsive/frontend contract pytest suites pass.

## Constraints and Invariants

- Mobile < 720px must keep the iPhone application shell (`mobile-iphone.css`); desktop ≥ 720px keeps the terminal/quant-workstation identity.
- Do NOT restyle desktop as a side effect of the mobile redesign.
- Do not break existing contract tests that assert `responsive.css` is mobile-first with `min-width` queries (they forbid `@media (max-width:` in that file).
- New layer must be purely additive (layered last) — do not rewrite existing stylesheets' core rules.

## Implementation Tasks

- [ ] 1. Create `frontend/src/responsive-2026.css` with container queries, fluid type, media/CLS guards, touch-target net.
- [ ] 2. Import it after `cyber-fantasy-theme.css` in both entry files.
- [ ] 3. Add `container-type` to the component-card wrappers the CSS queries target.
- [ ] 4. Add contract tests in `python/portfolio/tests/` (new file).
- [ ] 5. Run responsive/frontend contract pytest suites and `npm run build`.

## Related Notes

- `frontend/src/responsive.css`
- `frontend/src/mobile-iphone.css`
- `frontend/src/ui-polish.css`
- `python/portfolio/tests/test_frontend_responsive.py`
- `python/portfolio/tests/test_mobile_iphone_shell_contract.py`

## Validation Evidence

_To be filled after running tests._

## Decisions

_To be recorded during implementation._

## Result

_To be filled on completion._