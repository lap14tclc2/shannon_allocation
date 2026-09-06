---
id: TASK-20260906-101
title: Add Executable Share-Quantity Plans and Explainable Candidate Selection to Allocation
status: completed
priority: high
created: 2026-09-06
updated: 2026-09-06
tags: [allocation, execution-planner, candidates, lot-size, rationale, ui, risk]
related: [TASK-20260906-095-buffett-thorp-allocation.md, TASK-20260906-096-refactor-allocation-remove-composite-weights.md, TASK-20260906-100-fix-allocation-reduce-to-zero-semantics.md, BUY_AND_HOLD_SYSTEM_SPEC.md, AGENTS.md]
---

## Requirement

Implement two advisory enhancements for the Allocation V1 module:

1. **PART A — EXECUTABLE SHARE-QUANTITY PLAN**:
   - Compute lot-rounded share quantities, reference prices, gross trade values, estimated commission fees, sell taxes, slippage estimates, post-trade cash, post-trade weights, and risk impact.
   - Enforce lot size rules (default 100 shares), cash constraints, hard allocation caps, and post-trade risk re-simulation.
   - Stale or missing prices mark plans as non-executable; never fabricate prices.
   - Advisory only — no ledger mutation, no auto-execution, no Kelly, no expected alpha.

2. **PART B — EXPLAINABLE NEW-CANDIDATE SELECTION**:
   - Make new candidate suggestion criteria explicit, deterministic, and explainable.
   - Gates: Security universe (common stock only, exclude warrants/derivatives), Liquidity (20D avg traded value >= min_liquidity), Buffett Quality eligibility, Valuation safety (`actual_mos - required_mos >= min_valuation_safety`), and Portfolio-fit simulation.
   - Expose structured `selection_evidence` with `why_selected` human explanations for each candidate.
   - Shortlist 3–5 candidates max using deterministic lexicographic ordering (no unvalidated composite decision score).
   - If no candidates clear all gates, return `KEEP_CASH` / `NO_COMPELLING_NEW_OPPORTUNITY`; do not force 5 candidates.

## Context

Current Allocation recommendations output theoretical percentage targets (e.g. `ACB BUY_MORE 10%`), which are not actionable enough for a retail investor executing standard 100-share board lots on Vietnamese exchanges. Additionally, users need clear, transparent rationale explaining why candidates appear in the shortlist for their specific portfolio.

## Acceptance Criteria

- [x] `AllocationExecutionPlan` model created with exact quantity, price, lot, cost, cash, post-trade weight, target error, and risk fields.
- [x] Execution planner module (`execution_planner.py`) computes lot-rounded quantities for `BUY_MORE`, `REDUCE`, `SELL`.
- [x] BUY quantity math accounts for fee, tax, slippage, available cash, lot size, and max allocation cap.
- [x] REDUCE quantity math finds closest valid in-band lot size without causing accidental full exit.
- [x] SELL quantity equals current owned quantity.
- [x] Missing/stale price blocks executable plan (`is_executable = False`, `blocking_reasons`).
- [x] Post-rounding risk re-simulation verifies risk bounds.
- [x] Candidate selection pipeline enforces security universe, 20D liquidity, quality, valuation safety, and portfolio-fit gates.
- [x] `selection_evidence` attached to each candidate with `why_selected` Vietnamese rationale.
- [x] Warrants and invalid tickers excluded.
- [x] Empty shortlist when no candidates pass gates -> `KEEP_CASH`.
- [x] `/allocation` UI renders actionable share quantities, fees, post-trade cash/weights, and candidate selection rationale.
- [x] All 32+ item test matrix verified in pytest.
- [x] Frontend build verified (`npm run build`).

## Constraints and Invariants

1. `BUY_AND_HOLD_INFORMATION_SYSTEM` philosophy preserved — advisory only, no auto-execution, no ledger mutation.
2. No Kelly sizing, no Expected Alpha, no ML models.
3. Single sources of truth preserved: canonical Value Engine for valuation, `portfolio_risk()` for risk.

## Implementation Tasks

- [x] Task 1: Create `AllocationExecutionPlan` and `SelectionEvidence` models in `python/portfolio/allocation/models.py`.
- [x] Task 2: Implement `python/portfolio/allocation/execution_planner.py` with lot rounding, fee/tax/slippage, cash limits, and risk re-simulation.
- [x] Task 3: Update `python/portfolio/allocation/candidate_service.py` with security universe gate, 20D liquidity gate, valuation safety gate, portfolio fit gate, lexicographic ordering, and `selection_evidence` rationale.
- [x] Task 4: Integrate execution planner and candidate evidence into `python/portfolio/allocation/service.py`.
- [x] Task 5: Update `frontend/src/pages/AllocationPage.jsx` to display executable share quantities, trade values, fees, post-trade cash/weights, and candidate selection rationale.
- [x] Task 6: Add comprehensive unit, integration, and architecture tests in `python/portfolio/tests/`.
- [x] Task 7: Run pytest suite and frontend production build (`npm run build`).

## Validation Evidence

- Pytest execution planner suite:
  `.venv\Scripts\python.exe -m pytest -o pythonpath=python python/portfolio/tests/test_allocation_execution_planner.py` -> 7 passed in 0.60s.
- Entire Allocation test suite:
  `.venv\Scripts\python.exe -m pytest -o pythonpath=python python/portfolio/tests/test_allocation_*.py` -> 108 passed in 1.92s.
- Frontend production build:
  `npm run build` in `frontend/` -> Vite built `dist/` successfully (0 errors, 110 modules transformed).

## Decisions

- Lot size default is 100 shares (HOSE/HNX standard board lot).
- Standard commission rate default is 0.1%, sell tax 0.1%, slippage 0.05%.
- Candidate ordering uses deterministic lexicographic priority (investable -> portfolio fit -> valuation safety -> quality score -> liquidity).

## Result

Completed advisory share-quantity execution planner and explainable candidate selection. All test suites and frontend build passed cleanly.
