# TASK-20260830-076: Screener Filter & Sorting by Buffett Margin of Safety

**Status**: in-progress
**Priority**: High
**Date**: 2026-08-30

## Requirement
Transform the Screener (`/screener`) from a raw 100-point score filter to a **Buffett Margin of Safety (Biên An Toàn) First** screener:
1. **Backend (`python/portfolio/screener.py`)**:
   - Compute Intrinsic Value, Margin of Safety (MOS), Required MOS, and Valuation Status for all symbols in the universe.
   - Add `mos_filter` parameter:
     - `buffett_qualified`: Only stocks with MOS >= Required MOS (e.g. >= 20%-25%).
     - `positive`: Only stocks with MOS > 0% (Trading below intrinsic value).
     - `undervalued`: Deep value & Undervalued stocks.
     - `all`: All stocks regardless of MOS.
   - Default sort to `mos` (Margin of Safety: High -> Low).
2. **Frontend (`frontend/src/pages/ScreenerPage.jsx`)**:
   - Replace primary filter from Score to **Biên An Toàn Buffett** (`Đạt chuẩn bảo vệ vốn`, `Biên an toàn dương > 0%`, `Định giá hấp dẫn`, `Tất cả`).
   - Highlight **Biên An Toàn MOS (+X.X%)**, **Thị giá** vs **Giá trị Thực** on stock cards.
   - Update header copy to reflect Buffett's Rule #1 ("Never lose money", Margin of Safety first).

## Acceptance Criteria
- [ ] Screener filters by Margin of Safety by default (stocks with positive / qualified MOS).
- [ ] Cards display prominent Margin of Safety badge, Market Price vs Intrinsic Value.
- [ ] Filter by MOS options work smoothly.
- [ ] Sorting by MOS (High -> Low) works.
- [ ] Contract tests and builds pass.

## Constraints and Invariants
- `BUY_AND_HOLD_INFORMATION_SYSTEM` invariant.
- Theme tokens synchronization.

## Validation Evidence
*To be filled.*

## Decisions
- Evaluate valuation for screened stocks using canonical facts and market prices to produce deterministic MOS.

## Result
*To be filled.*
