---
id: TASK-20260909-116
title: Canonical Buffett-Munger Investment Policy (T01)
status: completed
priority: high
created: 2026-09-09
updated: 2026-09-09
tags: [policy, buffett-munger, specification]
related: [TASK-20260909-115]
---

## Requirement
Create authoritative, canonical Buffett/Munger Investment Policy document `docs/QPORT_BUFFETT_MUNGER_INVESTMENT_POLICY.md` establishing core philosophy, decision precedence, prohibited triggers, state definitions, UNKNOWN semantics, concentration rules, and no-action semantics.

## Context
QPort requires one single source of truth for all investment decision logic consumed by policy engines, terminal UI, AI coach, and test suites.

## Acceptance Criteria
- [x] Document `docs/QPORT_BUFFETT_MUNGER_INVESTMENT_POLICY.md` created.
- [x] 10-step decision precedence explicitly defined.
- [x] Prohibited decision triggers explicitly listed.
- [x] 10 canonical decision states defined with exact entry/exit conditions.
- [x] First-class `UNKNOWN` degradation semantics established.
- [x] Concentration and No-Action semantics codified.

## Constraints and Invariants
- Zero technical analysis, market-timing, or volatility-driven sell triggers allowed.
- Survival reserve funds strictly separated from deployable buy capital.
- Deterministic behavior: same input context yields same decision state.

## Implementation Tasks
- [x] Create `docs/QPORT_BUFFETT_MUNGER_INVESTMENT_POLICY.md`.
- [x] Verify alignment with Master Refactor Plan requirements B01-B30.
- [x] Register task in `docs/tasks/README.md`.

## Related Notes
- Refactor Master Plan: `QPort Buffett–Munger Refactor Plan for Antigravity`
- Architecture Audit: `docs/QPORT_BUFFETT_TERMINAL_ARCHITECTURE_AUDIT.md`

## Validation Evidence
- Created `docs/QPORT_BUFFETT_MUNGER_INVESTMENT_POLICY.md`.
- Codified 10-step precedence, prohibited triggers table, 10 canonical decision states, missing data degradation, personal balance sheet formula, and value trap gate order.

## Decisions
- Canonical investment policy finalized as authoritative reference for T02-T20 implementations.

## Result
- Task T01 completed successfully.

