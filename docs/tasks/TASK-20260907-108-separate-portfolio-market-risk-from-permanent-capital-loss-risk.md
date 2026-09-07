# TASK-20260907-108: Separate Portfolio Market Risk from Permanent Capital Loss Risk

---
id: TASK-20260907-108
title: Separate Portfolio Market Risk from Permanent Capital Loss Risk
status: completed
priority: high
date: 2026-09-07
---

## Requirement

Redesign the `/risk` module to explicitly separate Portfolio Market Risk (volatility, correlation, risk contribution, VaR/CVaR, concentration, diversification) from Permanent Capital Loss Risk (business quality deterioration, balance sheet safety, earnings durability, moat/competitive position, capital allocation quality, valuation margin of safety, thesis status, data confidence).

Key Requirements:
1. Maintain canonical quantitative market risk metrics without removal.
2. Clarify risk contribution semantics as "Đóng góp vào biến động danh mục", NOT "Rủi ro doanh nghiệp".
3. High volatility or high risk contribution alone MUST NOT trigger business-risk warnings or trade execution recommendations (`BUY`, `SELL`, `REDUCE`).
4. Introduce deterministic `PermanentCapitalLossRisk` / `BusinessRiskAssessment` layer reusing canonical value-engine evidence without inventing unvalidated AI scores.
5. Dimensions for permanent capital loss risk:
   - `BUSINESS_QUALITY`
   - `BALANCE_SHEET`
   - `EARNINGS_DURABILITY`
   - `MOAT`
   - `CAPITAL_ALLOCATION`
   - `VALUATION`
   - `THESIS_DETERIORATION`
   - `DATA_CONFIDENCE`
6. Thesis deterioration statuses: `INTACT`, `WATCH`, `DETERIORATING`, `BROKEN`, `UNKNOWN`. Stock price decline alone is NOT a thesis break.
7. Data confidence: Missing data returns `UNKNOWN` / `REVIEW_REQUIRED` (UNKNOWN != SAFE).
8. Categorical severity for permanent-loss risk: `LOW`, `MODERATE`, `ELEVATED`, `HIGH`, `UNKNOWN` (Vietnamese: `Thấp`, `Trung bình`, `Đáng chú ý`, `Cao`, `Chưa đủ dữ liệu`). No arbitrary 0-100 composite score mixing market volatility with quality/valuation.
9. Redesign `/risk` UI and API output to structurally separate Market/Portfolio Risk from Permanent Capital Loss Risk into two distinct sections.
10. Surface `CONCENTRATED_THESIS_RISK` warning and simple position stress scenario (-20%, -30%, -50% hypothetical shock) for large positions (>= 20% NAV) clearly labeled as "Kịch bản giả định".
11. Strict warning copy qualification: never say "Rủi ro cao" without specifying the exact risk type ("Biến động cao", "Rủi ro tập trung cao", "Rủi ro bảng cân đối cao", "Rủi ro thesis tăng", "Rủi ro định giá cao").

## Context

In Buffett/Munger value investing philosophy:
- Market volatility / NAV fluctuation is NOT permanent capital loss risk.
- DGC holding 42.2% NAV with 59.5% risk contribution means DGC is the main driver of portfolio volatility, not that DGC is a bad company or must be sold.
- Permanent capital loss occurs when business quality structurally decays, balance sheet becomes unsafe, moat erodes, management destroys value, or investment thesis breaks.

## Acceptance Criteria

- [x] Structurally separate `/risk` backend response into `market_risk` and `permanent_loss_risk`.
- [x] Create `python/portfolio/permanent_loss_risk.py` providing deterministic business risk assessment.
- [x] Implement explicit severity precedence:
  - Thesis break or Solvency hard reject => `HIGH`
  - Quality deterioration + valuation weak => `ELEVATED`
  - Strong business + robust balance sheet + valuation adequate => `LOW` / `MODERATE`
  - Data insufficient => `UNKNOWN`
