---
id: TASK-20260909-119
title: Personal Balance Sheet Domain & Stress Engine (T04, T05, T06)
status: completed
priority: high
created: 2026-09-09
updated: 2026-09-09
tags: [personal-finance, fortress, balance-sheet, stress-engine]
related: [TASK-20260909-118]
---

## Requirement
Create package `python/portfolio/personal_finance/` implementing the Personal Survival Balance Sheet domain (T04), capital durability metrics (T05), and crash / job-loss stress engine (T06).

## Context
Personal capital durability is step 1 in the Buffett-Munger decision precedence hierarchy. Survival reserve funds must be strictly separated from deployable buy capital to prevent forced selling during severe market drawdowns.

## Acceptance Criteria
- [x] Create package `python/portfolio/personal_finance/` with `models.py`, `service.py`, and `stress.py`.
- [x] Implement 4 capital buckets: `SURVIVAL_RESERVE`, `COMPOUNDING_ASSET`, `NEAR_TERM_LIABILITY_FUND`, `OPPORTUNITY_CASH`.
- [x] Implement metrics: Net Worth, Investable Net Worth, Survival Months, Available Long-Term Capital, Reserve Coverage.
- [x] Mandatory Invariant: `survival reserve != buy capital`. `Available Long-Term Capital` formula strictly enforced.
- [x] Deterministic Stress Engine running 4 scenarios (`MARKET_CRASH`, `JOB_LOSS`, `COMBINED`, `FAMILY_SHOCK`) evaluating `FORCED_EQUITY_SALE_REQUIRED: YES/NO`.
- [x] Full unit test suite `python/portfolio/tests/test_personal_finance.py` passing.

## Constraints and Invariants
- No transaction-level expense tracker.
- If required balance sheet data is missing, `PERSONAL_CAPITAL_STATUS = UNKNOWN`, auto-buying is prohibited (`BUILD_RESERVE_FIRST`).

## Implementation Tasks
- [x] Create `python/portfolio/personal_finance/__init__.py`.
- [x] Create `python/portfolio/personal_finance/models.py`.
- [x] Create `python/portfolio/personal_finance/service.py`.
- [x] Create `python/portfolio/personal_finance/stress.py`.
- [x] Create `python/portfolio/tests/test_personal_finance.py`.
- [x] Register task in `docs/tasks/README.md`.

## Related Notes
- Investment Policy: `docs/QPORT_BUFFETT_MUNGER_INVESTMENT_POLICY.md`

## Validation Evidence
- Created `python/portfolio/personal_finance/` package (`models.py`, `service.py`, `stress.py`).
- Unit test suite `python/portfolio/tests/test_personal_finance.py` verified (3/3 tests passed).

## Decisions
- Personal Balance Sheet health directly gates deployable capital and investment state decisions.

## Result
- Tasks T04, T05, T06 completed successfully.

