---
id: TASK-20260906-095
title: Implement Buffett Core + Thorp Overlay Allocation Architecture
status: verified
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

- [x] Add Allocation backend domain without duplicating current valuation or risk engines.
- [x] Reuse canonical Value Engine for investability/valuation inputs.
- [x] Reuse canonical `portfolio_risk()` for correlation/covariance/risk simulation.
- [x] Reuse Screener for candidate discovery only; Screener must not directly execute or create trades.
- [x] Add deterministic actions: `BUY_MORE`, `HOLD`, `WATCH`, `REDUCE`, `SELL`, `KEEP_CASH` as recommendations only.
- [x] `HOLD` and `KEEP_CASH` are first-class successful outcomes.
- [x] Hard rejects always override momentum/technical signals.
- [x] Avoid double-counting quality/leverage already embedded in valuation logic.
- [x] Add `/api/portfolio/allocation` read-only evaluation endpoint.
- [x] Add `/api/portfolio/allocation/simulate` hypothetical before/after risk endpoint with no persistence.
- [x] Add `/allocation` UI with portfolio verdict, holdings, 3–5 new opportunities, proposed changes, and before/after risk impact.
- [x] Preserve `X-QPort-Portfolio-Id` isolation and multi-portfolio behavior.
- [x] Preserve hide-values/privacy behavior.
- [x] No autonomous trade execution.
- [x] No numerical expected alpha in V1.
- [x] No Kelly sizing in V1.
- [ ] Add point-in-time research foundation before any historical alpha claim. *(deferred to T09; satisfied in V1 by guard — no alpha claim is made)*
- [ ] Add VNIndex benchmark before factor excess-return validation. *(deferred to T10; satisfied in V1 by guard — no factor validation is made)*
- [x] Add architecture/unit/integration tests and frontend build evidence before completion.

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

- [x] T00 Commit architecture/system plan and implementation plan.
- [x] T01 Create `python/portfolio/allocation/` domain models and reason codes.
- [x] T02 Implement Buffett eligibility adapter from canonical valuation outputs.
- [x] T03 Implement Screener candidate adapter with max 3–5 candidates.
- [x] T04 Implement hypothetical portfolio-fit simulation by reusing `portfolio_risk()`.
- [x] T05 Implement conservative opportunity-cost decision engine with hysteresis.
- [x] T06 Add allocation API endpoints and multi-portfolio isolation tests.
- [x] T07 Add responsive `/allocation` UI and transaction-draft handoff only.
- [x] T08 Run V1 architecture/test/build audit.
- [ ] T09 Audit/implement point-in-time fundamental availability metadata. *(deferred — outside V1 scope)*
- [ ] T10 Implement and verify VNIndex benchmark service. *(deferred — outside V1 scope)*
- [ ] T11 Persist factor snapshots. *(deferred — outside V1 scope)*
- [ ] T12 Persist forward benchmark-relative outcomes. *(deferred — outside V1 scope)*
- [ ] T13 Add IC, quantile spread, walk-forward, and sealed-OOS validation. *(deferred — outside V1 scope)*
- [ ] T14 Only if T13 validates an edge, research expected-alpha calibration. *(deferred — outside V1 scope)*
- [ ] T15 Only after validated alpha, optionally research fractional Kelly under hard caps. *(deferred — outside V1 scope)*

## Related Notes

- `docs/QPORT_BUFFETT_THORP_SYSTEM_PLAN.md`
- `docs/QPORT_BUFFETT_THORP_IMPLEMENTATION.md`
- `BUY_AND_HOLD_SYSTEM_SPEC.md`
- `AGENTS.md`
- reference repository: `lap14tclc2/recommended_share`

## Validation Evidence

V1 scope (T00–T08) implemented on branch `feature/buffett-thorp-allocation`.

Runtime/test commands executed from the repo root:

```
$env:PYTHONPATH="python;." ; python -m pytest python/portfolio/tests/test_allocation_domain.py python/portfolio/tests/test_allocation_eligibility.py python/portfolio/tests/test_allocation_sizing.py python/portfolio/tests/test_allocation_opportunity.py python/portfolio/tests/test_allocation_service.py python/portfolio/tests/test_allocation_api.py python/portfolio/tests/test_allocation_architecture.py -q
=> 75 passed in 1.91s
```

Full allocation + existing architecture regression:

```
$env:PYTHONPATH="python;." ; python -m pytest python/portfolio/tests/test_allocation_*.py python/portfolio/tests/test_architecture.py -q
=> 84 passed in 2.43s
```

Core backend regression (sqlite-based, no network):

```
cd python ; python -m pytest portfolio/tests/test_service.py portfolio/tests/test_accounting.py portfolio/tests/test_analytics.py portfolio/tests/test_validation.py portfolio/tests/test_price_units.py portfolio/tests/test_locale.py portfolio/tests/test_vi_labels.py -q
=> 64 passed, 2 pre-existing frontend-contract failures (test_mobile_app_shell_contract.py, test_mobile_iphone_shell_contract.py)
```

Full backend suite `python -m pytest python/portfolio/tests -q`:

