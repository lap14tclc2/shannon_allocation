---
id: TASK-20260828-030
title: Support stock dividend ratio display and observation details in Dividend UI
status: completed
priority: medium
created: 2026-08-28
updated: 2026-08-28
tags: [dividend, frontend, canonical-events, stock-dividend, ui]
related: [TASK-20260827-029]
---

## Requirement

1. Display stock dividend percentage on UI when `stock_ratio` (or `stock_ratio_percent`) is present (e.g., `stock_ratio: 0.15` -> display `15%`).
2. Enrich `get_canonical_dividend_events` to include `stock_ratio_percent`, observation dates (`ex_date`, `record_date`, `payment_date`, `announcement_date`, `provider`) from `dividend_observations`.
3. In `DividendTree.jsx`, handle both `stock_ratio_percent` and direct `stock_ratio` fallback (`stock_ratio * 100`).
4. Keep event details clean and render only available dates or meaningful metadata instead of empty dashes.

## Context

When viewing stock dividends on the UI (e.g. ACB 2025-05-23 stock dividend 15%), the UI displayed `-` under "Tỷ lệ" because `get_canonical_dividend_events` returned `stock_ratio` without `stock_ratio_percent`, and `DividendTree.jsx` only looked for `event.stock_ratio_percent`. Furthermore, event details lacked joined observation date fields.

## Acceptance Criteria

- [x] `get_canonical_dividend_events` joins with `dividend_observations` (via `chosen_observation_id`) to supply `ex_date`, `record_date`, `payment_date`, `announcement_date`, `provider`, and `stock_ratio_percent`.
- [x] `DividendTree.jsx` accurately formats stock dividends using `stock_ratio_percent` or `stock_ratio * 100`.
- [x] `DividendTree.jsx` detail section renders cleanly without displaying meaningless empty blocks when details are absent.
- [x] Regression tests pass.

## Constraints and Invariants

- Preserve ledger invariants.
- No synthetic dividend events or fake numbers.

## Implementation Tasks

- [x] Update `get_canonical_dividend_events` in `python/portfolio/finance_catalog.py`.
- [x] Update `DividendTree.jsx` to format `stock_ratio` / `stock_ratio_percent` and render details cleanly.
- [x] Test frontend/backend integration.

## Decisions

- Support `stock_ratio * 100` fallback in both backend `get_canonical_dividend_events` and frontend `DividendTree.jsx` for defense in depth.

## Validation Evidence

- Tested `get_canonical_dividend_events('ACB')`:
  - `2025-05-23 | STOCK_DIVIDEND | Ratio: 0.15 | Ratio %: 15.0 | GDKHQ: 2025-05-23`
  - `2023-06-01 | STOCK_DIVIDEND | Ratio: 0.15 | Ratio %: 15.0 | GDKHQ: 2023-06-01`
  - `2022-06-02 | STOCK_DIVIDEND | Ratio: 0.25 | Ratio %: 25.0 | GDKHQ: 2022-06-02`
- `DividendTree.jsx` renders `15%` instead of `-` and cleans up empty detail rows.

## Result

Stock dividend ratio is properly formatted and rendered in the Dividend UI across all stocks, with joined observation metadata.

