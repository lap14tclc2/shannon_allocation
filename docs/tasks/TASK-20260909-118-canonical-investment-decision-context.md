---
id: TASK-20260909-118
title: Canonical InvestmentDecisionContext (T03)
status: completed
priority: high
created: 2026-09-09
updated: 2026-09-09
tags: [policy, domain, context, buffett-munger]
related: [TASK-20260909-116, TASK-20260909-117]
---

## Requirement
Create canonical `InvestmentDecisionContext` dataclass and builder service in `python/portfolio/policy/` unifying portfolio holding context, business quality dimensions, valuation estimates, personal capital status, value trap assessment, hard rejects, missing data, and warnings into one aggregate payload.

## Context
Decouples decision making from distributed modules. Consumed by policy engine, API endpoints, terminal UI, AI evidence coach, and golden test suites.

## Acceptance Criteria
- [x] Create package `python/portfolio/policy/` with `models.py` and `context_builder.py`.
- [x] `InvestmentDecisionContext` dataclass with serialization `to_dict()` and `from_dict()`.
- [x] Data availability and degradation attributes included.
- [x] Builder service constructs context from existing portfolio ledgers, valuation engine reports, and personal finance status.
- [x] Unit test suite `python/portfolio/tests/test_policy_context.py` written and passing.

## Constraints and Invariants
- `NULL != 0`, `UNKNOWN` qualitative states preserved.
- One single backend call produces complete decision evidence set.
- Frontend does not recompute business or valuation metrics.

## Implementation Tasks
- [x] Create `python/portfolio/policy/__init__.py`.
- [x] Create `python/portfolio/policy/models.py`.
- [x] Create `python/portfolio/policy/context_builder.py`.
- [x] Create `python/portfolio/tests/test_policy_context.py`.
- [x] Register task in `docs/tasks/README.md`.

## Related Notes
- Investment Policy: `docs/QPORT_BUFFETT_MUNGER_INVESTMENT_POLICY.md`

## Validation Evidence
- Created `python/portfolio/policy/models.py` (`InvestmentDecisionContext`), `context_builder.py` (`build_decision_context`).
- Created unit test suite `python/portfolio/tests/test_policy_context.py` — all 3 tests passed.

## Decisions
- Unified decision aggregate eliminates ad-hoc logic across API routers and UI pages.

## Result
- Task T03 completed successfully.

