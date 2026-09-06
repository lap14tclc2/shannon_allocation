# TASK-20260906-103: Frontend CSS Typography, Aesthetic Polish, and Responsive Overhaul

- **Status**: completed
- **Priority**: high
- **Date**: 2026-09-06
- **Author**: Antigravity AI

---

## ## Requirement

Enhance and harden the frontend CSS across QPort to make it visually aesthetic, eliminate font breakage / diacritic clipping for Vietnamese text, and ensure robust mobile-first responsive layout behavior across all screen sizes (320px to 1440px+).

---

## ## Context

Users reported UI text issues including Vietnamese diacritic clipping, font fallback mismatches, and execution plan details jamming together on single lines without inline spacing. This task unifies core typography rules, design tokens, card glassmorphism aesthetics, execution plan item flex grids, table touch scrolling, and responsive layout breakpoints across `styles.css`, `design-system-v1.css`, `ui-polish.css`, `allocation-page.css`, `responsive.css`, and related component stylesheets.

---

## ## Acceptance Criteria

- [x] **Vietnamese Typography Standard**: Define robust system font fallbacks (`system-ui`, `-apple-system`, `BlinkMacSystemFont`, `"Segoe UI"`, `Roboto`, `"Helvetica Neue"`, `Arial`, `"Noto Sans"`, `sans-serif`) across root design system tokens to prevent font switching or broken glyphs on Windows, Mac, Android, and iOS.
- [x] **Prevent Diacritic Clipping**: Set line-height minimums ($\ge 1.25$) and vertical padding on headings, cards, badges, and metric labels so Vietnamese accents (`ấ, ầ, ẩ, ẫ, ậ, ế, ề, ể, ễ, ệ, ố, ồ, ổ, ỗ, ộ, ứ, ừ, sử, ữ, ự, đ`) are never clipped.
- [x] **Text Overflow Defense**: Apply `overflow-wrap: break-word; word-break: break-word;` and `text-overflow: ellipsis` on tight cards, table cells, metric labels, and decision rationales.
- [x] **Execution Plan Flex Grid Formatting**: Overhauled `.allocation-change-item`, `.allocation-change-main`, `.allocation-plan-details`, and `.allocation-qty-badge` so execution parameters (reference price, gross trade value, estimated fee, post-trade cash, post-trade shares/weight) format cleanly with clear inline flex gaps instead of clumping into single inline strings.
- [x] **Aesthetic Polish**: Modernize dark mode theme tokens with subtle glassmorphism panel background gradients, crisp border contrasts, smooth micro-animations on interactive elements, and clear advisory action badges (`BUY_MORE`, `REDUCE`, `SELL`, `HOLD`, `KEEP_CASH`).
- [x] **Responsive Mobile Overhaul**: Ensure pages render cleanly without horizontal body overflow down to 320px screen width. Mobile views (< 720px) stack grid cards vertically, provide touch scroll containers (`.table-scroll`) for wide tables, and enforce comfortable touch targets ($\ge 40\text{px}$).
- [x] **Build & Visual Verification**: Built production bundle cleanly with `npm run build` (1.18s) and verified 54/54 allocation backend unit tests pass.

---

## ## Constraints and Invariants

- Preserve existing color theme switching functionality (`data-theme="dark"` / `data-theme="light"` and custom palettes).
- Maintain 3-dimension recommendation layout (%, VND amount, share count) in Allocation UI without breaking layout structure.
- Touch only CSS and layout stylesheets unless JSX markup requires wrapper classes for table scrolling or text wrapping.

---

## ## Implementation Tasks

- [x] Audit and refine root font-family tokens in `design-system-v1.css`, `styles.css`, and `ui-polish.css`.
- [x] Enhance line-heights and text wrapping in `ui-polish.css`, `allocation-page.css`, `responsive.css`, and `styles.css`.
- [x] Upgrade card glassmorphism, hover transitions, and action badge colors across pages.
- [x] Format execution plan detail flex grids in `allocation-page.css` and fix `RiskRow` extra column bug in `AllocationPage.jsx`.
- [x] Harden touch scrolling and mobile responsive breakpoints down to 320px.
- [x] Execute `npm run build` and `pytest` to verify frontend build and backend tests cleanly.

---

## ## Related Notes

- [AGENTS.md](file:///c:/workspace/shannon_allocation/AGENTS.md)
- [TASK-20260906-101](file:///c:/workspace/shannon_allocation/docs/tasks/TASK-20260906-101-executable-share-quantity-plans-and-explainable-candidate-selection.md)
- [TASK-20260906-102](file:///c:/workspace/shannon_allocation/docs/tasks/TASK-20260906-102-add-vnd-amount-and-share-quantity-to-allocation.md)

---

## ## Validation Evidence

- **Frontend Production Build**: Executed `npm run build` in `frontend/` — output:
  `✓ built in 1.18s` with `dist/assets/index-CGKeaDbI.css (273.47 kB)`.
- **Backend Unit Tests**: Executed `$env:PYTHONPATH="python"; .venv\Scripts\pytest.exe python/portfolio/tests/test_allocation_*.py` — output:
  `54 passed in 0.63s`.

---

## ## Decisions

- Use native system font stack with `"Noto Sans"` and `"Segoe UI"` fallbacks to ensure native Vietnamese diacritic support without relying on external web fonts that may fail to load offline or over slow connections.
- Format `.allocation-plan-details` with a flex-wrap container and subtle panel background to keep execution values distinctly separated and readable on both desktop and mobile.

---

## ## Result

Successfully overhauled QPort frontend CSS typography, diacritic line-height protection, glassmorphism aesthetics, execution plan item detail layout, and mobile-first responsive layout contracts.
