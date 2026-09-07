# TASK-20260907-114: Align Allocation with Buffett-First Thesis, Concentration, and Risk-Overlay Semantics

---
id: TASK-20260907-114
title: Align Allocation with Buffett-First Thesis, Concentration, and Risk-Overlay Semantics
status: completed
priority: high
date: 2026-09-07
---

## Requirement

Refine QPort so `/risk` and `/allocation` follow a true Buffett/Munger-first interpretation:
1. Volatility is not permanent loss. High risk contribution is a review/sizing signal, not an automatic REDUCE/SELL trigger.
2. Concentration is a thesis-impact multiplier (`CONCENTRATED_THESIS_RISK`), not automatically bad.
3. Business quality, thesis integrity, permanent-loss evidence, and valuation safety come before market-risk statistics.
4. Market risk primarily refines sizing, candidate fit, review priority, and scenario stress awareness.
5. Specific portfolio cases:
   - DGC (~40.4% NAV, 59.2% RC, MOS +6.1pp, cyclical, thesis intact): returns `HOLD` + `REVIEW_REQUIRED` (`GIỮ · CẦN RÀ SOÁT`).
   - ACB (~36.7% NAV, 26.8% RC, quality good, MOS -7.2pp, thesis intact): returns `HOLD` + `REVIEW_REQUIRED`.
   - FPT (~18.6% NAV, 14.0% RC, quality good, MOS ~-0.8pp, thesis intact): returns `HOLD` + `REVIEW_REQUIRED`.
6. Non-actionable `HOLD + REVIEW` decisions do not produce executable sell quantity plans.
7. Moat trend defaults to `UNKNOWN` unless multi-period evidence exists.
8. Balance sheet severity `HIGH_RISK` requires confirmed solvency violation (`has_solvency_reject`); non-violating leverage concern is `ATTENTION`.

## Acceptance Criteria

- [x] RC breach alone never triggers `REDUCE` (returns `HOLD` + `REVIEW_REQUIRED`).
- [x] High concentration alone never triggers `REDUCE` (returns `HOLD` + `REVIEW_REQUIRED` with `POSITION_CONCENTRATED` & `CONCENTRATED_THESIS_RISK`).
- [x] DGC case returns `HOLD` + `REVIEW_REQUIRED`.
- [x] ACB case returns `HOLD` + `REVIEW_REQUIRED`.
- [x] FPT case returns `HOLD` + `REVIEW_REQUIRED`.
- [x] Execution planner produces zero trade quantity for `HOLD` & `HOLD + REVIEW`.
- [x] Expanded holding view in UI displays 5 structured Buffett-first sections (Why Own, Valuation, Concentration, Market Risk, Action).
- [x] All 220+ unit/integration tests pass cleanly.
- [x] Frontend build succeeds cleanly.

## Implementation Tasks

- [x] Refactor `python/portfolio/permanent_loss_risk.py`:
  - Ensure `HIGH_RISK` balance sheet status requires `has_solvency_reject`; leverage without solvency violation is `ATTENTION`.
  - Default `moat_trend` to `UNKNOWN` when multi-period evidence is absent.
- [x] Refactor `python/portfolio/risk_warnings.py`:
  - Clarify overall `HIGH_RISK` headline to state concentration/RC driven severity.
- [x] Refactor `python/portfolio/allocation/opportunity.py` and `service.py`:
  - Enforce Buffett-first action precedence hierarchy.
- [x] Update `frontend/src/pages/AllocationPage.jsx` and `frontend/src/allocation-page.css`:
  - Add 5-layer structured Buffett-first grid for holdings.
- [x] Update and verify test suite:
  - Verify all 220 allocation and risk gating tests pass.
- [x] Run `cd frontend && npm run build`.

## Validation Evidence

```powershell
& "$HOME\.venv\Scripts\python.exe" -m pytest -o pythonpath=python python/portfolio/tests/test_allocation_api.py python/portfolio/tests/test_allocation_architecture.py python/portfolio/tests/test_allocation_candidate_tiers.py python/portfolio/tests/test_allocation_domain.py python/portfolio/tests/test_allocation_eligibility.py python/portfolio/tests/test_allocation_execution_planner.py python/portfolio/tests/test_allocation_opportunity.py python/portfolio/tests/test_allocation_risk_gating.py python/portfolio/tests/test_allocation_semantic_invariants.py python/portfolio/tests/test_allocation_service.py python/portfolio/tests/test_allocation_sizing.py python/portfolio/tests/test_permanent_loss_risk.py python/portfolio/tests/test_risk_warnings.py python/portfolio/tests/test_risk_data_integrity.py

# Results: 220 passed in 2.77s

cd frontend && npm run build
# Results: built in 1.10s
```

## Decisions

- **Decision Hierarchy:** Thesis > Business Quality > Permanent Loss Risk > Valuation / MOS > Concentration > Market Risk Overlay > Opportunity Cost > Sizing > Execution.
- **Review Mapping:** `HOLD` + `REVIEW_REQUIRED` maps to `"GIỮ · CẦN RÀ SOÁT"`.
- **Zero Trade Execution for HOLD:** Non-trading decisions carry `rounded_quantity_change = 0` and `is_executable = True/False` without trade order generation.

## Result

Successfully aligned Allocation and Risk semantics with Buffett-first principles. DGC, ACB, and FPT return HOLD + REVIEW with clear multi-layer explanations. 220 test cases pass cleanly and production build compiled in 1.10s.
