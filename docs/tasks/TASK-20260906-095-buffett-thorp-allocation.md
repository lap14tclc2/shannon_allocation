---
id: TASK-20260906-095
title: Implement Buffett Core + Thorp Overlay Allocation Architecture
status: ready
priority: high
created: 2026-09-06
updated: 2026-09-06
tags: [allocation, buffett, thorp, risk, screener, research, point-in-time]
related: [BUY_AND_HOLD_SYSTEM_SPEC.md, AGENTS.md]
---

## Requirement

Redesign QPort toward a long-term capital-allocation system for a retail investor using:

- Buffett Core for business quality, valuation, and investability;
- Thorp Overlay for correlation, covariance, risk contribution, concentration, and sizing;
- existing Screener as candidate discovery;
- opportunity-cost logic for conservative portfolio rotation;
- cash as a valid allocation;
- HOLD as the default action.

The implementation must remain advisory and must never autonomously execute trades.

## Context

QPort already contains strong building blocks:

- canonical Buffett/Munger valuation engine;
- quality and hard-reject logic;
- screener with Buffett MOS and liquidity filtering;
- portfolio risk engine with correlation matrix, covariance, volatility, risk contribution, ERC reference, HHI, effective positions, diversification ratio, VaR/CVaR, and downside statistics;
- multi-portfolio support;
- DB-first production behavior.

The target is not a high-turnover quant trading system. It is a long-horizon allocation layer that combines existing valuation and risk intelligence while minimizing unnecessary churn.

Implementation guidance was compared with `lap14tclc2/recommended_share` agent governance:

- architecture contract is authoritative;
- mutating work is task-first;
- architecture deviations require ADR;
- no DONE without verification evidence;
- point-in-time truth must be enforced for historical research;
- atomic tasks should be independently verifiable.

Reference skills inspected:

- `.agents/skills/architecture-guard/SKILL.md`
- `.agents/skills/task-execution/SKILL.md`

## Acceptance Criteria

- [ ] Add Allocation backend domain without duplicating current valuation or risk engines.
- [ ] Reuse canonical Value Engine for investability/valuation inputs.
- [ ] Reuse canonical `portfolio_risk()` for correlation/covariance/risk simulation.
- [ ] Reuse Screener for candidate discovery only; Screener must not directly execute or create trades.
- [ ] Add deterministic actions: `BUY_MORE`, `HOLD`, `WATCH`, `REDUCE`, `SELL`, `KEEP_CASH` as recommendations only.
- [ ] `HOLD` and `KEEP_CASH` are first-class successful outcomes.
- [ ] Hard rejects always override momentum/technical signals.
- [ ] Avoid double-counting quality/leverage already embedded in valuation logic.
- [ ] Add `/api/portfolio/allocation` read-only evaluation endpoint.
- [ ] Add `/api/portfolio/allocation/simulate` hypothetical before/after risk endpoint with no persistence.
- [ ] Add `/allocation` UI with portfolio verdict, holdings, 3–5 new opportunities, proposed changes, and before/after risk impact.
- [ ] Preserve `X-QPort-Portfolio-Id` isolation and multi-portfolio behavior.
- [ ] Preserve hide-values/privacy behavior.
- [ ] No autonomous trade execution.
- [ ] No numerical expected alpha in V1.
- [ ] No Kelly sizing in V1.
- [ ] Add point-in-time research foundation before any historical alpha claim.
- [ ] Add VNIndex benchmark before factor excess-return validation.
- [ ] Add architecture/unit/integration tests and frontend build evidence before completion.

## Constraints and Invariants

1. Follow root `AGENTS.md` Zettelkasten task-first workflow.
2. Preserve `BUY_AND_HOLD_INFORMATION_SYSTEM` philosophy.
3. Allocation output is advice/recommendation only; only explicit user transactions/events may mutate ledger balances.
4. Existing `python/portfolio/risk.py` is the single source of truth for portfolio covariance/correlation/risk metrics.
5. Existing `python/portfolio/value_engine/` remains the single source of truth for valuation.
6. Existing Screener remains candidate discovery and must not become an execution engine.
7. No external provider crawl in a production allocation request when canonical DB data is available.
8. Missing or stale data must degrade confidence; never fabricate fallback values.
9. Historical research must obey `available_from <= as_of_date` semantics.
10. No fake alpha, no full Kelly, no automatic daily rotation.
11. Architecture deviation requires ADR before implementation.

## Implementation Tasks

- [ ] T00 Commit architecture/system plan and implementation plan.
- [ ] T01 Create `python/portfolio/allocation/` domain models and reason codes.
- [ ] T02 Implement Buffett eligibility adapter from canonical valuation outputs.
- [ ] T03 Implement Screener candidate adapter with max 3–5 candidates.
- [ ] T04 Implement hypothetical portfolio-fit simulation by reusing `portfolio_risk()`.
- [ ] T05 Implement conservative opportunity-cost decision engine with hysteresis.
- [ ] T06 Add allocation API endpoints and multi-portfolio isolation tests.
- [ ] T07 Add responsive `/allocation` UI and transaction-draft handoff only.
- [ ] T08 Run V1 architecture/test/build audit.
- [ ] T09 Audit/implement point-in-time fundamental availability metadata.
- [ ] T10 Implement and verify VNIndex benchmark service.
- [ ] T11 Persist factor snapshots.
- [ ] T12 Persist forward benchmark-relative outcomes.
- [ ] T13 Add IC, quantile spread, walk-forward, and sealed-OOS validation.
- [ ] T14 Only if T13 validates an edge, research expected-alpha calibration.
- [ ] T15 Only after validated alpha, optionally research fractional Kelly under hard caps.

## Related Notes

- `docs/QPORT_BUFFETT_THORP_SYSTEM_PLAN.md`
- `docs/QPORT_BUFFETT_THORP_IMPLEMENTATION.md`
- `BUY_AND_HOLD_SYSTEM_SPEC.md`
- `AGENTS.md`
- reference repository: `lap14tclc2/recommended_share`

## Validation Evidence

Architecture preparation evidence:

- QPort root `AGENTS.md` inspected on `main`.
- `recommended_share/AGENTS.md` inspected.
- `recommended_share/.agents/skills/architecture-guard/SKILL.md` inspected.
- `recommended_share/.agents/skills/task-execution/SKILL.md` inspected.
- Current QPort risk engine previously audited and confirmed to expose correlation/covariance/ERC/risk contribution metrics.

No source-code implementation has started in this task yet, therefore runtime/test evidence is pending.

## Decisions

1. User-facing module name will be `Allocation / Phân bổ vốn`; “Thorp” is an internal architectural concept, not a trading-brand UI.
2. `/valuation`, `/risk`, and `/screener` remain independent views and canonical engines.
3. Allocation V1 is deterministic, conservative, read-only, and recommendation-only.
4. Expected alpha and Kelly are explicitly locked until point-in-time and OOS research gates pass.
5. The initial implementation branch is `feature/buffett-thorp-allocation`.

## Result

Architecture checkpoint prepared. Task is `ready`; source implementation begins only after this checkpoint commit.
