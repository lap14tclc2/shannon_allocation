---
id: TASK-20260909-123
title: Golden Baseline Regression & System Invariants Test Suite (T17, T20)
status: completed
priority: high
created: 2026-09-09
updated: 2026-09-09
tags: [regression, golden-tests, invariants, testing]
related: [TASK-20260909-122]
---

## Requirement
Build end-to-end regression test suite `python/portfolio/tests/test_golden_baseline_regression.py` verifying golden baseline symbols (`ACB`, `DGC`, `FPT`), ledger invariants, missing-data degradation, and financial data-source boundary isolation.

## Context
Verifies that the Buffett-Munger refactor maintains strict ledger non-regression and guarantees deterministic outputs for representative stocks.

## Acceptance Criteria
- [x] Baseline symbols `ACB`, `DGC`, `FPT` verified for ledger non-regression.
- [x] All 16 Golden Decision scenarios verified in automated test suite.
- [x] Data-source boundary interface confirmed isolated from vendor details.
- [x] Full test suite `python/portfolio/tests/test_golden_baseline_regression.py` passing.

## Constraints and Invariants
- `NULL != 0`, `UNKNOWN` qualitative evidence preserved.
- Ledger quantities invariant to price or risk metric changes.

## Implementation Tasks
- [x] Create `python/portfolio/tests/test_golden_baseline_regression.py`.
- [x] Run pytest suite.
- [x] Register task in `docs/tasks/README.md`.

## Related Notes
- Investment Policy: `docs/QPORT_BUFFETT_MUNGER_INVESTMENT_POLICY.md`

## Validation Evidence
- Created `python/portfolio/tests/test_golden_baseline_regression.py`.
- Verified 61/61 automated tests passing cleanly in 1.37s across policy, personal finance, business review, value trap gate, allocation risk gating, and golden baseline suites.

## Decisions
- Automated golden decision tests guarantee system reliability under future updates.

## Result
- Task T17 completed successfully.

