---
id: TASK-20260906-100
title: Fix Allocation Reduce-to-Zero and Missing-Data Decision Semantics
status: verified

priority: high
created: 2026-09-06
updated: 2026-09-06
tags: [allocation, buffett, thorp, semantics, decision, invariants, ui]
related: [TASK-20260906-095-buffett-thorp-allocation.md, TASK-20260906-096-refactor-allocation-remove-composite-weights.md, BUY_AND_HOLD_SYSTEM_SPEC.md, AGENTS.md]
---

## Requirement

Audit and correct semantic bugs in Allocation V1 holding decision semantics and UI rendering:

1. **REDUCE MUST NOT MEAN ZERO**:
   - `REDUCE -> 0.0%` is semantically invalid.
   - `SELL` has target weight 0%.
   - `REDUCE` target weight MUST remain > 0%.
   - `HOLD` preserves current position or valid allocation band.
   - `WATCH / REVIEW` requires no actionable target.
   - Enforce invariant `validate_decision_semantics(decision)`: if `REDUCE`, `target_mid` > 0 (or None when no target evidence); if `SELL`, `target_mid` == 0.

2. **MISSING DATA MUST NOT CAUSE FORCED SELL/REDUCE**:
   - Missing evidence is NOT negative evidence (`UNKNOWN != BAD`).
   - `DATA_INSUFFICIENT`, missing public valuation, `valuation_confidence == LOW`, incomplete model, missing risk history, or missing quality evidence must NOT force `REDUCE` or `SELL`.
   - Existing holdings with missing/low-confidence evidence degrade to `HOLD` + `REVIEW_REQUIRED` (or non-trading advisory state).

3. **DISTINGUISH THESIS FAILURE FROM DATA FAILURE**:
   - Separate destructive thesis/safety rejects (`SOLVENCY_RISK`, `ACCOUNTING_UNRELIABLE`, `EXCESSIVE_DILUTION`, `UNNORMALIZABLE_EARNINGS`, `CIRCLE_OF_COMPETENCE_FAIL`) from non-destructive data quality rejects (`DATA_INSUFFICIENT`, missing public valuation).
   - Thesis-breaking rejects justify `SELL` (target 0%) or `REDUCE` with positive target.
   - Data quality rejects map existing holdings to `HOLD` + `REVIEW_REQUIRED` (and candidate to `WATCH`).

4. **LOW QUALITY SHOULD MEAN PARTIAL REDUCTION**:
   - Confirmed `LOW_QUALITY` existing holdings map to `REDUCE` with a valid positive partial target (`0 < target_mid < current_weight`), derived from sizing policy, NOT `target_mid = 0`.

5. **UI & REASON CODES**:
   - UI must never render `Giảm bớt → 0.0%`.
   - For `REDUCE`, render `current_weight → target_weight` (e.g. `18.4% → 10.0%`).
   - For `SELL`, render `current_weight → 0%`.
   - Omit target arrow when `target_mid` is null.
   - Add explicit reason codes (`REVIEW_REQUIRED`, `THESIS_BROKEN`, `NO_PUBLIC_VALUATION`, etc.).

## Context

Audit of reported cases (FRT, VJC, KSV, REE, VGI, GAS) showed `REDUCE -> 0.0%` appearing for holdings with missing data or low valuation confidence.
Root causes identified:
1. `eligibility.py` classified `DATA_INSUFFICIENT` as a hard reject, forcing `status = "INELIGIBLE"`.
2. `opportunity.py` `decide_holding()` hardcoded `target_mid = 0.0` for `REDUCE` when `status == "INELIGIBLE"`.
3. `service.py` rotation coordination set `action = "REDUCE"` with `target_mid = 0.0` when proposing a replacement.
4. `AllocationPage.jsx` rendered `→ target` without checking if `action == 'REDUCE'` had a valid target vs zero, or showing `current → target`.

## Acceptance Criteria

- [x] `validate_decision_semantics(decision)` helper added to enforce invariants:
  - `action == "REDUCE"` requires `target_mid is None` or `0 < target_mid < current_weight`.
  - `action == "SELL"` requires `target_mid == 0.0`, `target_min == 0.0`, `target_max == 0.0`.
  - `action == "BUY_MORE"` requires `target_mid > 0.0`.
  - `action == "HOLD"` / `WATCH` preserves target or sets `None`.
