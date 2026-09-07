# TASK-20260907-106: Add Deterministic Risk Warnings and Plain-Language Risk Interpretation

---
id: TASK-20260907-106
title: Add Deterministic Risk Warnings and Plain-Language Risk Interpretation
status: completed
priority: high
date: 2026-09-07
---

## Requirement

Introduce a deterministic Risk Warning and Plain-Language Risk Interpretation layer for the `/risk` page.
Transform raw quant risk metrics into clear, human-understandable warnings, reminders, risk interpretations, and review guidance answering:
1. What does the risk mean?
2. Why does it matter?
3. How severe is it?
4. What should be reviewed next?

## Context

The `/risk` page currently exposes raw metrics (volatility, VaR/CVaR, correlation, risk contribution, concentration, effective positions, sector concentration). Raw numbers are hard to digest for retail long-term investors.

Important boundaries:
- `/risk` remains diagnostic/advisory.
- `/risk` explains and warns; `/allocation` decides capital actions.
- `/risk` must NOT become the Allocation engine and must NOT output trade recommendations (`BUY_MORE`, `REDUCE`, `SELL`).
- `/risk` must NOT mutate the ledger.
- No AI/LLM is required; use deterministic rules based on canonical risk metrics.

## Acceptance Criteria

- [x] Deterministic Risk Warning Engine introduced in `python/portfolio/risk_warnings.py`.
- [x] Severity vocabulary: `NORMAL` (Bình thường), `ATTENTION` (Cần chú ý), `WARNING` (Cảnh báo), `HIGH_RISK` (Nguy cơ cao).
- [x] Warning Model Schema includes `id`, `category`, `severity`, `title`, `summary`, `metric_name`, `metric_value`, `threshold`, `affected_symbols`, `evidence`, `impact`, `review_guidance`, `reason_codes`.
- [x] Implement 10 Warning Categories:
  1. Position Concentration (`max_position_weight`)
  2. Risk Contribution Concentration (`largest_risk_contribution`)
  3. Correlation Cluster (high pairwise correlation >= 0.70)
  4. Low Effective Diversification (`effective_positions` vs nominal position count)
  5. Portfolio Volatility (`volatility_63` vs `volatility_252`)
  6. VaR / CVaR (statistically correct tail risk interpretation with explicit disclaimers)
  7. Worst Historical Day / Downside
  8. Sector Concentration
  9. Data Quality / Incomplete Analysis (`status == PARTIAL/UNAVAILABLE` or `missing_symbols`)
  10. Cash Concentration (neutral / informational)
- [x] Portfolio Risk Summary provided at top of API payload and UI (overall severity, headline, warning counts).
- [x] Deterministic priority ranking for warnings (Data Quality -> High Risk -> Warning -> Attention -> Informational).
- [x] Duplicate warning cards grouped/deduplicated (e.g. position concentration + risk contribution for same symbol combined into comprehensive evidence).
- [x] Primary plain Vietnamese human explanation + advanced metric technical details preserved.
- [x] `/risk` API response includes `risk_summary` and `warnings` array.
- [x] Redesigned `/risk` UI hierarchy: Summary -> Important Warnings -> Portfolio Concentration -> Diversification & Correlation -> Tail Risk -> Advanced Metrics.
- [x] Cross-link from Risk warnings to `/allocation` for simulation ("Xem tác động trong Phân bổ vốn").
- [x] Zero trade recommendation strings (`BUY`, `SELL`, `REDUCE`, `HOLD`, `BUY_MORE`) in Risk warning engine.
- [x] Architecture test verifying Risk Warning module depends on canonical risk metrics, but NOT on allocation or transaction execution modules.
- [x] Comprehensive unit, integration, and UI tests pass.

## Constraints and Invariants

1. Canonical risk metrics from `python/portfolio/risk.py` MUST be reused without recomputation.
2. VaR/CVaR MUST NEVER be described as a guaranteed maximum loss.
3. UNKNOWN data is NOT safe (`missing_symbols` produces `DATA_QUALITY` warning).
4. `/risk` explains & warns; `/allocation` decides capital actions.
5. Zero trade actions (`BUY`, `SELL`, `REDUCE`, `HOLD`, `BUY_MORE`) returned by Risk engine.
6. No ledger mutation.
7. Multi-portfolio isolation preserved.

## Implementation Tasks

- [x] Create `python/portfolio/risk_warnings.py` defining `RiskWarning` data structures, warning rules, priority ranking, and `generate_risk_warnings(risk_data, position_rows)`.
- [x] Integrate `risk_warnings` into `portfolio_risk()` in `python/portfolio/risk.py` and `PortfolioService.risk()` in `python/portfolio/service.py`.
- [x] Create unit tests in `python/portfolio/tests/test_risk_warnings.py` covering all 10 categories, severity thresholds, statistical phrasing, deduplication, and trade action exclusion.
- [x] Add architecture test in `python/portfolio/tests/test_risk_architecture.py`.
- [x] Update `frontend/src/pages/RiskPage.jsx` to render Risk Summary, Priority Warnings, Human Explanations, Impact, Review Guidance, and links to `/allocation`.
- [x] Verify unit tests and frontend build (`npm run build`).

## Related Notes

- [AGENTS.md](file:///c:/workspace/shannon_allocation/AGENTS.md)
- [BUY_AND_HOLD_SYSTEM_SPEC.md](file:///c:/workspace/shannon_allocation/BUY_AND_HOLD_SYSTEM_SPEC.md)
- [python/portfolio/risk.py](file:///c:/workspace/shannon_allocation/python/portfolio/risk.py)

## Validation Evidence

- Unit & Architecture Tests:
  `python -m pytest -o pythonpath=python python/portfolio/tests/test_risk_warnings.py python/portfolio/tests/test_risk_architecture.py python/portfolio/tests/test_risk_performance_depth_contract.py`
  Output: `19 passed in 0.77s`
- Frontend Build:
  `npm run build`
  Output: `built in 1.14s` with 0 errors.

## Decisions

- **Severity levels:** `NORMAL`, `ATTENTION`, `WARNING`, `HIGH_RISK`.
- **Backend-driven interpretation:** Backend generates warning cards so single semantic source of truth is maintained across API and frontend.
- **Grouping:** Group related warnings for a symbol (e.g. weight concentration + risk contribution) into a single high-priority warning card with rich evidence fields.

## Result

- Created `python/portfolio/risk_warnings.py` with 10 deterministic risk warning rules.
- Connected warning engine to `portfolio_risk()` in `python/portfolio/risk.py`.
- Added 14 unit and architecture tests in `test_risk_warnings.py` and `test_risk_architecture.py`.
- Redesigned `frontend/src/pages/RiskPage.jsx` with summary header, severity pills, risk warning cards, impact text, review guidance, and safe navigation to `/allocation`.