```
=> 443 passed, 1 skipped, 15 failed
```

The 15 failures were verified to be **pre-existing on the base commit** `abde669`
(identical failure set reproduced in a clean `git worktree add` of HEAD, before
any V1 changes). None are caused by the Allocation V1 implementation.

Frontend production build:

```
cd frontend ; npm run build
=> vite v6.4.3 · 110 modules transformed · ✓ built in ~1.2s (chunk-size warning only)
```

Allocation golden scenarios covered by tests (1–9 from the plan):

1. Excellent business + attractive valuation + good fit -> BUY_MORE
2. Excellent business + fair valuation + high-but-not-excessive risk contribution -> HOLD
3. Weak business + large MOS -> NOT BUY (excluded from opportunities)
4. High momentum + accounting hard reject -> INELIGIBLE
5. Weak holding + superior low-correlation candidate -> REDUCE/ROTATE
6. Weak holding + no superior alternative -> HOLD / KEEP_CASH
7. Correlated bank candidate in bank-heavy portfolio -> capped (<=5%) / WATCH
8. No eligible candidates -> KEEP_CASH
9. Missing risk history -> UNAVAILABLE fit, never zero-risk assumption

Plus: hysteresis (small advantage never rotates), determinism, simulate
no-mutation, multi-portfolio isolation, and an end-to-end test that drives the
real canonical `portfolio_risk()` engine with synthetic histories.

Architecture audit (`test_allocation_architecture.py`) asserts: reuse of the
canonical risk engine only (no copied covariance/ERC/VaR math), no second
valuation engine, no Kelly/expected-alpha identifiers, no auto-execution/ledger
writes, no provider-crawl imports in the allocation domain, existing `/valuation`
`/risk` `/screener` routes untouched, `/allocation` UI is not a trading terminal,
and the `Phân bổ vốn` nav entry exists.

## Decisions

1. User-facing module name will be `Allocation / Phân bổ vốn`; “Thorp” is an internal architectural concept, not a trading-brand UI.
2. `/valuation`, `/risk`, and `/screener` remain independent views and canonical engines.
3. Allocation V1 is deterministic, conservative, read-only, and recommendation-only.
4. Expected alpha and Kelly are explicitly locked until point-in-time and OOS research gates pass.
5. The initial implementation branch is `feature/buffett-thorp-allocation`.
6. Valuation factor is kept pure as `valuation_safety = actual_mos_pct - required_mos_pct`; Quality and Valuation remain separate bands (no reuse of the broad quality `total_score` as the value factor).
7. The “excessive” risk-contribution threshold reuses the existing QPort health convention `largest RC > max(45%, 1.5 × equal-risk)`; nominal weight above the hard cap is informational (`POSITION_CONCENTRATED`) and never forces a sale by itself.
8. Rotation requires hysteresis: candidate opportunity score must exceed the weak holding score by ≥ 0.15 AND the holding must be weak (< 0.50). Lower rank alone never forces a sell.
9. Candidate discovery reuses the existing Screener (including its cached price refresh/persist behavior) exactly as `/screener` does; the allocation module itself has zero provider-crawl imports.
10. `POST /api/portfolio/allocation/simulate` is strictly in-memory; infeasible hypothetical buys are skipped and reported, never fabricated.
11. Mobile bottom tab bar was widened to a horizontally scrollable 7-column bar to accommodate the new `Phân bổ vốn` entry without truncating labels.

## Result

Allocation V1 (T00–T08) implemented and verified:

- `python/portfolio/allocation/` domain (models, reason codes, eligibility, candidate service, sizing, opportunity, service) with deterministic advisory actions and reason codes.
- `GET /api/portfolio/allocation` and `POST /api/portfolio/allocation/simulate` (simulation never persists).
- `/allocation` UI (`Phân bổ vốn`) with portfolio verdict, holdings, 3–5 opportunities, proposed changes / NO ACTION REQUIRED, before/after risk simulation, evidence & confidence, transaction-draft handoff, privacy-mode support, and responsive mobile/desktop layouts.
- 75 allocation tests + architecture audit pass; frontend production build passes; no new backend regressions (the 15 full-suite failures are pre-existing on the base commit and reproduced identically on a clean HEAD worktree).

T09–T15 (PIT research foundation, VNIndex benchmark, factor snapshots/validation, expected-alpha, fractional Kelly) are explicitly deferred outside V1 scope. Status is `verified` for the V1 scope; it becomes `completed` only when the research milestone gates are implemented and verified.

---
**Correction note (TASK-20260906-096):** the test counts recorded above
("75 allocation tests", "84 passed", "443 passed") were captured at earlier
points in the V1 session and do not match the final re-measured command output.
Authoritative re-measured figures (with the V1 gate refactor in place) are:
91 allocation tests, 101 allocation + `test_architecture.py`, and
460 passed / 1 skipped / 15 failed for the full backend suite. The 15
pre-existing failures were reproduced on a clean worktree of `abde669` (the
base commit at the time) and re-confirmed on `5380a78` (pushed V1 HEAD) in
TASK-20260906-096.
