# TASK-20260907-113: Make Allocation Buffett-First and Demote Market Risk to Sizing Overlay

---
id: TASK-20260907-113
title: Make Allocation Buffett-First and Demote Market Risk to Sizing Overlay
status: completed
priority: high
date: 2026-09-07
---

## Requirement

Refactor QPort Allocation so it follows a true Buffett/Munger-first hierarchy:
1. Thesis status and business quality decide WHAT to own.
2. Permanent capital loss risk decides whether ownership remains justified.
3. Valuation decides whether price provides sufficient margin of safety.
4. Concentration determines how dangerous a thesis mistake would be (`CONCENTRATED_THESIS_RISK`).
5. Market risk metrics (volatility, correlation, VaR/CVaR, risk contribution) refine sizing and review priority (`HOW-MUCH` layer), but NEVER act as standalone ownership invalidation.

Hard Invariants:
- Hard Invariant 1: Risk contribution (RC) breach alone CANNOT trigger `REDUCE`.
- Hard Invariant 2: Action Precedence strictly enforced (`SELL` -> `REDUCE` -> `HOLD` + `REVIEW_REQUIRED` -> `HOLD` -> `BUY_MORE`).
- Hard Invariant 3: DGC case (weight ~42.2% NAV, RC ~59.5%, thesis intact, MOS positive) returns `HOLD` + `REVIEW_REQUIRED` (not automatic `REDUCE`).
- Hard Invariant 4: Concentration (>= 20% NAV) emits `POSITION_CONCENTRATED` and `CONCENTRATED_THESIS_RISK`, but does not force `REDUCE` when thesis is intact and quality is acceptable.
- Hard Invariant 5: Market risk is a `HOW-MUCH` sizing overlay layer.
- Hard Invariant 6: Permanent loss risk dominates market volatility in decision hierarchy.
- Hard Invariant 7: Valuation safety (`actual_mos_pct - required_mos_pct`) is distinct from business quality (no double counting).
- Hard Invariant 8: Review state represented via `action = "HOLD"` + `REVIEW_REQUIRED` reason code.
- Hard Invariant 9: `new_position_guidance` is distinct from existing holding target (`post_action_target_weight = current_weight` for `HOLD`).
- Hard Invariant 10: Full-coverage RC breach alone yields `HOLD` + `REVIEW_REQUIRED`.

## Context

Previous iterations treated risk contribution breach (`rc > threshold`) as an automatic `REDUCE` gate. In Buffett/Munger investing, volatility and risk contribution describe price fluctuations, not permanent business risk. Allocation logic must demote market risk to a sizing and review priority overlay.

## Acceptance Criteria

- [x] RC breach alone never triggers `REDUCE` (returns `HOLD` + `REVIEW_REQUIRED` with `RISK_CONTRIBUTION_HIGH`).
- [x] High concentration alone never triggers `REDUCE` (returns `HOLD` + `REVIEW_REQUIRED` with `POSITION_CONCENTRATED` & `CONCENTRATED_THESIS_RISK`).
- [x] DGC case (42.2% NAV, 59.5% RC, intact thesis, positive MOS) returns `HOLD` + `REVIEW_REQUIRED` (not `REDUCE`).
- [x] ACB case (38.3% NAV, MOS -7.1pp, intact thesis) returns `HOLD` + `REVIEW_REQUIRED`.
- [x] FPT case (19.5% NAV, MOS -1.3pp, intact thesis) returns `HOLD` + `REVIEW_REQUIRED`.
- [x] `SELL` triggered only by broken thesis / solvency hard reject / accounting unreliability.
- [x] `REDUCE` triggered only by confirmed fundamental deterioration, confirmed severe permanent loss, or concentration + deteriorating thesis/business evidence.
- [x] Market risk metrics (RC, correlation, volatility) refine candidate sizing caps and stress test scenarios without invalidating ownership.
- [x] All 171+ allocation unit and integration tests pass cleanly.
- [x] Frontend build succeeds.

## Constraints and Invariants

1. `VOLATILITY IS NOT PERMANENT LOSS`. `CONCENTRATION IS NOT AUTOMATICALLY BAD`.
2. `THESIS + BUSINESS QUALITY + VALUATION COME FIRST`.
3. `MARKET RISK PRIMARILY REFINES SIZING AND REVIEW PRIORITY`.
4. No ledger mutation. Advisory information only.
5. Expected Alpha and Kelly remain disabled.

## Implementation Tasks

- [x] Update `python/portfolio/allocation/reason_codes.py` and `frontend/src/lib/allocationLabels.js`:
  - Add `CONCENTRATED_THESIS_RISK`, `CYCLICAL_EARNINGS`, `BALANCE_SHEET_REVIEW`, `VOLATILITY_HIGH`, `PERMANENT_LOSS_DATA_INSUFFICIENT`.
- [x] Refactor `python/portfolio/allocation/opportunity.py`:
  - Update `decide_holding()` hierarchy to enforce Buffett-first precedence.
  - Demote RC breach alone to `HOLD` + `REVIEW_REQUIRED`.
  - Pass structured `permanent_loss_context`.
- [x] Update `python/portfolio/allocation/service.py`:
  - Pass `perm_loss_risk["symbol_assessments"]` into `decide_holding()`.
- [x] Update `frontend/src/pages/AllocationPage.jsx`:
  - Render `"GIỮ · CẦN RÀ SOÁT"` for `HOLD` decisions with `REVIEW_REQUIRED`.
  - Render Buffett-first evidence explanation blocks.
- [x] Update and expand test suite in `python/portfolio/tests/test_allocation_risk_gating.py` and `test_allocation_opportunity.py`.
- [x] Run backend test suite: 171 passed across 11 test modules.
- [x] Run `cd frontend && npm run build`: Built successfully in 1.09s.

## Validation Evidence

```powershell
& "$HOME\.venv\Scripts\python.exe" -m pytest -o pythonpath=python python/portfolio/tests/test_allocation_api.py python/portfolio/tests/test_allocation_architecture.py python/portfolio/tests/test_allocation_candidate_tiers.py python/portfolio/tests/test_allocation_domain.py python/portfolio/tests/test_allocation_eligibility.py python/portfolio/tests/test_allocation_execution_planner.py python/portfolio/tests/test_allocation_opportunity.py python/portfolio/tests/test_allocation_risk_gating.py python/portfolio/tests/test_allocation_semantic_invariants.py python/portfolio/tests/test_allocation_service.py python/portfolio/tests/test_allocation_sizing.py

# Results: 171 passed in 2.35s

cd frontend && npm run build
# Results: built in 1.09s
```

## Decisions

- **Decision Hierarchy:** Thesis > Quality > Permanent Loss > MOS > Concentration > Market Risk Overlay > Replacement > Sizing > Execution.
- **Review Action Mapping:** `HOLD` + `REVIEW_REQUIRED` reason code maps to `"GIỮ · CẦN RÀ SOÁT"`.
- **DGC Semantics:** Intact thesis + positive MOS preserves `HOLD` regardless of 42.2% NAV weight or 59.5% RC.

## Result

Completed refactoring Allocation to a true Buffett/Munger-first hierarchy. Market risk metrics (volatility, correlation, RC) refine sizing and review priority (`HOW-MUCH` layer) and never act as standalone REDUCE/SELL triggers.
