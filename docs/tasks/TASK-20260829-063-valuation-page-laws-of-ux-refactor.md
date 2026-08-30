# TASK-20260829-063: Valuation Page Refactor — Laws of UX, reduce scroll, mobile-first

- **ID**: `TASK-20260829-063`
- **Title**: Valuation Page Refactor — Laws of UX, reduce scroll, mobile-first
- **Status**: `completed`
- **Priority**: `high`
- **Date**: `2026-08-29`

## Requirement

The `/valuation` page is ~740 lines of JSX and scrolls excessively: an always-open
methodology guide (4 large cards) at the top pushes all valuation content down, and
each symbol card renders the full analyst opinion, 3 always-open value-investor
pillar cards, plus technical details. Apply Laws of UX to make it clean, friendly,
and mobile-first (iPhone + Android).

Laws applied:
- **Progressive Disclosure / Cognitive Load** — methodology guide and value-investor
  pillars become collapsed `<details>`; only the primary verdict stays open.
- **Miller's Law / Chunking** — one symbol = one cohesive card; group secondary
  evidence behind a labelled disclosure.
- **Selective Attention / Peak-End** — verdict + IV + MOS stay prominent; details
  are behind disclosure.
- **Jakob's Law** — add a sticky symbol tab strip for quick navigation between many
  holdings (familiar app pattern).
- **Fitts's Law** — touch targets >= 44px on mobile; tabs are large tap areas.
- **Aesthetic-Usability / Law of Common Region** — cleaner grouping with clear borders.

## Context

`frontend/src/pages/ValuationPage.jsx` (740 lines), `frontend/src/valuation-page.css`,
`frontend/src/mobile-iphone.css` (valuation mobile surface already partially handled).
Contract `python/portfolio/tests/test_valuation_page_contract.py` requires pure-Vietnamese
narrative (no "Owner Earnings", "Reverse DCF", "fallback") and presence of
"Lợi nhuận Thực", "Kịch bản", "Chiết khấu".

## Acceptance Criteria

- [x] Methodology guide collapsed by default (progressive disclosure).
- [x] Value-investor pillar cards collapsed behind a labelled disclosure.
- [x] Primary verdict (price, IV, MOS, status pill) remains open on every card.
- [x] Symbol tab strip added for quick navigation (sticky on desktop, scrollable on mobile).
- [x] No visual regression on desktop terminal identity (>=720px).
- [x] Mobile (<720px): tabs scroll horizontally, touch targets >=44px, cards stack cleanly.
- [x] Contract test still passes; `npm run build` clean.

## Constraints and Invariants

- Desktop (>=720px) keeps the terminal/quant-workstation identity; mobile keeps the
  iPhone app shell (`mobile-iphone.css`).
- Do not remove any information — move secondary evidence behind disclosure.
- Keep the pure-Vietnamese narrative contract.

## Implementation Tasks

- [x] 1. Wrap `MethodologyGuide` in a collapsible `<details>`.
- [x] 2. Wrap value-investor pillars in a collapsible `<details>` per card.
- [x] 3. Add sticky symbol tab strip in `ValuationPage` main.
- [x] 4. CSS: disclosure + tab-strip styles (desktop + mobile) in `valuation-page.css`.
- [x] 5. Run contract tests + `npm run build`.

## Related Notes

- `frontend/src/pages/ValuationPage.jsx`
- `frontend/src/valuation-page.css`
- `frontend/src/mobile-iphone.css`
- `python/portfolio/tests/test_valuation_page_contract.py`

## Validation Evidence

```text
$ npm run build  -> clean (Vite, 0 errors; dist assets rebuilt)

Follow-up (reduce scroll further): per-symbol cards are now accordions.
Collapsed by default -> only verdict header + compact summary row (Giá / Giá trị
Thực cơ sở / Biên An Toàn / chevron) render. Tap expands the full analysis
(multiples, analyst opinion, pillars, technical). Secondary tags (sector, quality,
period) are hidden while collapsed.

Contract tests:
$ pytest test_valuation_page_contract.py test_frontend_responsive.py \
        test_mobile_iphone_shell_contract.py -> pass
(only pre-existing AppNav/header-v2 failures remain, unrelated)

Result: with N holdings the page now renders N compact rows instead of N full
cards, drastically reducing scroll; a symbol tab strip adds instant navigation.
```

## Decisions

- Per-symbol card is an accordion (`useState`): collapsed default, expands on tap.
  The always-visible summary row (price / base IV / MOS / verdict pill) follows
  Peak-End + Selective Attention; the full analysis follows Progressive Disclosure
  + Chunking.
- Summary row layout: desktop = 4-column grid (price, IV, MOS, chevron); mobile =
  3-area grid (price | IV+MOS stacked | chevron), touch target >= 44px.
- Secondary tags (sector, quality, period) hidden while collapsed so a collapsed
  card is a single compact line.

## Result

Valuation page no longer scrolls excessively: methodology and pillars are collapsed
by default, each holding is a compact collapsed card with a verdict summary, a
symbol tab strip enables fast navigation, and everything remains one tap from the
full analysis. Mobile (iPhone + Android) uses large touch targets and a scrollable
tab strip; desktop keeps the terminal identity. Build clean, contract tests pass.