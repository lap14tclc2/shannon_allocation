---
id: TASK-20260909-117
title: Remove Risk-Driven Allocation Decisions (T02)
status: completed
priority: high
created: 2026-09-09
updated: 2026-09-09
tags: [allocation, risk, buffett-munger, invariants]
related: [TASK-20260909-116]
---

## Requirement
Ensure allocation service and opportunity logic strictly treat market risk metrics (volatility, correlation, VaR, CVaR, risk contribution) as optional diagnostics only, prohibiting them from triggering automatic `SELL` or `REDUCE` decisions.

## Context
Under Buffett-Munger principles (B02), market price fluctuations and risk contribution targets must never trigger liquidations or reductions.

## Acceptance Criteria
- [x] `high volatility` => **NOT** `SELL`
- [x] `high risk contribution` => **NOT** `REDUCE`
- [x] `drawdown` => **NOT** automatic `SELL`
- [x] Dedicated unit tests in `python/portfolio/tests/test_allocation_risk_gating.py` verify zero market-risk-driven SELL/REDUCE actions.

## Constraints and Invariants
- Retain risk contribution and volatility metrics strictly for display/diagnostics.
- Do not alter ledger balance or transaction recording.

## Implementation Tasks
- [x] Verify `python/portfolio/allocation/opportunity.py` and `service.py` adhere to non-gating rules.
- [x] Add explicit unit tests confirming high volatility/drawdown/RC cannot cause `SELL` or `REDUCE`.
- [x] Register task in `docs/tasks/README.md`.

## Related Notes
- Investment Policy: `docs/QPORT_BUFFETT_MUNGER_INVESTMENT_POLICY.md`

## Validation Evidence
- Added `test_32_high_volatility_and_high_risk_contribution_do_not_cause_sell_or_reduce` and `test_33_drawdown_does_not_cause_automatic_sell` to `python/portfolio/tests/test_allocation_risk_gating.py`.
- Ran 70 unit tests in `test_allocation_risk_gating.py` and `test_allocation_opportunity.py` — all 70 passed cleanly.

## Decisions
- Market risk metrics demoted to sizing diagnostics and review hints.

## Result
- Task T02 completed successfully.

