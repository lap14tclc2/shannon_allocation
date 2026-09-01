# TASK-20260901-093: Cross-Layer Normalization & Unclamped Classifier Score Integrity

## Requirement
Xử lý dứt điểm 3 vấn đề hệ thống:
1. **Cross-Layer Normalization Consistency**: Đồng bộ 100% giữa `owner_earnings_bridge` và `normalization_window`.
   - Với `LATEST_FY`: `normalization_input_years = [latest_fiscal_year]` và `normalization_years = 1`.
   - Phân tách độc lập 3 timeline: `candidate_years` (toàn bộ lịch sử có sẵn), `regime_years` (năm thuộc regime hiện tại), và `normalization_input_years` (năm thực sự đi vào mô hình).
   - Invariant: `owner_earnings_bridge.normalization_input_years == normalization_window.normalization_input_years` và `len(normalization_input_years) == normalization_years`.
2. **Classifier Score Integrity (Bỏ hoàn toàn Score-Clamping)**:
   - `rule_score == actual_score_used_by_rule` (Tuyệt đối không dùng `max(actual, threshold)`).
   - Phân loại `CYCLICAL_EXTREME` chỉ áp dụng khi có bằng chứng chu kỳ thực thụ ($\text{breadth } A \ge 0.35, \text{coherence } C \ge 0.35, \text{cycle\_score} \ge 0.05$). Các case tăng lợi nhuận đơn lẻ ($A < 0.4$) như DP3 2017 chuyển thành `EARNINGS_ONE_OFF_CANDIDATE` hoặc `SUSPICIOUS_ISOLATED`.
3. **Disambiguate `block` trong `valuation_handling`**:
   - Khai báo rõ ràng: `fact_rejected: bool`, `model_blocked: bool`, `model_recomputed: bool`.

## Acceptance Criteria
- [x] 100% symbols thỏa mãn: `owner_earnings_bridge.normalization_input_years == normalization_window.normalization_input_years` (66/66 symbols pass).
- [x] Khi `normalization_method == "LATEST_FY"`, `normalization_years == 1` và `len(normalization_input_years) == 1` (53/53 symbols pass).
- [x] `rule_score` bằng đúng score thực tế của classifier, không còn bất kỳ hàm clamp `max(score, threshold)` (306/306 events pass).
- [x] DP3 2017 được phân loại chính xác (`SUSPICIOUS_ISOLATED`, score: 0.68 >= 0.36), không bị gán sai `CYCLICAL_EXTREME`.
- [x] `valuation_handling` thể hiện rõ `fact_rejected`, `model_blocked`, `model_recomputed`.

## Constraints and Invariants
- `normalization_years == len(normalization_input_years)`.
- `owner_earnings_bridge.normalization_input_years == normalization_window.normalization_input_years`.
- `rule_score == actual_score_used_by_rule`.

## Implementation Tasks
- [x] Cập nhật `python/portfolio/value_engine/owner_earnings.py` để `LATEST_FY` trả về `normalization_input_years = [latest_fiscal_year]`.
- [x] Cập nhật `python/portfolio/value_engine/engine.py` để `_build_normalization_window` lấy chính xác `normalization_input_years` từ `oe_bridge`.
- [x] Cập nhật `python/portfolio/value_engine/validation/validation_gate.py` để gỡ bỏ hoàn toàn score-clamping, tinh chỉnh cycle/one-off rules, và mở rộng `valuation_handling` (`fact_rejected`, `model_blocked`, `model_recomputed`).
- [x] Viết test tự động khóa 8 invariants và audit toàn bộ 82 mã archetypes.

## Decisions
- Phân định rõ 3 timeline độc lập: `candidate_years` (data available), `regime_years` (regime filter), `normalization_input_years` (actual inputs to model).
- Gỡ bỏ hoàn toàn mọi thao tác ép điểm clamping.

## Validation Evidence
- `scratch/audit_ac1_to_ac4.py`:
  - Total Events: 306.
  - AC-1 Determinism: 0 violations, 0 clamping.
  - AC-2 Materiality: 113 Counterfactual Margin, 193 Not Computed, 62 Immaterial/Not Applicable.
  - AC-3 Regime Single Source: 4 confirmed break events, 0 mismatch.
  - Invariant 1 (`normalization_years == len(normalization_input_years)`): 82/82 (100%).
  - Invariant 2 (`LATEST_FY` $\implies \text{years}=1 \land \text{inputs}=1$): 53/53 (100%).
  - Invariant 3 (`owner_earnings_bridge == normalization_window`): 66/66 (100%).
- Unit tests: `59 passed in 61.73s`.

## Result
Toàn bộ cross-layer normalization và classifier score integrity đã được đồng bộ chuẩn hóa và kiểm chứng thành công.
