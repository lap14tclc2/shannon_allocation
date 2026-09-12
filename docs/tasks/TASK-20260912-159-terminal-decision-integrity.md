# TASK-20260912-159: Audit & Fix QPort Buffett Terminal — Portfolio Decision Integrity

- **ID**: TASK-20260912-159
- **Title**: Audit & Fix QPort Buffett Terminal — Portfolio Decision Integrity
- **Status**: completed
- **Priority**: high
- **Date**: 2026-09-12

---

## Requirement

Rà soát và sửa toàn diện Buffett Terminal và toàn bộ các trang liên quan (Portfolio, Decision Matrix, Valuation, Business, Pre-Commitment 8 câu hỏi, Value Trap, Candidate Discovery) để đảm bảo:
1. Người dùng hiểu rõ ràng 9 câu hỏi cốt lõi:
   - Tôi đang sở hữu gì?
   - Giá hiện tại là bao nhiêu?
   - Giá vốn là bao nhiêu?
   - Giá trị hiện tại của từng vị thế là bao nhiêu?
   - Doanh nghiệp đang được đánh giá thế nào?
   - Định giá cho thấy mức MOS bao nhiêu?
   - Value Trap đang cảnh báo điều gì?
   - Quyết định Buffett/Munger hiện tại là gì?
   - Tôi nên làm gì tiếp theo?
2. 100% Vietnamese Semantic Layer: Tuyệt đối không còn raw enum (`REVIEW_BUSINESS`, `WATCH`, `CLEAR`, `HIGH_QUALITY`, `INVESTABLE`, `EXCEPTIONAL`, `POTENTIAL_COMPOUNDER`, `PROFIT_CASH_DIVERGENCE`, `RECEIVABLES_GROW_FASTER_THAN_REVENUE`, `INSUFFICIENT_DATA`, `NO_DETERIORATION`, `UNPROTECTED`, `UNKNOWN`), không còn `snake_case`, không còn `N/A`/`null`/`nullx`/`undefined`/`NaN`.
3. Metric Accuracy & Calculation Integrity: Phân biệt rõ Có thể tính / Chưa đủ dữ liệu / Không áp dụng. Không dùng N/A bừa bãi.
4. Market price & Cash & Portfolio calculations:
   - Tổng tài sản = Giá trị thị trường cổ phiếu + Tiền mặt.
   - Tỷ trọng phân bổ tính trên Tổng tài sản.
   - Thêm / sửa / xóa vị thế và tiền mặt persist đúng.
   - Nút "Xem định giá" trên từng vị thế dẫn trực tiếp tới `/valuation?symbol={SYMBOL}` hoặc `/business/{SYMBOL}`.
5. Value Trap giàu thông tin: Đưa ra phát hiện, bằng chứng BCTC nhiều năm, tác động và điều kiện theo dõi.
6. Munger Pre-Commitment (8 câu hỏi): QPort tự động trả lời bằng dữ liệu BCTC định lượng.
7. Candidate Stocks / Doanh nghiệp đáng chú ý: Tích hợp động từ engine Munger.

## Context

- Frontend:
  - `frontend/src/pages/TerminalPage.jsx`
  - `frontend/src/pages/BusinessDetailPage.jsx`
  - `frontend/src/pages/BusinessPage.jsx`
  - `frontend/src/pages/ValuationPage.jsx`
  - `frontend/src/utils/vietnameseSemantics.js`
  - `frontend/src/terminal-page.css`
- Backend:
  - `python/portfolio/value_engine/munger_analyzer.py`
  - `python/portfolio/value_engine/value_trap.py`
  - `python/portfolio/value_engine/munger_candidates.py`
  - `python/portfolio/value_engine/munger_thesis_challenge.py`
  - `app/main.py`
- Report: `docs/reports/terminal-decision-integrity-audit.md`

## Acceptance Criteria

- [x] AC1: User mở Terminal và hiểu được toàn bộ danh mục và từng vị thế mà không cần biết bất kỳ enum nội bộ nào.
- [x] AC2: Không còn raw enum / snake_case / nullx / undefined / NaN trên UI.
- [x] AC3: Không còn N/A ở metric có thể tính từ dữ liệu BCTC.
- [x] AC4: Market price và P/L tính toán chính xác, có thông báo rõ nếu chưa có giá.
- [x] AC5: Portfolio Total = Stock Market Value + Cash; Tỷ trọng phân bổ tính trên Total Assets.
- [x] AC6: Vị thế và tiền mặt có thể thêm/sửa/xóa và persist sau refresh.
- [x] AC7: Mỗi position có nút "Xem định giá" điều hướng chuẩn xác tới trang chi tiết ticker.
- [x] AC8: Value Trap cung cấp đầy đủ phát hiện, bằng chứng lịch sử nhiều năm, tác động và điều kiện theo dõi.
- [x] AC9: Munger 8 câu hỏi pre-commitment được QPort tự trả lời từ dữ liệu tài chính.
- [x] AC10: Doanh nghiệp đáng chú ý (Munger Candidates) sinh động từ engine, không hard-code.
- [x] AC11: Tương thích hoàn toàn với SSI BCTC và bất biến sổ cái (Ledger Invariants).
- [x] AC12: Unit & Regression tests pass 100%.
- [x] AC13: Frontend build pass với 0 lỗi.
- [x] AC14: Báo cáo audit `docs/reports/terminal-decision-integrity-audit.md` ghi nhận chi tiết.

