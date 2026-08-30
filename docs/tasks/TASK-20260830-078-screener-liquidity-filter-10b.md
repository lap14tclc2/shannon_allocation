# TASK-20260830-078: Screener Liquidity Filter (>= 10 Billion VND / Day)

**Status**: in-progress
**Priority**: High
**Date**: 2026-08-30

## Requirement
Add 20-day average liquidity (Giá trị giao dịch trung bình 20 phiên) calculation & filter to Screener (`/screener`):
1. **Backend (`python/portfolio/screener.py`)**:
   - Calculate 20-day average turnover in billion VND (`avg_turnover_20d_billion`) and 20-day volume (`avg_volume_20d`) for all stocks.
   - Add `min_liquidity` parameter:
     - `10`: `≥ 10 Tỷ / ngày` (Thanh khoản cao - Loại bỏ cổ phiếu kém thanh khoản).
     - `5`: `≥ 5 Tỷ / ngày` (Thanh khoản khá).
     - `1`: `≥ 1 Tỷ / ngày` (Thanh khoản vừa).
     - `0`: `Tất cả thanh khoản`.
   - Default `min_liquidity=10` or provide intuitive segmented filter.
2. **Frontend (`frontend/src/pages/ScreenerPage.jsx`)**:
   - Add Liquidity Filter row with segmented options (`≥ 10 Tỷ/ngày`, `≥ 5 Tỷ/ngày`, `≥ 1 Tỷ/ngày`, `Tất cả`).
   - Display **Thanh khoản TB (20D)** directly on stock cards (e.g. `462,4 tỷ/ngày`, `23,3 tỷ/ngày`).
3. **Build & Verify**:
   - Verify that all tests pass and both workspaces are updated.

## Acceptance Criteria
- [ ] Screener filters stocks by 20-day average turnover >= 10B/day.
- [ ] Stock cards display 20-day average liquidity value.
- [ ] User can switch liquidity filter between 10B, 5B, 1B, All.
- [ ] Contract tests and builds pass.

## Constraints and Invariants
- `BUY_AND_HOLD_INFORMATION_SYSTEM` invariant.
- Theme tokens synchronization.

## Validation Evidence
*To be filled.*

## Decisions
- Use 20-day trading average (1 month) turnover to provide robust, non-manipulated liquidity filtering.

## Result
*To be filled.*
