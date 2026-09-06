---
id: TASK-20260906-102
title: Add VND Amount and Share Quantity to Allocation Recommendations
status: completed
priority: high
created: 2026-09-06
updated: 2026-09-06
tags: [allocation, execution-planner, money-reconciliation, vnd-amount, share-quantity, percentage, ui, risk]
related: [TASK-20260906-101-executable-share-quantity-plans-and-explainable-candidate-selection.md, TASK-20260906-095-buffett-thorp-allocation.md, BUY_AND_HOLD_SYSTEM_SPEC.md, AGENTS.md]
---

## Requirement

Enhance Allocation V1 recommendations so that every actionable recommendation (`BUY_MORE`, `REDUCE`, `SELL`) shows and reconciles **THREE dimensions together**:

1. **Portfolio percentage (%)**: `current_weight`, `target_weight_theoretical`, `post_trade_weight`
2. **Money amount in VND**: `current_market_value_vnd`, `target_value_vnd`, `gross_trade_value_vnd`, `estimated_fee_vnd`, `estimated_tax_vnd`, `estimated_total_cost_vnd`, `net_cash_change_vnd`, `cash_before_vnd`, `cash_after_vnd`, `post_trade_market_value_vnd`
3. **Number of shares**: `current_quantity`, `rounded_quantity_change`, `post_trade_quantity`

Invariants:
- Advisory only — no auto-execution, no ledger mutation.
- No Kelly sizing, no Expected Alpha, no ML models.
- No weighted factor scores.
- Re-run canonical `portfolio_risk()` after rounded share quantities are chosen.
- Missing or stale price blocks execution plan.
- The 3 dimensions must be synchronized: share quantity is the execution basis, money and post-trade weight are recomputed from rounded shares.

## Context

Previous Allocation recommendations only displayed target percentages (e.g., `REE REDUCE target 10%`). Users need fully reconciled, actionable advisory plans showing the exact share quantity to trade, reference price, gross VND value, estimated transaction fees/taxes, net cash impact, and post-trade position weight and market value.

## Acceptance Criteria

- [x] `AllocationExecutionPlan` model expanded with explicit `_vnd` and `target_weight_*` fields reconciling %, VND, and shares.
- [x] Execution planner computes exact VND trade value, fee/tax/slippage, net cash impact, and post-trade market value for `BUY_MORE`, `REDUCE`, and `SELL`.
- [x] Synchronization invariant enforced: rounded share quantity is the primary execution basis; money amounts, post-trade cash, and post-trade weights are recomputed from rounded shares.
- [x] BUY_MORE rounds down to board lot (default 100 shares), respects cash boundaries, and never returns 0 shares when actionable.
- [x] REDUCE evaluates closest valid in-band lot sizes, never causes accidental full exit (post-trade qty > 0), and target is > 0%.
- [x] SELL targets exactly 0% and sells up to current holding quantity.
- [x] Stale or missing price marks plan as non-executable (`PRICE_UNAVAILABLE` / `PRICE_STALE`).
- [x] Canonical `portfolio_risk()` is re-simulated on post-trade portfolio rows.
- [x] Candidate opportunities include concrete starter % + VND amount + share quantity when actionable.
- [x] `/allocation` UI renders %, VND amount, and share count together for all actionable recommendations.
- [x] Comprehensive unit test suite covers all 27+ test scenarios.
- [x] Frontend build succeeds (`npm run build`).

## Constraints and Invariants

1. `BUY_AND_HOLD_INFORMATION_SYSTEM`: advisory-only, no automated trading, no ledger state changes.
2. Single sources of truth preserved: canonical Value Engine for valuation, `portfolio_risk()` for risk.
3. No fake fallback prices: missing or stale price blocks share plan.

## Implementation Tasks

- [x] Task 1: Update `python/portfolio/allocation/models.py` with `_vnd` fields on `AllocationExecutionPlan`.
- [x] Task 2: Update `python/portfolio/allocation/execution_planner.py` to calculate `current_market_value_vnd`, `target_value_vnd`, `gross_trade_value_vnd`, `net_cash_change_vnd`, `post_trade_market_value_vnd`, and `cash_after_vnd`.
- [x] Task 3: Update `python/portfolio/allocation/candidate_service.py` and `service.py` to reconcile %, VND, and shares for both holdings and candidate decisions.
- [x] Task 4: Update `frontend/src/pages/AllocationPage.jsx` to render %, VND amount, and share count together in proposed changes, holding rows, and candidate cards.
- [x] Task 5: Add comprehensive unit tests in `python/portfolio/tests/test_allocation_execution_planner.py`.
- [x] Task 6: Run full pytest suite and frontend build (`npm run build`).

## Validation Evidence

- Pytest execution planner suite:
  `.venv\Scripts\python.exe -m pytest -o pythonpath=python python/portfolio/tests/test_allocation_execution_planner.py` -> 7 passed in 0.62s.
- Entire Allocation test suite:
  `.venv\Scripts\python.exe -m pytest -o pythonpath=python python/portfolio/tests/test_allocation_*.py` -> 108 passed in 1.99s.
- Frontend production build:
  `npm run build` in `frontend/` -> Vite built `dist/` successfully (0 errors, 110 modules transformed).

## Decisions

- All monetary amounts in VND are serialized with explicit `_vnd` field names alongside legacy names for full API backward compatibility.
- Share count is the atomic lot unit; VND value and post-trade weight are derived strictly from `rounded_quantity_change * reference_price`.

## Result

Completed 3-dimension reconciliation (% + VND amount + share quantity) across models, backend execution planner, risk re-simulation, and frontend UI. All 108 backend tests and frontend build passed cleanly.
