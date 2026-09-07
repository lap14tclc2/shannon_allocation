# TASK-20260907-111: Gate Allocation Decisions on Reliable Risk Coverage and Permanent-Loss Evidence

---
id: TASK-20260907-111
title: Gate Allocation Decisions on Reliable Risk Coverage and Permanent-Loss Evidence
status: completed
priority: high
date: 2026-09-07
---

## Requirement

Harden the coupling between `/risk` and `/allocation` to prevent partial/unreliable market risk data from improperly driving allocation decisions:
1. Risk Usability Contract: Expose `market_risk_data_status` (`VALID`, `PARTIAL`, `INSUFFICIENT`), `market_risk_actionable` (bool), `risk_contribution_scope` (`FULL_PORTFOLIO`, `ELIGIBLE_UNIVERSE_ONLY`, `UNAVAILABLE`), and `risk_context` in risk/allocation payloads.
2. Governance Coverage Policy: Centralize `MIN_MARKET_RISK_NAV_COVERAGE = 0.80` and `MIN_MARKET_RISK_SYMBOLS = 2`. Set `market_risk_actionable = true` only when coverage meets governance criteria.
3. Partial Risk Diagnostic Only: Partial market risk is diagnostic; Allocation MUST NOT use partial covariance metrics to trigger `REDUCE`, risk caps, rotation, or candidate BUY sizing.
4. Fix `_current_fit()`: Return `UNAVAILABLE` when `market_risk_actionable` is `false`. Do not compute `GOOD`/`MODERATE`/`WEAK` from partial data. Capital concentration is tracked separately.
5. Fix `_fit_for_proposed()`: Candidate simulation sets `risk_available = false` and `fit = UNAVAILABLE` when portfolio/candidate coverage is inadequate. Missing correlation (`None`) is NOT `GOOD` fit. `UNKNOWN != GOOD`.
6. Candidate Unknown Market Fit: Candidate with unknown market fit cannot become `BUY_READY` (placed in `WATCHLIST` / `RESEARCH`), unless explicit policy allows.
7. Existing Holding Unknown Market Risk: Existing holding with unavailable market risk defaults to `HOLD` / `REVIEW_REQUIRED` (not automatic `REDUCE`). `UNKNOWN != BAD`.
8. Permanent-Loss Decision Precedence: Permanent capital loss risk (Thesis break > Solvency/Accounting > Business Quality > MOS) dominates market volatility risk in decision hierarchy.
9. Capital Concentration + Thesis Combination: High position weight (e.g. FPT 52.7% NAV) creates `POSITION_CONCENTRATION_REVIEW`, but `SELL`/`REDUCE` requires valid fundamental/permanent-loss evidence, reliable market risk evidence, or superior rotation target.
10. Rotation & Execution Safety: Block risk-based rotation and buy execution plans when market risk fit is `UNAVAILABLE`.
11. UI Agreement: Cross-page invariant: If `/risk` says "Chưa đủ dữ liệu toàn danh mục", `/allocation` MUST say "Portfolio fit: Chưa đủ dữ liệu" (not `GOOD`).
12. API Contract & Explainability: Expose `risk_context` (`data_status`, `actionable`, `eligible_nav_weight`, `eligible_symbols`, `missing_symbols`) and `fit_evidence_status` in `/allocation` API payloads.

## Context

When a portfolio has partial price history (e.g. FPT, ACB missing; only DGC eligible at 3.1% NAV), `/risk` reports `INSUFFICIENT` data. However, Allocation code paths previously evaluated `_current_fit()`, `_fit_for_proposed()`, `decide_holding()`, and `rotation_gates()` on the 3.1% NAV subset, resulting in false `GOOD` fit classifications or false risk-based `REDUCE` recommendations.

## Acceptance Criteria

