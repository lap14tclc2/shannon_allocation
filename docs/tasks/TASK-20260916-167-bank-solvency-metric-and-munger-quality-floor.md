# TASK-20260916-167: Bank Solvency Metric & Munger Quality Floor Gate (DDV Cheap vs Good Business Separation)

## Metadata
- **ID**: `TASK-20260916-167`
- **Title**: Bank Solvency Metric & Munger Quality Floor Gate (DDV Cheap vs Good Business Separation)
- **Status**: completed
- **Priority**: high
- **Date**: 2026-09-16
- **Branch**: `feature/buffett-munger-refactor`

---

## Requirement
1. **Thay thế Nợ/VCSH cho Ngân hàng**: Ngân hàng không sử dụng tỷ lệ Nợ/VCSH (Debt/Equity). Cần thay thế bằng chỉ số an toàn đòn bẩy ngân hàng chuẩn mực: **Đòn bẩy Tài sản (Tổng tài sản / VCSH - Bank Leverage)** và **Tỷ lệ Đệm vốn (VCSH / Tổng tài sản - Equity to Assets)**.
2. **Ngăn chặn bẫy "Giá rẻ nhưng chất lượng kém" (The DDV Case)**:
   - Tách biệt tuyệt đối giữa "giá rẻ (MOS cao)" và "doanh nghiệp chất lượng tốt".
   - Doanh nghiệp có `compounder_classification == WEAK_BUSINESS`, hoặc `ROE < 8.0%`, hoặc `decision == AVOID`, hoặc `synthesis_conclusion` là bẫy giá trị/rủi ro tài chính cao KHÔNG được đưa vào danh sách ứng viên Munger Candidate.
   - Dữ liệu dòng tiền: `CFO/PAT = Chưa đủ dữ liệu` TUYỆT ĐỐI KHÔNG được coi là PASS và không được gán lời khen dòng tiền tự do.
   - Diễn đạt ngữ nghĩa (Rationale): Khi thị giá chiết khấu sâu (MOS cao) nhưng chất lượng kinh tế chưa được chứng minh (ROE thấp, CFO/PAT thiếu, rủi ro chu kỳ), hệ thống phải cảnh báo rõ ràng: *"Giá đang thấp so với giá trị nội tại ước tính, nhưng chất lượng kinh tế chưa đủ thuyết phục. Cần xác minh earning power trước khi xem xét đầu tư"*, thay vì khuyến nghị "Xem xét mua".

## Context & Root Cause Analysis
1. **Ngân hàng hiển thị "Không áp dụng"**: Tại `munger_candidates.py` và `BusinessPage.jsx`, trường `Nợ / Vốn CSH` hiển thị `"Không áp dụng"` đối với TCB, ACB, MBB... Trong khi đó, `munger_archetype_analyzers.py` đã tính toán đầy đủ `bank_leverage` (ví dụ TCB là `6.64x`) và `equity_assets_ratio` (`15.1%`), nhưng chưa được ánh xạ lên giao diện thẻ ứng viên.
2. **Thiếu sàn lọc chất lượng (Missing Quality Floor)**: Trong `munger_candidates.py`, hàm `_evaluate_candidate_symbol` dùng nhánh `else: candidate_tier_code = "INVESTABLE"` cho mọi mã còn lại, dẫn đến cổ phiếu chất lượng tài chính yếu (như DDV: ROE 4.1%, WEAK_BUSINESS, quyết định AVOID) vẫn lọt vào Candidate. Hơn nữa, vì MOS của DDV đạt 78.9%, nó được cộng thêm +30 điểm rank score và gán nhãn `Đạt biên an toàn (Xem xét mua)`, tạo ra mâu thuẫn trực tiếp với cảnh báo bẫy giá trị.

## Acceptance Criteria
- [x] Bổ sung trường `solvency_metric_label` và `solvency_metric_display` trong Candidate payload:
  - Archetype `BANK`: Label `"Đòn bẩy TS (TS/VCSH)"`, Value `f"{bank_leverage:.1f}x (Đệm vốn {equity_assets*100:.1f}%)"`.
  - Archetype `SECURITIES`: Label `"Đòn bẩy TS (TS/VCSH)"`, Value `f"{sec_leverage:.1f}x"`.
  - Archetype `NORMAL_ENTERPRISE`: Label `"Nợ / Vốn CSH"`, Value `f"{de_ratio:.2f}x"`.
