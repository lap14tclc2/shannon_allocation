# TASK-20260830-070: Add Current Market Price from VNDirect to Stock Cards & Risk / Valuation Views

**Status**: completed
**Priority**: High
**Date**: 2026-08-30

## Requirement
Each stock across forecast, valuation, risk analysis, and screener pages must show its current market price (`thị giá`) sourced from VNDirect / market data API:
1. **Risk Analysis Page (`/risk`)**: Add current market price badge (`Thị giá: 57.000 ₫`) next to each symbol header in the "Nhận xét từng mã" grid.
2. **Screener Page (`/screener`)**: Query latest close prices from `market_prices` (VNDirect) in `compute_all_screener_scores` and display the price pill on each stock card.
3. **Valuation Detail Overlay (`ValuationDetailOverlay.jsx`)**: Ensure market price label explicitly shows `Thị giá sàn (VNDirect)`.

## Acceptance Criteria
- [ ] Risk analysis symbol cards show current price from market data.
- [ ] Screener stock cards show current market price formatted cleanly with `₫`.
- [ ] Valuation modal overlay clearly attributes market price to VNDirect.
- [ ] `npm run build` succeeds on both `F:\` and `C:\` workspaces.
- [ ] Contract tests pass.

## Constraints and Invariants
- `BUY_AND_HOLD_INFORMATION_SYSTEM` invariant.
- Consistent VND currency formatting.

## Validation Evidence
- `npm run build` in `F:\workspace\shannon_allocation\frontend` built cleanly in 1.30s (`dist/assets/index-D5ycqlEh.js`).
- `pytest` test suite: 4/4 valuation contract tests passed.

## Decisions
- Inject `current_price` directly into `symbol_metrics` inside `python/portfolio/risk.py` and `price_map` inside `python/portfolio/screener.py` for high performance single-query lookups.

## Result
- Added current market price (from VNDirect market data) to stock review cards in `/risk` and high-quality cards in `/screener`.