- [x] Correctly handle bank-specific balance sheet rules (CAMEL/NPL/CASA) without applying industrial debt rules to banks.
- [x] Cyclical businesses (e.g. DGC) evaluated with cyclical earnings durability (moderate permanent loss risk, high volatility).
- [x] Price decline alone does NOT break thesis.
- [x] High risk contribution / volatility does NOT generate business risk warnings or SELL recommendations.
- [x] Add `CONCENTRATED_THESIS_RISK` warning and exposure stress simulation (-20%, -30%, -50% shock, labeled "Kịch bản giả định").
- [x] Qualified UI warning text (e.g. "Biến động cao", "Rủi ro tập trung cao", "Rủi ro bảng cân đối cao").
- [x] Redesign `frontend/src/pages/RiskPage.jsx` into TWO distinct sections (Biến động & Tập trung vs Rủi ro mất vốn vĩnh viễn) with top summary cards for both.
- [x] Zero trade recommendations returned by `/risk`.
- [x] No ledger mutation.
- [x] Unit, integration, architecture, and frontend build tests pass.

## Constraints and Invariants

1. Reuses canonical risk math from `python/portfolio/risk.py` and value-engine outputs without recomputing math.
2. No composite score adding volatility + quality + valuation.
3. `/risk` is diagnostic only; capital actions stay in `/allocation`.
4. Ledger remains immutable.
5. Vietnamese UI terminology strictly enforced.

## Implementation Tasks

- [x] Create `python/portfolio/permanent_loss_risk.py`.
- [x] Update `python/portfolio/risk_warnings.py` to ensure risk warnings explicitly qualify market risk vs permanent loss risk and include `CONCENTRATED_THESIS_RISK`.
- [x] Update `portfolio_risk()` in `python/portfolio/risk.py` and `PortfolioService.risk()` in `python/portfolio/service.py` to integrate permanent loss risk model.
- [x] Redesign `frontend/src/pages/RiskPage.jsx` and related components/styles to present two distinct sections.
- [x] Add tests in `python/portfolio/tests/test_permanent_loss_risk.py` covering all mandatory test requirements (16 test cases).
- [x] Verify frontend build (`npm run build`).

## Related Notes

- [AGENTS.md](file:///c:/workspace/shannon_allocation/AGENTS.md)
- [BUY_AND_HOLD_SYSTEM_SPEC.md](file:///c:/workspace/shannon_allocation/BUY_AND_HOLD_SYSTEM_SPEC.md)
- [docs/QPORT_BUFFETT_THORP_SYSTEM_PLAN.md](file:///c:/workspace/shannon_allocation/docs/QPORT_BUFFETT_THORP_SYSTEM_PLAN.md)
- [python/portfolio/risk.py](file:///c:/workspace/shannon_allocation/python/portfolio/risk.py)
- [python/portfolio/risk_warnings.py](file:///c:/workspace/shannon_allocation/python/portfolio/risk_warnings.py)

## Validation Evidence

- Python unit & architecture tests:
  `python -m pytest -o pythonpath=python python/portfolio/tests/test_permanent_loss_risk.py python/portfolio/tests/test_risk_warnings.py python/portfolio/tests/test_risk_architecture.py python/portfolio/tests/test_allocation_architecture.py python/portfolio/tests/test_risk_performance_depth_contract.py`
  Output: `50 passed in 0.94s`
- Frontend build:
  `cd frontend && npm run build`
  Output: `✓ built in 1.25s` with 0 errors.

## Decisions

- **Structural Separation:** API payload returns top-level `market_risk` and `permanent_loss_risk` plus `symbol_risk` detailing per-symbol market risk and permanent loss risk metrics.
- **No Composite Score:** Overall permanent loss severity is derived using explicit rule precedence (Thesis Break / Solvency -> HIGH; Quality Deterioration -> ELEVATED; Safe -> LOW/MODERATE; Missing -> UNKNOWN).

## Result

- Created `python/portfolio/permanent_loss_risk.py` implementing 8 fundamental risk dimensions.
- Updated `python/portfolio/risk.py` and `python/portfolio/service.py` to provide separated `market_risk` and `permanent_loss_risk` structure.
- Updated `python/portfolio/risk_warnings.py` to qualify warnings and explain risk contribution semantics.
- Redesigned `frontend/src/pages/RiskPage.jsx` into two clear sections: "Biến động & Tập trung Danh mục" and "Rủi ro Mất vốn Vĩnh viễn".
- Added 16 unit tests in `python/portfolio/tests/test_permanent_loss_risk.py`.
- 50 risk & allocation tests passed and frontend build succeeded.