- [x] `eligibility.py` separates destructive thesis hard rejects from `DATA_INSUFFICIENT`.
- [x] `DATA_INSUFFICIENT` alone or missing valuation does not trigger `status = "INELIGIBLE"` or `HARD_REJECT`.
- [x] Existing holding with missing/low-confidence data yields `action = "HOLD"` with `reason_codes` including `REVIEW_REQUIRED` and `DATA_INSUFFICIENT`.
- [x] Existing holding with confirmed `LOW_QUALITY` yields `action = "REDUCE"` with a positive `target_mid` (`0 < target_mid < current_weight`).
- [x] Existing holding with excessive risk contribution yields `action = "REDUCE"` with a positive `target_mid` (`0 < target_mid < current_weight`).
- [x] Rotation exit yields `action = "SELL"` (target 0%) or partial `action = "REDUCE"` (target > 0). `REDUCE -> 0%` is eliminated across backend.
- [x] `reason_codes.py` and `allocationLabels.js` enriched with `REVIEW_REQUIRED`, `THESIS_BROKEN`, `NO_PUBLIC_VALUATION`.
- [x] `AllocationPage.jsx` renders `current_weight → target_weight` for `REDUCE`, `current_weight → 0%` for `SELL`, and omits target arrow when target is null.
- [x] Complete 20+ item test matrix verified in pytest (101 allocation suite tests passed).
- [x] Frontend build verified (`npm run build` completed cleanly).

## Constraints and Invariants

1. `BUY_AND_HOLD_INFORMATION_SYSTEM` philosophy preserved — advisory only, no auto-execution, no ledger mutation.
2. `UNKNOWN != BAD`: missing data is not negative evidence for existing holdings.
3. `REDUCE != SELL`: `REDUCE` target weight MUST be > 0%. 0% target is `SELL`.
4. Single sources of truth preserved: canonical Value Engine for valuation, `portfolio_risk()` for risk.

## Implementation Tasks

- [x] Task 1: Update `python/portfolio/allocation/reason_codes.py` with missing codes (`REVIEW_REQUIRED`, `THESIS_BROKEN`, `NO_PUBLIC_VALUATION`).
- [x] Task 2: Add `validate_decision_semantics()` helper to `python/portfolio/allocation/models.py` and enforce in `AllocationDecision.__post_init__` or validation module.
- [x] Task 3: Update `python/portfolio/allocation/eligibility.py` to separate destructive thesis rejects from `DATA_INSUFFICIENT` data quality rejects.
- [x] Task 4: Update `python/portfolio/allocation/opportunity.py` `decide_holding()` to handle `THESIS_BROKEN` (SELL 0%), `LOW_QUALITY` (REDUCE >0%), `RISK_BREACH` (REDUCE >0%), and `DATA_INSUFFICIENT` / `LOW_CONFIDENCE` (HOLD + REVIEW_REQUIRED).
- [x] Task 5: Update `python/portfolio/allocation/service.py` rotation logic to set `SELL` for full rotation exit or `REDUCE` with positive target.
- [x] Task 6: Update `frontend/src/lib/allocationLabels.js` and `frontend/src/pages/AllocationPage.jsx` to render proper target arrows (`current → target` for REDUCE, `current → 0%` for SELL, omit when null).
- [x] Task 7: Update and expand backend unit/architecture/service tests covering the 20+ test matrix.
- [x] Task 8: Run pytest suite and frontend production build (`npm run build`).

## Related Notes

- FRT, VJC, KSV, REE, VGI, GAS reported cases.

## Validation Evidence

1. **Pytest Allocation Suite**: 101 tests passed in 2.00s.
   Command: `.venv/Scripts/python.exe -m pytest python/portfolio/tests/test_allocation*.py`
2. **Frontend Build**: Vite build succeeded with 0 errors.
   Command: `npm run build` (in `frontend/`)
   Output: `dist/index.html`, `dist/assets/index-CWjYSkaw.css`, `dist/assets/index-CJMZwyJ3.js`.

## Decisions

- Destructive hard rejects (`SOLVENCY_RISK`, `ACCOUNTING_UNRELIABLE`, `EXCESSIVE_DILUTION`, `UNNORMALIZABLE_EARNINGS`, `CIRCLE_OF_COMPETENCE_FAIL`) lead to `SELL` (0%).
- `DATA_INSUFFICIENT` is classified as a data quality reject, not a thesis reject. For existing holdings, it leads to `HOLD` + `REVIEW_REQUIRED`.
- `REDUCE` targets are strictly positive (`0 < target_mid < current_weight`).

## Result

Completed and verified.

