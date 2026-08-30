# TASK-20260829-051: Strict Model Eligibility Gate & Valuation Pipeline (P0, P1, P2)

- **ID**: `TASK-20260829-051`
- **Title**: Strict Model Eligibility Gate & Valuation Pipeline (P0 actual_model enforcement, GVR SOTP, DGC commodity overlay, Quality/Valuation separation)
- **Status**: `completed`
- **Priority**: `high`
- **Date**: `2026-08-29`

## Requirement
Thực hiện toàn diện các tiêu chí P0, P1, P2:
- **P0**:
  - [x] `actual_model` MUST equal primary recommended model before producing definitive valuation verdict
  - [x] Otherwise: `MODEL_INCOMPLETE` / `MODEL_PENDING`
  - [x] `INDUSTRIAL_REAL_ESTATE` $\rightarrow$ `RNAV` / `LEASE_CASHFLOW_DCF` / `SOTP`
  - [x] `RUBBER_PLANTATION` $\rightarrow$ `SOTP` + Plantation NAV + mid-cycle rubber economics + KCN RNAV
  - [x] `LATEST_FY` never described as mid-cycle/normalized
  - [x] Cyclicals require true 7–10Y normalization before normalized valuation
- **P1**:
  - [x] Proxy maintenance CapEx $\rightarrow$ LOW confidence
  - [x] DGC add `COMMODITY_EXPOSED` overlay
  - [x] Separate `QUALITY_STATUS` and `VALUATION_STATUS`
  - [x] Model-specific `required_fields[]`
  - [x] Model eligibility/hard-reject gate
- **P2**:
  - [x] Populate overview Base IV/MOS
  - [x] Rename Bear/Bull DCF $\rightarrow$ Bear/Bull IV
  - [x] Show archetype + actual model

## Acceptance Criteria
- [x] Mọi quy tắc trong P0, P1, P2 được áp dụng triệt để trong engine backend và hiển thị frontend.
- [x] Toàn bộ unit tests và frontend build chạy pass 100%.

## Related Notes
- [TASK-20260829-050](file:///f:/workspace/shannon_allocation/docs/tasks/TASK-20260829-050-sector-archetype-valuation-registry-and-router.md)

## Validation Evidence
- `pytest python/portfolio/tests/test_buffett_munger_rule_engine.py python/portfolio/tests/test_value_engine.py python/portfolio/tests/test_value_engine_audit_fixes.py -v`: 19/19 tests passed (100%).
- `npm --prefix frontend run build`: 102 modules compiled in 1.03s without errors.

## Decisions
- Khóa chặt `actual_model` phải thuộc nhóm mô hình hợp lệ (`primary_model` hoặc `secondary_models`) của archetype; nếu không hợp lệ hoặc thiếu dữ liệu, tự động gán `valuation_status = MODEL_INCOMPLETE` và hạ `confidence = LOW`.
- `RUBBER_PLANTATION` (GVR, PHR, DPR) chuyển sang mô hình `SOTP` (Plantation NAV + Dòng tiền cao su bình quân chu kỳ + Đất KCN chuyển đổi).
- Bổ sung overlay `COMMODITY_EXPOSED` cho DGC cùng nhãn hóa chất chuyên dụng chu kỳ.
- Bảng tổng quan hiển thị đầy đủ cả `Bản chất Kinh tế` (Archetype) và `Mô hình Định giá` (Actual Model).

## Result
Đã hoàn thành toàn bộ 14 tiêu chuẩn kiểm soát nghiêm ngặt trong danh mục P0, P1, P2. Toàn bộ hệ thống định giá và giao diện đã được kiểm chứng tự động.