## Constraints and Invariants

1. `BUY_AND_HOLD_INFORMATION_SYSTEM`: Hệ thống giải thích, hỗ trợ quan sát và khuyến nghị kỷ luật; không tự sinh lệnh mua/bán.
2. `LEDGER_INVARIANT`: Biến động giá, thời gian hay rủi ro không làm thay đổi số lượng cổ phiếu sổ cái.
3. `FINANCIAL_STATEMENTS_ONLY`: Dữ liệu tài chính từ BCTC SSI chuẩn hóa.

## Implementation Tasks

- [x] Task 1: Audit toàn bộ frontend & backend presentation layer cho Terminal, Business Detail, Value Trap và Munger 8-Q.
- [x] Task 2: Nâng cấp centralized semantic helper `frontend/src/utils/vietnameseSemantics.js` để bao quát 100% enum, status, value trap indicators, moat, capital allocation và pre-commitment.
- [x] Task 3: Cập nhật `frontend/src/pages/TerminalPage.jsx` (Position table, Decision matrix, Cash editor, Total Assets, Actions, Buttons, Semantic cards, Munger candidates widget).
- [x] Task 4: Cập nhật `frontend/src/components/ThesisChallengeSection.jsx` và `BusinessPage.jsx` (Value Trap Forensics detail, Munger 8 pre-commitment answers, 12D matrix metrics).
- [x] Task 5: Cập nhật backend `python/portfolio/value_engine/munger_thesis_challenge.py` và `munger_analyzer.py` để tự động tổng hợp câu trả lời định lượng cho 8 câu hỏi Munger.
- [x] Task 6: Viết bộ test kiểm thử `python/portfolio/tests/test_terminal_decision_integrity.py`.
- [x] Task 7: Lập báo cáo audit `docs/reports/terminal-decision-integrity-audit.md`.
- [x] Task 8: Chạy kiểm thử, build frontend, commit và push branch `munger-buffer`.

## Related Notes

- [TASK-20260912-148-complete-enum-leakage-audit.md](file:///c:/workspace/shannon_allocation/docs/tasks/TASK-20260912-148-complete-enum-leakage-audit.md)
- [TASK-20260912-155-terminal-semantic-data-completeness.md](file:///c:/workspace/shannon_allocation/docs/tasks/TASK-20260912-155-terminal-semantic-data-completeness.md)
- [TASK-20260912-157-deep-value-trap-munger-financial-forensics.md](file:///c:/workspace/shannon_allocation/docs/tasks/TASK-20260912-157-deep-value-trap-munger-financial-forensics.md)
- [TASK-20260912-158-business-munger-candidates-valuation-navigation.md](file:///c:/workspace/shannon_allocation/docs/tasks/TASK-20260912-158-business-munger-candidates-valuation-navigation.md)

## Validation Evidence

- Unit/Regression Tests:
  ```text
  pytest python/portfolio/tests/test_terminal_decision_integrity.py \
         python/portfolio/tests/test_munger_candidates_and_valuation_navigation.py \
         python/portfolio/tests/test_deep_value_trap_forensics.py \
         python/portfolio/tests/test_golden_baseline_regression.py -v
  ======================= 24 passed in 118.61s (0:01:58) ========================
  ```
- Frontend Build:
  ```text
  npm --prefix frontend run build
  ✓ built in 1.63s (0 errors)
  ```

## Decisions

- Tích hợp widget "Cơ Hội Đầu Tư Đáng Chú Ý (Tiêu Chuẩn Munger)" trực tiếp vào Buffett Terminal để tạo trải nghiệm liền mạch từ quản lý danh mục đến khám phá cơ hội mới.
- Modal chi tiết từng vị thế cung cấp hai nút điều hướng rõ ràng: "Xem định giá chi tiết →" và "Mở trang doanh nghiệp →".
- Munger 8 câu hỏi phản biện luận điểm đầu tư tự động sinh số liệu định lượng về kịch bản sụt giảm lợi nhuận (-30%/-50%), kịch bản giá trị nội tại bị thổi phồng (+30%) và tiêu chí bác bỏ thesis.

## Result

- (Sẽ cập nhật khi hoàn thành)
