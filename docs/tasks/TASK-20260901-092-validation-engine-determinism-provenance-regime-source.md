# TASK-20260901-092: Validation Engine Determinism, Materiality Provenance & Regime Single Source

## Requirement
Thực hiện 4 tiêu chuẩn nghiệm thu chốt (Final Acceptance Criteria) cho Universal Financial Validation Engine:
1. **AC-1 CLASSIFIER DETERMINISM**: Với mọi event, bất biến `rule_score >= rule_threshold` phải luôn đúng. Nếu không vượt ngưỡng, chuyển sang fallback rule tương ứng có `rule_score >= rule_threshold` xác thực.
2. **AC-2 MATERIALITY PROVENANCE**: Phân định rõ ràng nguồn gốc đo lường của materiality (`COUNTERFACTUAL_MARGIN`, `NOT_APPLICABLE`, `NOT_COMPUTED`). Tuyệt đối không giả lập giá trị mặc định 5% cho các case `UNKNOWN`.
3. **AC-3 REGIME SINGLE SOURCE**: Đồng bộ 100% giữa Event Classifier và Regime Builder. Chỉ năm được xác nhận chia regime (`confirmed_regime_break`) mới mang phân loại `STRUCTURAL_REGIME_BREAK` (`split_regime: true`). Các năm còn lại mang `STRUCTURAL_BREAK_CANDIDATE` (`split_regime: false`).
4. **AC-4 NORMALIZATION TRACE**: Duy trì bất biến `normalization_years == len(normalization_input_years) == len(included_years)` trên 100% symbols.

## Context
Phát hiện từ audit cho thấy 148 event từng là UNKNOWN bị gán heuristic 5% giả lập đo lường, một số event có `rule_score < rule_threshold` nhưng vẫn nhận classification, và năm 2017 của DGC bị gán `STRUCTURAL_REGIME_BREAK` nhưng không tạo break trong Regime Builder.

## Acceptance Criteria
- [x] $\forall \text{event}: \text{rule\_score} \ge \text{rule\_threshold}$ trên 100% events (302/302 events đạt chuẩn, 0 violations).
- [x] `materiality.method` phân định rõ `COUNTERFACTUAL_MARGIN` (113 events), `NOT_COMPUTED` (189 events với `impact_pct: null`, `grade: UNKNOWN`). Xóa bỏ hoàn toàn default 5% giả tạo.
- [x] Chỉ các năm thực sự tạo regime split trong `regime_analysis` mới có `STRUCTURAL_REGIME_BREAK` (5/5 events match 100%, 0 mismatch).
- [x] Bất biến `normalization_years == len(normalization_input_years)` tiếp tục đạt 100% (81/81 symbols).

## Implementation Tasks
- [x] Cập nhật `python/portfolio/value_engine/validation/validation_gate.py` với logic rule evaluation chặt chẽ `rule_score >= rule_threshold`.
- [x] Cập nhật `python/portfolio/value_engine/validation/materiality_checker.py` và `validation_gate.py` với enum `method` (`COUNTERFACTUAL_MARGIN`, `NOT_APPLICABLE`, `NOT_COMPUTED`).
- [x] Đồng bộ danh sách confirmed structural break giữa `detect_structural_breaks` và `_classify_year`.
- [x] Chạy audit script kiểm tra toàn bộ 302 events và 81 archetypes.

## Decisions
- Chuyển toàn bộ các năm chưa đo được materiality về `method: "NOT_COMPUTED"`, `impact_pct: null`, `grade: "UNKNOWN"`.
- Gán `STRUCTURAL_REGIME_BREAK` độc quyền cho các năm xác nhận trong `break_years`; các năm level shift candidate được gán `STRUCTURAL_BREAK_CANDIDATE`.

## Validation Evidence
- `scratch/audit_ac1_to_ac4.py`:
  - 302 events parsed.
  - AC-1 Violations: 0 (100% satisfy `rule_score >= rule_threshold`).
  - AC-2 Materiality: 113 `COUNTERFACTUAL_MARGIN`, 189 `NOT_COMPUTED` (`impact_pct: null`, `grade: UNKNOWN`).
  - AC-3 Regime Single Source: 5 `STRUCTURAL_REGIME_BREAK` events khớp 100% với `regime_analysis` (0 mismatch).
  - AC-4 Normalization Invariant: 81/81 symbols (100% pass).
- Unit tests: `59 passed in 51.44s`.

## Result
Cả 4 Acceptance Criteria (AC-1, AC-2, AC-3, AC-4) đã hoàn thành và kiểm chứng thành công.
