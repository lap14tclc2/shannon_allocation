# Task: Fix VEA Valuation 500 Error and Sector Warning Box CSS Styling

- **ID**: `TASK-20260829-053`
- **Title**: Fix VEA Valuation 500 Error, Holding Company SOTP & Sector Warning Box CSS
- **Status**: `completed`
- **Priority**: `high`
- **Date**: `2026-08-29`

## Requirement
1. **Fix VEA Valuation 500 Internal Server Error**:
   - Classify VEA as `HOLDING_COMPANY` with `SOTP` model (major joint ventures: Toyota ~30%, Honda ~20%, Ford ~25%).
   - Add VEA components in `SOTPValuationModel`.
   - Prevent `OWNER_EARNINGS_NON_POSITIVE` from throwing unhandled `ValueError` 500 in `engine.py` and `app/main.py` (gracefully return `UNVALUABLE` report or 422 JSON response).
2. **Fix Broken CSS in Sector Warning Box**:
   - Replace `.opinion-finhealth` reuse with dedicated `.opinion-sector-warning` class.
   - Eliminate dashed border touching / overlapping and provide proper padding and spacing.

## Acceptance Criteria
- [x] `GET /api/portfolio/valuation/VEA` returns 200 OK with valid SOTP valuation report.
- [x] CSS for sector conflict warning box renders with clean padding, left border, and no dashed line collision.
- [x] All unit and contract tests pass (`pytest`).
- [x] Frontend build succeeds (`npm run build`).

## Validation Evidence
- `GET /api/portfolio/valuation/VEA` trả về 200 OK với SOTP breakdown gồm 4 cấu phần (Honda 20%, Toyota 30%, Ford 25%, Cơ khí VEAM Mẹ) và Base IV 36,891 ₫.
- Đã tách biệt class CSS `.opinion-sector-warning` trong `valuation-page.css`, khắc phục triệt để lỗi đường viền nét đứt đè lên hộp cảnh báo.
- `pytest python/portfolio/tests/test_buffett_munger_rule_engine.py python/portfolio/tests/test_value_engine.py python/portfolio/tests/test_value_engine_audit_fixes.py python/portfolio/tests/test_vi_labels.py python/portfolio/tests/test_valuation_page_contract.py -v`: 29/29 tests passed (100%).
- `npm --prefix frontend run build`: 102 modules biên dịch thành công.

## Decisions
- Thêm `VEA` vào `EXPLICIT_SYMBOL_ARCHETYPES` với `EconomicArchetype.HOLDING_COMPANY` và mô hình `SOTP`.
- Xây dựng cấu phần SOTP chuyên biệt cho VEA dựa trên 3 liên doanh ô tô - xe máy hàng đầu (Toyota, Honda, Ford) và khấu trừ Nợ vay ròng.
- Bổ sung class CSS `.opinion-sector-warning` trong `valuation-page.css` để tách biệt hoàn toàn với `.opinion-finhealth`.
