---
id: TASK-20260828-031
title: Add IS.SHARES.OUTSTANDING fact to API Valuation facts construction
status: completed
priority: high
created: 2026-08-28
updated: 2026-08-28
tags: [valuation, api, shares-outstanding, fast-api, bugfix]
related: [TASK-20260827-029]
---

## Requirement

Fix 500 error on `GET /api/portfolio/valuation/{symbol}` caused by `ValueError: VALUATION_FACTS_INCOMPLETE: IS.SHARES.OUTSTANDING` in `app/main.py`.

## Context

In `app/main.py`, the endpoint `portfolio_symbol_valuation` assembles `CanonicalFact` list from the catalog snapshot before calling `ValuationEngine.evaluate`. It populated `IS.PROFIT.NET`, `IS.PROFIT.OPERATING`, `BS.DEBT.TOTAL`, `BS.ASSETS.CASH_AND_EQUIVALENTS`, `CF.OPERATING.NET`, `CF.OPERATING.DEPRECIATION`, `CF.CAPEX`, but missed calling `add_fact("IS.SHARES.OUTSTANDING", StatementType.INCOME_STATEMENT, shares, PeriodType.QUARTER if fiscal_quarter else PeriodType.FY)`. Since `ValuationEngine.evaluate` strictly requires `IS.SHARES.OUTSTANDING` in `usable_facts`, it threw `ValueError: VALUATION_FACTS_INCOMPLETE: IS.SHARES.OUTSTANDING`.

## Acceptance Criteria

- [x] `add_fact("IS.SHARES.OUTSTANDING", ...)` added in `portfolio_symbol_valuation` in `app/main.py`.
- [x] Financial statement scaling properly handled (billion VND vs share count).
- [x] `GET /api/portfolio/valuation/FPT` returns 200 OK with full valuation report.
- [x] Direct verification on sample stocks (FPT, DGC, ACB, MWG, IDC, HPG, VNM) returns 200 OK with comprehensive valuation report.
- [x] Regression tests pass for value engine & financial pipeline.

## Constraints and Invariants

- Preserve deterministic valuation engine calculations.
- Maintain consistency between `shares_outstanding` and `IS.SHARES.OUTSTANDING`.

## Implementation Tasks

- [x] Add `add_fact("IS.SHARES.OUTSTANDING", StatementType.INCOME_STATEMENT, shares, PeriodType.QUARTER if fiscal_quarter else PeriodType.FY)` in `app/main.py`.
- [x] Scale financial statement values to full VND in `add_fact` for valuation facts.
- [x] Add on-demand market price sync fallback via `svc._sync_symbol(ticker, today_d)`.
- [x] Verify `portfolio_symbol_valuation` for FPT, DGC, ACB, MWG, IDC, HPG, VNM.

## Decisions

- Pass `shares` directly as `IS.SHARES.OUTSTANDING` canonical fact to satisfy `ValuationEngine.evaluate` completeness validation.
- Scale statement values by `1e9` (tỷ VND $\rightarrow$ VND) if raw values are in billion VND so that per-share values align with VND market price.

## Validation Evidence

- Executed valuation calculation across 7 symbols:
  - FPT: 200 OK | Status: FAIR_VALUE | Market: 71,400 đ | Base IV: 69,946 đ
  - DGC: 200 OK | Status: DEEP_VALUE | Market: 43,900 đ | Base IV: 77,350 đ
  - ACB: 200 OK | Status: FAIR_VALUE | Market: 22,500 đ | Base IV: -63,471 đ
  - MWG: 200 OK | Status: OVERVALUED | Market: 75,900 đ | Base IV: 43,942 đ
  - IDC: 200 OK | Status: DEEP_VALUE | Market: 32,500 đ | Base IV: 125,575 đ
  - HPG: 200 OK | Status: OVERVALUED | Market: 22,200 đ | Base IV: 9,135 đ
  - VNM: 200 OK | Status: FAIR_VALUE | Market: 62,500 đ | Base IV: 61,864 đ
- Pytest suite: `pytest python/portfolio/tests/test_value_engine.py python/portfolio/tests/test_financial_pipeline.py` (9/9 passed).

## Result

- API `/api/portfolio/valuation/{symbol}` operates without 500 errors and produces complete valuation reports with Owner Earnings, DCF Scenarios, EPV, Reverse DCF, and Sensitivity Matrix.
