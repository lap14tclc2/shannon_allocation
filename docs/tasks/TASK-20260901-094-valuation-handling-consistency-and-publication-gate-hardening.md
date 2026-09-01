# TASK-20260901-094: Valuation Handling Consistency & Publication Gate Hardening

## Requirement
Xử lý dứt điểm 5 vấn đề consistency ở layer `valuation_handling` và publication gate:
1. **Fix `EXCLUDE_METRIC_YEAR` vs `include=true` mismatch**:
   - Nếu `include=True` và `exclude_metric=None`: action là `KEEP_WITH_WARNING` hoặc `NO_ADJUSTMENT`.
   - Chỉ khi thực sự exclude mới mang `EXCLUDE_METRIC_YEAR` (kèm `fact_rejected=True`, `model_recomputed=True`, `exclude_metric != []`).
2. **Relevance Hierarchy theo Normalization Window**:
   - Chuẩn hóa 5 cấp bậc: `VALUATION_INPUT`, `NORMALIZATION_INPUT`, `REGIME_INPUT`, `HISTORICAL_CONTEXT`, `PER_SHARE_INPUT`.
   - Năm không nằm trong `normalization_input_years` (ví dụ 2016–2024 ở `LATEST_FY`) được gán `HISTORICAL_CONTEXT` hoặc `REGIME_INPUT`, không gán nhầm `NORMALIZATION_INPUT`.
3. **Phân định rõ `REJECT_FACT` vs `BLOCK_MODEL`**:
   - `REJECT_FACT` (Layer 1 / one-offs): `fact_rejected=True`, `model_blocked=False`, `model_recomputed=True`.
   - `BLOCK_MODEL` (chỉ áp dụng cho `UNRESOLVED_MATERIAL`): `fact_rejected=True`, `model_blocked=True`, `model_recomputed=False`.
4. **Hard Gate Material Anomaly trong `VALUATION_INPUT` (NT2 Case)**:
   - Anomaly thuộc `VALUATION_INPUT` có `materiality >= MATERIAL` và không được recomputed/adjusted: chuyển thành `UNRESOLVED_MATERIAL`, `model_blocked=True`, hạ model status thành `MODEL_PARTIAL`/`MODEL_INCOMPLETE` và ẩn public IV.
5. **Rename `DOWNWEIGHT_EARNINGS` $\to$ `EXCLUDE_EARNINGS_METRIC`**:
   - Khớp tên action với hành vi thực tế.

## Acceptance Criteria
- [x] 0 event nào bị mâu thuẫn giữa `use == "EXCLUDE_METRIC_YEAR"` và `include == True` (0 mismatches).
- [x] 100% events ở các mã `LATEST_FY` cho các năm trước latest_year mang `HISTORICAL_CONTEXT`/`REGIME_INPUT` (0 mismatches).
- [x] 0 mã `MODEL_VERIFIED` nào chứa event mang `model_blocked == True` (0 mismatches).
- [x] Hard regression test cho NT2: anomaly 2025 material (15.1%) kích hoạt `BLOCK_MODEL` $\implies$ model status `MODEL_PARTIAL`, ẩn public Base IV.
- [x] Action `DOWNWEIGHT_EARNINGS` được đổi thành `EXCLUDE_EARNINGS_METRIC` (0 legacy usages).

## Constraints and Invariants
- `model_blocked == True` $\implies$ không có public IV.
- `normalization_input_years` chỉ chứa các năm đi vào tính toán model.
- `rule_score == actual_score_used_by_rule`.

## Implementation Tasks
- [x] Cập nhật `python/portfolio/value_engine/validation/validation_gate.py` với USE_MATRIX mới, relevance hierarchy, và tách bạch `REJECT_FACT` vs `BLOCK_MODEL`.
- [x] Cập nhật `python/portfolio/value_engine/engine.py` để inject `normalization_input_years` vào validation gate và gate chặt các mã có unhandled material anomaly ở `VALUATION_INPUT`.
- [x] Chạy comprehensive audit trên 82 mã archetypes và suite unit tests.

## Decisions
- Phân định rõ 5 cấp bậc relevance: `VALUATION_INPUT` (năm mới nhất), `NORMALIZATION_INPUT` (năm vào model), `REGIME_INPUT` (năm trong regime nhưng không vào model), `HISTORICAL_CONTEXT` (ngoài regime), `PER_SHARE_INPUT` (biến động cổ phiếu).
- Tách bạch `REJECT_FACT` (bỏ fact sai/one-off để tính lại model) và `BLOCK_MODEL` (khóa model vì material risk chưa giải thích).

## Validation Evidence
- `scratch/audit_ac1_to_ac4.py`:
  - Total Events: 306.
  - CHECK 1 (`EXCLUDE_METRIC_YEAR` Consistency): 0 mismatches (PASS).
  - CHECK 2 (`Valuation Relevance vs Window`): 0 mismatches (PASS).
  - CHECK 3 (`Model Blocked vs MODEL_VERIFIED`): 0 mismatches (PASS).
  - CHECK 4 (`VALUATION_INPUT Material Gating`): 0 leaked public IV (PASS).
  - CHECK 5 (`EXCLUDE_EARNINGS_METRIC` Name): 0 legacy usages (PASS).
  - AC-1 Classifier Determinism: 0 violations (PASS).
  - AC-2 Materiality: 96 Counterfactual Margin, 107 Not Applicable, 103 Not Computed (PASS).
- `scratch/test_5_cases.py`:
  - NT2 FY2025: `UNRESOLVED_MATERIAL` $\to$ `MODEL_PARTIAL`, Public Base IV: None.
  - CHP: `MODEL_VERIFIED`, FY2019/2024 `UNIT_MAPPING_ERROR_CANDIDATE` mang `REJECT_FACT` (`fact_rejected=True, model_blocked=False, model_recomputed=True`).
  - DP3: `MODEL_VERIFIED`, FY2017/2020 mang `REGIME_INPUT`, `KEEP_WITH_WARNING`, `NOT_APPLICABLE (IMMATERIAL, 0.0%)`.
  - DGC: `MODEL_VERIFIED`, FY2017 `HISTORICAL_CONTEXT`, FY2021/2022 `NORMALIZATION_INPUT` mang `KEEP_WITH_WARNING`.
- Unit tests: `59 passed in 50.93s`.

## Result
Cả 5 vấn đề consistency giữa event classification, valuation relevance, handling action và publication gate đã được giải quyết triệt để.