- [x] `market_risk_actionable` exposed as `false` when coverage < 80% NAV or eligible symbols < 2.
- [x] `AllocationService._current_fit()` returns `UNAVAILABLE` when `market_risk_actionable` is `false`.
- [x] `_fit_for_proposed()` sets `risk_available = false` and `fit = UNAVAILABLE` under insufficient risk coverage.
- [x] `decide_holding()` gates risk-contribution `REDUCE` behind `market_risk_actionable == true`.
- [x] Candidates with unavailable market risk fit are routed to `WATCHLIST`, not `BUY_READY`.
- [x] Existing holdings with unavailable market risk default to `HOLD` / `REVIEW_REQUIRED` (never false `REDUCE`).
- [x] High capital concentration (e.g., >20% NAV) without price history creates a review warning, but `HOLD` remains intact if thesis is unbroken.
- [x] Permanent loss decision hierarchy strictly enforced (Thesis > Hard Reject > Quality > MOS > Concentration > Volatility).
- [x] `/allocation` UI displays "Chưa đủ dữ liệu" for portfolio fit when market risk is not actionable.
- [x] All 27 required regression tests pass without errors.
- [x] Frontend build succeeds.

## Constraints and Invariants

1. `UNKNOWN MARKET RISK != LOW RISK`. `UNKNOWN MARKET RISK != HIGH RISK`. `UNKNOWN MARKET RISK = UNAVAILABLE`.
2. `/risk` explains market evidence; `/allocation` acts ONLY on evidence that is sufficiently reliable (`market_risk_actionable == true`).
3. Capital concentration is holdings-derived and available regardless of price history, but does NOT masquerade as covariance market fit.
4. Expected Alpha and Kelly remain disabled.
5. No ledger mutation. Allocation remains advisory.

## Implementation Tasks

- [x] Add `market_risk_actionable` and centralize policy in `python/portfolio/risk.py`.
- [x] Update `python/portfolio/allocation/service.py`:
  - `_current_fit()` checks `market_risk_actionable`.
  - `decide_holding()` gates `risk_contribution` breach behind `market_risk_actionable`.
  - Expose structured `risk_context` in response payload.
- [x] Update `python/portfolio/allocation/opportunity.py` and `candidate_service.py`:
  - Gate candidate `BUY_READY` status on actionable market fit. Candidates with `UNAVAILABLE` fit route to `WATCHLIST`.
- [x] Update `python/portfolio/allocation/sizing.py`:
  - Ensure `UNAVAILABLE` fit does not invent synthetic multiplier or false target for existing holdings.
- [x] Update `python/portfolio/allocation/execution_planner.py`:
  - Block execution plan generation for candidates/holdings where action is blocked due to unavailable market risk.
- [x] Update `frontend/src/pages/AllocationPage.jsx`:
  - Render "Chưa đủ dữ liệu" for unavailable portfolio fit.
  - Display explicit risk context and concentration explanation cards.
- [x] Add comprehensive contract and decision integrity unit tests.
- [x] Run test suite and `npm run build`.

## Validation Evidence

Executed command:
```bash
python -m pytest -o pythonpath=python python/portfolio/tests/test_allocation_risk_gating.py python/portfolio/tests/test_allocation_service.py python/portfolio/tests/test_allocation_opportunity.py python/portfolio/tests/test_allocation_sizing.py python/portfolio/tests/test_allocation_candidate_tiers.py python/portfolio/tests/test_allocation_eligibility.py python/portfolio/tests/test_allocation_execution_planner.py python/portfolio/tests/test_risk_data_integrity.py python/portfolio/tests/test_permanent_loss_risk.py python/portfolio/tests/test_risk_warnings.py
```
Result: 176 passed in 2.00s.

Executed frontend build:
```bash
cd frontend && npm run build
```
Result: Build completed in 1.19s with 0 errors.

## Decisions

- **Governance Coverage Policy:** `MIN_MARKET_RISK_NAV_COVERAGE = 0.80`, `MIN_MARKET_RISK_SYMBOLS = 2`.
- **Decision Priority:** Permanent loss (Thesis / Quality / Balance Sheet) > Capital Concentration > Market Covariance.
- **Actionability Gate:** Partial market risk is diagnostic only. `market_risk_actionable == false` disables quantitative risk-based `REDUCE` and rotation.

## Result

Task completed successfully. `/risk` and `/allocation` are now strongly coupled through explicit risk usability contracts (`market_risk_actionable`). Allocation decisions never evaluate partial covariance metrics as if they represented the whole portfolio. All 176 backend tests pass and frontend build succeeds cleanly.
