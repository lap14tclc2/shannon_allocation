---
id: TASK-20260909-121
title: Buffett-Munger Core Decision Engine & Evidence Contract (T08, T09)
status: completed
priority: high
created: 2026-09-09
updated: 2026-09-09
tags: [decision-engine, evidence, policy, buffett-munger]
related: [TASK-20260909-120]
---

## Requirement
Implement deterministic `BuffettPolicyEngine` in `python/portfolio/policy/engine.py` (T08) generating exact 10 decision states, and explainable `DecisionEvidence` payload generator in `python/portfolio/policy/evidence.py` (T09).

## Context
Acts as the central decision brain consuming `InvestmentDecisionContext` and producing deterministic decision states with full rule provenance for UI cards and AI Coach.

## Acceptance Criteria
- [x] Create `python/portfolio/policy/engine.py` (T08).
- [x] Create `python/portfolio/policy/evidence.py` (T09).
- [x] 10 canonical decision states supported with exact precedence evaluation.
- [x] Evidence payload exposes `rules_triggered`, `facts`, `missing_data`, `what_would_change_decision`.
- [x] Full unit test suite `python/portfolio/tests/test_policy_engine.py` passing.

## Constraints and Invariants
- Same input context MUST produce same decision.
- AI Coach cannot alter or override decision output.
- SELL is rare and restricted to structural business failure, solvency crash, or accounting fraud.

## Implementation Tasks
- [x] Create `python/portfolio/policy/engine.py`.
- [x] Create `python/portfolio/policy/evidence.py`.
- [x] Create `python/portfolio/tests/test_policy_engine.py`.
- [x] Register task in `docs/tasks/README.md`.

## Related Notes
- Investment Policy: `docs/QPORT_BUFFETT_MUNGER_INVESTMENT_POLICY.md`

## Validation Evidence
- Created `python/portfolio/policy/engine.py` and `evidence.py`.
- Created unit test suite `python/portfolio/tests/test_policy_engine.py` verifying all 8 Golden Decision Scenarios (8/8 passed).

## Decisions
- Deterministic decision engine guarantees 100% reproducible decisions across runs.

## Result
- Tasks T08 and T09 completed successfully.

