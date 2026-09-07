# TASK-20260907-110: Fix Risk Data Contract Semantics and Evidence

---
id: TASK-20260907-110
title: Fix Risk Data Contract Semantics and Evidence
status: completed
priority: high
date: 2026-09-07
---

## Requirement

Perform a comprehensive audit and overhaul of `/risk` backend API data contracts and frontend rendering for semantic correctness and data integrity:
1. Data Status Overrides Market Risk: Separate `data_status` (`INSUFFICIENT`, `PARTIAL`, `COMPLETE`) from `risk_severity`. When coverage is insufficient, top market risk status must be `INSUFFICIENT_DATA` ("Chưa đủ dữ liệu"), NOT "Nguy cơ cao" or "Bình thường". Concentration severity is displayed separately.
2. Unknown Must Stay Null: Ineligible symbols must have `risk_contribution = null` (NOT `0` or `0.00%`). UI displays "Chưa tính được". Invariant: `UNKNOWN != ZERO`.
3. Contribution Scope: Introduce `risk_contribution_scope` (`FULL_PORTFOLIO`, `ELIGIBLE_UNIVERSE_ONLY`, `UNAVAILABLE`). Qualify 100% single-eligible symbol as 100% of eligible universe, never full portfolio.
4. Suppress Portfolio VaR/CVaR: When coverage is insufficient/partial, portfolio-level `daily_var_95`, `daily_cvar_95`, `downside_volatility` must be `null` in payload. UI shows "Chưa đủ dữ liệu toàn danh mục".
5. Coverage Policy Centralization: Explicit coverage thresholds (`MIN_PORTFOLIO_RISK_NAV_COVERAGE = 0.50` / `0.80`, `MIN_PORTFOLIO_RISK_SYMBOLS = 2`). Expose coverage fields cleanly in API payload.
6. Effective Positions Semantic: Rename HHI-based effective positions to "Số vị thế hiệu dụng theo tỷ trọng". Warning under insufficient correlation data rephrased to "Tập trung vốn cao".
7. Solvency Source of Truth: Remove "Reject: Solvency" from diagnostic score components. Solvency hard reject used only when `SOLVENCY_RISK` is in canonical `hard_rejects`. Add invariant test.
8. Moat Strength vs Moat Trend: Refactor moat into `moat_strength` (`STRONG`, `MODERATE`, `WEAK`, `UNKNOWN`) and `moat_trend` (`IMPROVING`, `STABLE`, `DETERIORATING`, `UNKNOWN`). Require multi-period evidence for `DETERIORATING`.
9. Evidence Strength: Expose `status`, `evidence`, `evidence_strength` (`CONFIRMED`, `INDICATIVE`, `INSUFFICIENT`) for every permanent loss dimension.
10. Permanent Loss Summary Separation: Do not combine unrelated concerns. Expose individual dimension states cleanly.

## Context

Detailed audit revealed release-blocking semantic bugs in `/risk`:
- Top market-risk summary assigned `HIGH_RISK` ("Nguy cơ cao") when coverage was only 3.1% NAV.
- Missing history symbols (FPT/ACB) exposed `risk_contribution = 0.00%` instead of `null`.
- Portfolio VaR/CVaR/Downside volatility computed on 3.1% NAV sub-universe and reported as full portfolio metrics.
- Effective positions described as "independent positions" despite correlation data being missing.
- "Reject: Solvency" displayed alongside "no solvency violation" due to mixing low financial strength scores with hard rejects.
- Snapshot moat score of 7/100 reported as "Moat deteriorating" without temporal multi-period evidence.

## Acceptance Criteria

- [x] `data_status` overrides market-risk severity. Insufficient coverage forces top status to `INSUFFICIENT_DATA` ("Chưa đủ dữ liệu").
- [x] Ineligible symbol `risk_contribution` is `null` (never `0.0` or `0.00%`). UI displays "Chưa tính được".
- [x] `risk_contribution_scope` (`FULL_PORTFOLIO`, `ELIGIBLE_UNIVERSE_ONLY`, `UNAVAILABLE`) exposed and reflected in UI copy.
- [x] Portfolio VaR, CVaR, downside volatility set to `null` when portfolio coverage is insufficient. UI displays "Chưa đủ dữ liệu toàn danh mục".
- [x] Centralized coverage thresholds defined and exposed.
- [x] Effective positions renamed to "Số vị thế hiệu dụng theo tỷ trọng". Warning rephrased to "Tập trung vốn cao".
- [x] "Reject: Solvency" string removed from non-reject subscore output. Hard reject invariant tested.
- [x] Moat split into `moat_strength` and `moat_trend`. Single snapshot score yields `moat_trend = UNKNOWN`.
- [x] Evidence strength exposed for each permanent loss dimension.
- [x] Permanent loss concerns separated into individual dimensions.
- [x] All 21 required regression unit, integration, contract, and frontend tests pass.

