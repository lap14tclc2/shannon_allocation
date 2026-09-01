# TASK-20260901-091: Audit Universal Validation Engine & Activity Chain Reanchor

## Requirement
Xử lý dứt điểm 5 vấn đề hệ thống được chỉ ra sau đợt audit 68 mã valuation:
1. **Classifier Reproducibility**: Classification (CYCLICAL_EXTREME, STRUCTURAL_REGIME_BREAK, v.v.) phải derive từ một công thức / rule score xác định rõ ràng, không được có trường hợp `cycle_score = 0` nhưng gắn `CYCLICAL_EXTREME HIGH`.
2. **`included_years` Semantics & Invariant**: Đảm bảo `len(normalization_input_years) == normalization_years == len(included_years)` trên 100% mã. Phân tách rõ ràng giữa `candidate_years`, `regime_years`, `normalization_input_years`, và `excluded_years`.
3. **Materiality Engine Completeness & `valuation_relevance`**: Bổ sung enum `valuation_relevance` (`NOT_USED`, `QUALITY_ONLY`, `NORMALIZATION_INPUT`, `VALUATION_INPUT`, `PER_SHARE_INPUT`). Nếu fact lỗi thuộc năm không dùng trong định giá (`valuation_relevance == 'NOT_USED'`), gán `materiality = 'IMMATERIAL'`, `model_recomputed_after_rejection = True`, không để `UNKNOWN` và không chặn `MODEL_VERIFIED`.
4. **Cash Quality Scoring Robustness**: Cải tiến chấm điểm chất lượng tiền mặt trong `QualityScorer` (Winsorize CFO/NI, cap input tại 200%, gắn cờ `CASHFLOW_TIMING`, chấm điểm dựa trên tính nhất quán của dòng tiền dương và tương quan dòng tiền - lợi nhuận).
5. **Activity Chain Database Reanchor (P0)**: Thực thi lệnh reanchor trực tiếp trên Postgres DB để sửa `PREV_HASH_MISMATCH` từ record 73 đến 2090.

## Acceptance Criteria
- [x] Classification trong Regime Engine có `rule_score` / `rule_threshold` minh bạch, 100% reproduce được từ điểm số thành phần.
- [x] Invariant `normalization_years == len(normalization_input_years) == len(included_years)` thỏa mãn trên 100% cổ phiếu (81/81 test cases pass 100%).
- [x] `valuation_relevance` được gán đầy đủ trên 100% events, không còn event bị `materiality = 'UNKNOWN'` khi `valuation_relevance == 'NOT_USED'`.
- [x] Cash conversion ratio > 200% không bị thổi phồng điểm số ảo, kích hoạt cờ `CASHFLOW_TIMING` và chuyển status thành `GOOD` kèm chẩn đoán rõ ràng.
- [x] Database Activity Chain được reanchor thành công, toàn bộ 5 users và schemas trong PostgreSQL đạt `VERIFIED` / `VERIFIED_FROM_ANCHOR` (0 broken hash).

## Constraints and Invariants
- Buy & Hold Invariant: không làm thay đổi sổ cái giao dịch.
- Invariant: `normalization_years == len(normalization_input_years) == len(included_years)`.

## Implementation Tasks
- [x] Cập nhật `python/portfolio/value_engine/validation/validation_gate.py` với deterministic classifier logic và `valuation_relevance`.
- [x] Cập nhật `python/portfolio/value_engine/engine.py`, `owner_earnings.py`, `models.py` để format chuẩn `normalization_window` schema (`candidate_years`, `regime_years`, `normalization_input_years`, `excluded_years`, `included_years`).
- [x] Cập nhật `python/portfolio/value_engine/quality_scorer.py` và `app/main.py` với robust cash quality calculation và winsorizing > 200%.
- [x] Thực thi reanchor trên database PostgreSQL qua script kiểm toán activity chain.
- [x] Chạy test suite và audit script để xác nhận evidence.

## Decisions
- Bổ sung `valuation_relevance` vào schema event resolution để định vị chính xác phạm vi ảnh hưởng của dữ liệu.
- Giới hạn tối đa đóng góp của CFO/NI ở mức 200% để ngăn chặn méo mó tỷ lệ khi mẫu số LNST quá nhỏ.

## Validation Evidence
- **Activity Chain DB Reanchor**: Portfolio `Audit 34 Archetypes Universe` (2.090 records) đã được reanchor thành công từ root break ID 73, chuyển trạng thái sang `VERIFIED_FROM_ANCHOR` (2.091 records, 0 failures). 100% user schemas đạt status VERIFIED.
- **Normalization Invariant**: Kiểm tra 81/81 mã đạt `len(normalization_input_years) == normalization_years == len(included_years)` 100%.
- **Cash Quality Test**: HT1 (1.037%), MSR (3.478%), MWG (511%), GEG (550%), VGI (706%) đã được hạ bậc từ `EXCELLENT` ảo xuống `GOOD` kèm ghi nhận timing dòng tiền.
- **Unit tests**: `59 passed in 53.19s` (Value Engine, Screener, Rule Engine, Audit Integrity).

## Result
Cả 5 vấn đề hệ thống (P0 activity chain reanchor, P1 classifier math reproducibility, P1 normalization input semantics, P1 valuation relevance completeness, P1 cash quality scoring) đã được xử lý triệt để và kiểm chứng hoàn toàn.
