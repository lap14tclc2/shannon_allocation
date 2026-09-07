# TASK-20260907-112: Finalize Risk Semantics and Gate Allocation on Reliable Market-Risk Evidence

---
id: TASK-20260907-112
title: Finalize Risk Semantics and Gate Allocation on Reliable Market-Risk Evidence
status: completed
priority: high
date: 2026-09-07
---

## Requirement

Complete the remaining `/risk` semantic hardening and ensure `/allocation` consumes the corrected risk contract safely without relying on partial market risk data:
1. Fix DGC Headline Scope: Replace "100.0% tổng biến động danh mục" with "100.0% biến động trong phần danh mục có đủ dữ liệu" when market risk coverage is partial.
2. Remove UNKNOWN -> 0 Copy: Never show 0.0% risk contribution for symbols with insufficient price history (e.g. FPT 52.7% NAV). Show "Chưa đủ dữ liệu để tính đóng góp biến động." (UNKNOWN != ZERO).
3. Fix Effective-N Interpretation: Label `effective_positions` as "Số vị thế hiệu dụng theo tỷ trọng" and explain concentration without stating or implying "independent positions", correlation, or covariance.
4. Fix Concentration Impact Copy: When risk data is partial, explain concentration as "Mức tập trung vốn cao khiến kết quả danh mục phụ thuộc nhiều vào một số ít vị thế."
5. Scope Diversification Ratio & RC-HHI: Hide `diversification_ratio` and `risk_contribution_hhi` from main summary when `market_risk_actionable` is `false`.
6. Moat Trend Evidence: Set `moat_trend = "UNKNOWN"` ("Chưa đủ dữ liệu xu hướng") unless multi-period evidence exists. Do not infer `STABLE` from absence of deterioration evidence in a snapshot.
7. Specific Permanent-Loss Summary: Separate financial safety (balance sheet) and valuation safety (MOS) into distinct concerns instead of merged vague phrases.
8. Enforce Market Risk Usability Contract: Gate all quantitative risk-based allocation actions behind `market_risk_actionable == true`.

## Context

Previous iterations improved `/risk` status disclosures and separated permanent capital loss risk from market volatility. However, minor semantic inconsistencies remained in warning summaries, moat trend fallbacks, and effective position copy, while Allocation required strict enforcement of `market_risk_actionable` across all decision paths.

## Acceptance Criteria

- [x] DGC warning headline uses "100.0% biến động trong phần danh mục có đủ dữ liệu" under partial coverage.
- [x] Symbols missing price history (e.g. FPT) state "Chưa đủ dữ liệu để tính đóng góp biến động" instead of 0.0%.
- [x] `effective_positions` text describes "Số vị thế hiệu dụng theo tỷ trọng" with zero reference to "independent positions".
- [x] Concentration impact copy under partial data states "kết quả danh mục phụ thuộc nhiều vào một số ít vị thế".
- [x] `diversification_ratio` and `risk_contribution_hhi` are `None` when `market_risk_actionable` is `false`.
- [x] `moat_trend` defaults to `UNKNOWN` without multi-period evidence.
- [x] Permanent loss top concerns clearly separate balance sheet and valuation MOS.
- [x] Partial market risk cannot trigger risk-based `REDUCE`, risk caps, rotation, or candidate `BUY_READY` status.
- [x] All unit and integration tests pass cleanly.
- [x] Frontend build succeeds.

## Constraints and Invariants

1. `UNKNOWN MARKET RISK != ZERO`. `UNKNOWN MARKET RISK != LOW`. `UNKNOWN MARKET RISK = UNAVAILABLE`.
2. `/risk` explains evidence; `/allocation` acts ONLY on evidence that is sufficiently reliable (`market_risk_actionable == true`).
3. Capital concentration is holdings-derived and available regardless of price history, but does NOT masquerade as market covariance fit.
4. No ledger mutation. Advisory only.

## Implementation Tasks

- [x] Update `python/portfolio/risk_warnings.py`:
  - Fix DGC headline scope for partial risk coverage.
  - Fix UNKNOWN -> 0.0% formatting for missing risk contributions.
  - Fix concentration impact copy and effective positions wording.
- [x] Update `python/portfolio/risk.py`:
  - Suppress `diversification_ratio` and `risk_contribution_hhi` when coverage is incomplete.
  - Ensure `symbol_risk` explanations format partial and missing contributions correctly.
- [x] Update `python/portfolio/permanent_loss_risk.py`:
  - Require temporal evidence for `moat_trend == STABLE` (default to `UNKNOWN` otherwise).
  - Separate balance sheet and valuation MOS in concern summaries.
- [x] Verify `python/portfolio/allocation/service.py`, `opportunity.py`, `candidate_service.py`, and `sizing.py` enforce `market_risk_actionable`.
- [x] Run backend test suite.
- [x] Run `cd frontend && npm run build`.

## Validation Evidence

Executed command:
```bash
python -m pytest -o pythonpath=python python/portfolio/tests/test_allocation_risk_gating.py python/portfolio/tests/test_allocation_service.py python/portfolio/tests/test_allocation_opportunity.py python/portfolio/tests/test_allocation_sizing.py python/portfolio/tests/test_allocation_candidate_tiers.py python/portfolio/tests/test_allocation_eligibility.py python/portfolio/tests/test_allocation_execution_planner.py python/portfolio/tests/test_risk_data_integrity.py python/portfolio/tests/test_permanent_loss_risk.py python/portfolio/tests/test_risk_warnings.py
```
Result: 181 passed in 1.76s.

Executed frontend build:
```bash
cd frontend && npm run build
```
Result: Build completed in 1.16s with 0 errors.

## Decisions

- **Moat Trend:** Snapshot only yields `moat_strength`; `moat_trend` requires temporal evidence, defaulting to `UNKNOWN`.
- **Warning Semantics:** Partial risk contribution must state "biến động trong phần danh mục có đủ dữ liệu". Missing history must state "Chưa đủ dữ liệu".
- **Actionability Gate:** `market_risk_actionable == false` suppresses covariance-based actions while preserving capital concentration diagnostics.

## Result

Task completed successfully. `/risk` semantics are fully hardened, removing misleading full-portfolio claims under partial coverage, and `/allocation` is strictly gated on reliable market-risk evidence. All 181 backend tests pass and frontend build succeeds.