## Constraints and Invariants

1. Single canonical weight denominator (NAV weight).
2. `UNKNOWN` risk contribution is `null`, never `0.0` or `0.00%`.
3. `UNKNOWN` correlation is `null`, never `0.35` or `0.0`.
4. `UNKNOWN` moat trend is `UNKNOWN`, never `DETERIORATING` without multi-period evidence.
5. `SOLVENCY_RISK` in `hard_rejects` invariant strictly maintained.
6. No ledger mutation. `/risk` remains advisory.

## Implementation Tasks

- [x] Centralize coverage policy in `python/portfolio/risk.py`.
- [x] Update `portfolio_risk` to set top market risk status to `INSUFFICIENT_DATA` when coverage is insufficient, separate concentration severity from volatility severity.
- [x] Update symbol metrics to set `risk_contribution = None` and `risk_contribution_scope = "UNAVAILABLE"` for ineligible symbols.
- [x] Set `risk_contribution_scope = "ELIGIBLE_UNIVERSE_ONLY"` for single eligible symbol.
- [x] Suppress portfolio-level `daily_var_95`, `daily_cvar_95`, `downside_volatility` when coverage is insufficient/partial.
- [x] Update `generate_risk_warnings` in `python/portfolio/risk_warnings.py` to rephrase effective positions warning under insufficient correlation data to "Tập trung vốn cao".
- [x] Refactor `python/portfolio/permanent_loss_risk.py`:
  - Split moat into `moat_strength` and `moat_trend`.
  - Remove "Reject: Solvency" label from non-reject subscore evidence.
  - Expose `evidence_strength` per dimension.
- [x] Update `frontend/src/pages/RiskPage.jsx` to render `null` risk contribution as "Chưa tính được", qualified contribution copy, suppressed VaR/CVaR, separated moat strength/trend, and clean market risk banner.
- [x] Add 21 regression unit & contract tests in `python/portfolio/tests/test_risk_data_integrity.py`.
- [x] Run full test suite and frontend build (`npm run build`).

## Related Notes

- [AGENTS.md](file:///c:/workspace/shannon_allocation/AGENTS.md)
- [BUY_AND_HOLD_SYSTEM_SPEC.md](file:///c:/workspace/shannon_allocation/BUY_AND_HOLD_SYSTEM_SPEC.md)
- [python/portfolio/risk.py](file:///c:/workspace/shannon_allocation/python/portfolio/risk.py)
- [python/portfolio/risk_warnings.py](file:///c:/workspace/shannon_allocation/python/portfolio/risk_warnings.py)
- [python/portfolio/permanent_loss_risk.py](file:///c:/workspace/shannon_allocation/python/portfolio/permanent_loss_risk.py)
- [frontend/src/pages/RiskPage.jsx](file:///c:/workspace/shannon_allocation/frontend/src/pages/RiskPage.jsx)

## Validation Evidence

Executed test suite:
- `python -m pytest -o pythonpath=python python/portfolio/tests/test_risk_data_integrity.py python/portfolio/tests/test_permanent_loss_risk.py python/portfolio/tests/test_risk_warnings.py python/portfolio/tests/test_risk_architecture.py python/portfolio/tests/test_risk_performance_depth_contract.py python/portfolio/tests/test_risk_summary_contract.py`
  Result: 61 passed, 0 failed in 1.19s.
- `cd frontend && npm run build`
  Result: `built in 1.09s` with zero errors.

## Decisions

- **Data Status Override:** `risk_coverage_status == 'INSUFFICIENT'` overrides market risk severity to `INSUFFICIENT_DATA` ("Chưa đủ dữ liệu"). Concentration severity remains independent.
- **Null Invariants:** Ineligible risk contribution is `null`. Portfolio VaR/CVaR under incomplete coverage is `null`.
- **Moat Dimensions:** Single score gives `moat_strength`, `moat_trend` requires temporal multi-period evidence.

## Result

All 21 hard requirements implemented and verified. Both backend API payloads and frontend rendering reflect semantically correct data contracts.