- [x] Cập nhật frontend `BusinessPage.jsx`: Thẻ tài chính hiển thị linh hoạt theo `solvency_metric_label` và `solvency_metric_display`.
- [x] Thiết lập Munger Quality Floor Gate trong `_evaluate_candidate_symbol`:
  - Loại bỏ các mã có `compounder_classification == "WEAK_BUSINESS"`.
  - Loại bỏ các mã có `roe_pct < 8.0%` (mức sinh lời dưới lãi suất trái phiếu/tiết kiệm dài hạn).
  - Loại bỏ các mã có quyết định cốt lõi `decision_state == "AVOID"`.
  - Loại bỏ các mã có kết luận `synthesis_conclusion` là rủi ro tài chính cao / bẫy giá trị.
- [x] Cập nhật rationale builder `_generate_candidate_rationale_vi`:
  - Không khen MOS cao nếu ROE thấp hoặc thiếu dữ liệu CFO/PAT.
  - Phản ánh đúng ngữ nghĩa: "Rẻ nhưng chất lượng kinh tế chưa được chứng minh".
  - `CFO/PAT = None` không bao giờ được coi là PASS.
- [x] Chạy kiểm thử tự động, xác minh DDV bị loại khỏi Candidate hoặc được cảnh báo chuẩn mực, các ngân hàng (TCB, ACB, MBB, VIB) hiển thị đúng Đòn bẩy tài sản.

## Constraints and Invariants
- Giữ nguyên triết lý Buffett-Munger: "Thà mua doanh nghiệp tuyệt vời ở mức giá hợp lý, còn hơn mua doanh nghiệp bình thường ở mức giá tuyệt vời".
- Liquidity gate $\ge 5.0$ tỷ VNĐ/ngày tiếp tục duy trì.

## Implementation Tasks
- [x] Sửa `python/portfolio/canonical_valuation.py`: Trích xuất `BS.ASSETS.TOTAL` vào `financial_history` để cung cấp cho mô hình ngân hàng.
- [x] Sửa `python/portfolio/value_engine/munger_candidates.py`:
  - Thêm `solvency_metric_label`, `solvency_metric_display`, `bank_leverage`, `equity_assets_ratio_pct`.
  - Thiết lập Quality Floor: loại bỏ `WEAK_BUSINESS`, `AVOID`, `ROE < 8.0%`.
  - Sửa `_generate_candidate_rationale_vi` xử lý tình huống unproven quality.
- [x] Sửa `frontend/src/pages/BusinessPage.jsx`: Render dynamic solvency label & value.
- [x] Chạy kiểm thử tự động `pytest`.

## Validation Evidence
1. **Loại bỏ DDV & Bẫy giá trị khỏi Candidate**:
   - `_evaluate_candidate_symbol('DDV') -> None` (Đã bị loại hoàn toàn khỏi Candidate do `compounder_classification == WEAK_BUSINESS`, `ROE 4.1%`, `decision == AVOID`).
   - Tổng ứng viên Munger sau khi lọc chuẩn: **40 doanh nghiệp chất lượng cao thực thụ** (CTR, DGC, HAH, FPT, QNS, VIB, MBB, MWG, VHM, VNM...).
2. **Chỉ số an toàn Ngân hàng (Bank Leverage & Cushion)**:
   - TCB: `Đòn bẩy TS (TS/VCSH): 6.6x (Đệm vốn 15.1%)`.
   - ACB: `Đòn bẩy TS (TS/VCSH): 10.9x (Đệm vốn 9.2%)`.
   - MBB: `Đòn bẩy TS (TS/VCSH): 11.4x (Đệm vốn 8.8%)`.
   - VIB: `Đòn bẩy TS (TS/VCSH): 11.9x (Đệm vốn 8.4%)`.
3. **Automated Tests**:
   - `pytest python/portfolio/tests/test_munger_candidates_and_valuation_navigation.py python/portfolio/tests/test_receivables_evidence_forensics.py`: **13 passed in 12.74s**.

## Result
Hoàn tất việc thay thế Nợ/VCSH cho Ngân hàng bằng Đòn bẩy TS (Tổng TS/VCSH) & Đệm vốn, đồng thời siết chặt Munger Quality Floor Gate, loại bỏ hoàn toàn các trường hợp bẫy giá trị "thị giá rẻ nhưng chất lượng kém" (như DDV) ra khỏi Candidate.
