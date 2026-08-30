# TASK-20260829-073: Fix Full-Cycle Mid-Cycle Normalization for Cyclical Enterprises (DGC, HPG, etc.)

- **ID**: `TASK-20260829-073`
- **Title**: Enable Direct 7–10Y Mid-Cycle Median Normalization when Revenue Fact is Absent
- **Status**: completed
- **Priority**: high
- **Date**: 2026-08-29
- **Assignee**: AI Agent & Quant Contributor

---

## Requirement
Fix the cycle-normalization engine so cyclical commodity stocks (like DGC - Hóa chất Đức Giang, HPG, DCM) with full 10-year historical financial data can calculate mid-cycle Owner Earnings and achieve `MODEL_VERIFIED` status:
1. **Root Cause Analysis**:
   - `OwnerEarningsCalculator.calculate_cycle_normalized` previously required `IS.REVENUE.NET` for every year to compute margin `margin_t = OE_t / Rev_t`.
   - When revenue line item was absent in canonical facts (as in DGC where only `IS.PROFIT.NET`, `IS.PROFIT.OPERATING` were stored), `calculate_cycle_normalized` discarded all 10 valid annual Owner Earnings bridges `[2016..2025]` and fell back to `normalization_years=1` (`LATEST_FY`).
   - The strict full-cycle gate in `engine.py` (which requires >=7 years for cyclical commodities) then marked DGC as `MODEL_INCOMPLETE` and hid the public Base IV / MOS (`—`).
2. **Fix**:
   - In `OwnerEarningsCalculator.calculate_cycle_normalized`, if revenue facts are available, use `median(margin) * median(revenue)`.
   - If revenue facts are absent but >= 3 annual Owner Earnings bridges exist, calculate mid-cycle OE directly as `median(oe_t)` across the lookback years (`MID_CYCLE_MEDIAN`).
   - Allow full 10-year cycle normalization (`normalization_years=10`, `normalization_method="MID_CYCLE_MEDIAN"`), satisfying the full-cycle gate and unlocking verified valuation for DGC.

---

## Acceptance Criteria
- [x] `OwnerEarningsCalculator.calculate_cycle_normalized` computes 10-year `MID_CYCLE_MEDIAN` when annual OE facts exist even if `IS.REVENUE.NET` is not present.
- [x] DGC achieves `MODEL_VERIFIED` with a verified Base IV, 3 scenarios, and Margin of Safety.
- [x] All unit tests pass.

---

## Implementation Tasks
- [x] Update `python/portfolio/value_engine/owner_earnings.py`.
- [x] Run test suite `pytest python/portfolio/tests/test_value_engine*.py`.
- [x] Sync/verify valuation endpoint for DGC.

---

## Validation Evidence
- `pytest python/portfolio/tests/test_value_engine*.py`: 34 passed in 0.75s.
- Verified DGC valuation:
  - `Model Status`: `MODEL_VERIFIED`
  - `Base Intrinsic Value`: `66,734 ₫`
  - `Margin of Safety`: `+35.6%` (với thị giá `43.000 ₫`)
  - `Bear IV`: `42,985 ₫` | `Bull IV`: `101,327 ₫`
  - `Cycle Normalization`: 10 năm (`MID_CYCLE_MEDIAN`).

---

## Result
- DGC and cyclical commodity enterprises now successfully utilize full 10-year mid-cycle normalization and display verified intrinsic values.

