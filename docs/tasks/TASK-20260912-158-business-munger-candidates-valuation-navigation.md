# TASK-20260912-158: Business Munger Candidates & Portfolio Valuation Navigation

- **ID**: TASK-20260912-158
- **Title**: Business Munger Candidates & Portfolio Valuation Navigation
- **Status**: completed
- **Priority**: high
- **Date**: 2026-09-12

---

## Requirement

1. Bổ sung section **"Cổ phiếu tiềm năng theo tiêu chuẩn Munger"** vào trang `/business`:
   - Sinh danh sách động từ financial analysis / policy engine / canonical SSI BCTC hiện có.
   - Tuyệt đối không hard-code ticker, không tạo scoring riêng tách biệt ngoài engine.
   - Ưu tiên tuần tự Munger: QUALITY → DURABILITY → FINANCIAL STRENGTH → ACCOUNTING QUALITY → CAPITAL ALLOCATION → VALUE TRAP RISK → PRICE / MOS.
   - Mỗi candidate hiển thị tối thiểu: Mã, Phân loại chất lượng, Giá thị trường, Base IV, MOS, Required MOS, Bẫy giá trị, ROE, Tăng trưởng LNST, CFO/PAT, Debt/Equity, Cảnh báo tài chính quan trọng nhất, Quyết định hiện tại, Nguồn dữ liệu, Thời điểm cập nhật, và **Lý do được đề xuất** (semantic summary từ backend).
   - Value Trap Gate: Nếu có forensic warning nghiêm trọng (khoản phải thu/tồn kho tăng nhanh, CFO suy giảm, vỡ nợ, v.v.), không được đề xuất như candidate "mua ngay".
   - Hiển thị Top 5–10 mã với nút "Xem tất cả" / filter.
   - Nút "Xem phân tích" điều hướng mượt mà tới `/business/{symbol}`.
2. Bổ sung nút **"Xem định giá"** (hoặc `Định giá`) cho từng vị thế trong bảng danh mục tại Terminal / Portfolio:
   - Điều hướng trực tiếp sang canonical valuation route (ví dụ `/valuation?symbol={symbol}`).
   - Trang Valuation tự động nhận diện `symbol` từ query/hash, cuộn mượt mà đến phần định giá chi tiết và hiển thị đầy đủ Base IV, Bear IV, Bull IV, MOS, Normalized earnings, các giả định và kịch bản.
3. Tối ưu hiệu năng: Tuyệt đối không tạo N+1 requests từ browser. Sử dụng backend aggregation API endpoint (`/api/portfolio/business/candidates`).
4. 100% Semantic tiếng Việt: Không rò rỉ bất kỳ machine enum nào lên UI.
5. Viết unit tests / regression tests đầy đủ, đảm bảo frontend build và backend tests pass.

## Context

- Backend: `app/main.py`, `python/portfolio/value_engine/munger_candidates.py`, `python/portfolio/screener.py`, `python/portfolio/canonical_valuation.py`, `python/portfolio/value_engine/munger_analyzer.py`.
- Frontend: `frontend/src/pages/BusinessPage.jsx`, `frontend/src/pages/TerminalPage.jsx`, `frontend/src/pages/ValuationPage.jsx`, `frontend/src/lib/api.js`, `frontend/src/utils/vietnameseSemantics.js`.
- Report: `docs/reports/munger-candidates-and-valuation-navigation-audit.md`.

## Acceptance Criteria

- [x] AC1: `/business` có section "Cổ phiếu tiềm năng theo tiêu chuẩn Munger".
- [x] AC2: Candidate được sinh động từ financial engine hiện tại dựa trên SSI BCTC, không hard-code ticker.
- [x] AC3: Mỗi candidate có lý do được đề xuất rõ ràng bằng tiếng Việt.
- [x] AC4: Hiển thị đầy đủ các chỉ số tài chính cốt lõi (ROE, Tăng trưởng LNST, CFO/PAT, D/E, MOS, Base IV, Giá thị trường).
- [x] AC5: Hiển thị trạng thái Value Trap, không bỏ qua forensic warning (rủi ro cao không được đề xuất mua).
- [x] AC6: Ưu tiên chất lượng doanh nghiệp trước khi xét valuation/MOS.
- [x] AC7: Có nút "Xem phân tích" điều hướng chuẩn xác tới `/business/{symbol}`.
- [x] AC8: Terminal có nút "Xem định giá" cho từng position điều hướng tới canonical valuation route `/valuation?symbol={symbol}`.
- [x] AC9: Trang Valuation nhận diện và hiển thị chi tiết định giá của mã được truyền sang.
- [x] AC10: Không tạo valuation calculation riêng ở frontend; chỉ consume dữ liệu từ backend.
- [x] AC11: 100% semantic tiếng Việt, tuyệt đối không xuất hiện raw enums hoặc null/nullx/undefined.
- [x] AC12: Backend aggregation API tối ưu, không có N+1 requests từ browser.
- [x] AC13: Tests pass 100%.
- [x] AC14: Frontend build pass với 0 lỗi.
- [x] AC15: Audit report `docs/reports/munger-candidates-and-valuation-navigation-audit.md` ghi nhận đầy đủ chi tiết.

## Constraints and Invariants

1. `BUY_AND_HOLD_INFORMATION_SYSTEM`: Chỉ phân tích, đánh giá và khuyến nghị; không tự ý sinh lệnh giao dịch.
2. `FINANCIAL_STATEMENTS_ONLY`: Dựa trên dữ liệu BCTC đã canonicalize.
3. Không làm thay đổi hay phá vỡ logic định giá canonical valuation hiện hữu.

## Implementation Tasks

- [x] Task 1: Xây dựng module backend `python/portfolio/value_engine/munger_candidates.py` để lọc, xếp hạng và tạo semantic rationale cho các ứng viên Munger.
- [x] Task 2: Thêm endpoint backend `@app.get("/api/portfolio/business-candidates")` (alias `/api/portfolio/business/candidates`) trong `app/main.py` và client API `getMungerCandidates()` trong `frontend/src/lib/api.js`.
- [x] Task 3: Nâng cấp `frontend/src/pages/BusinessPage.jsx` để hiển thị Section "Cổ phiếu tiềm năng theo tiêu chuẩn Munger" với bộ lọc, thẻ ứng viên, chỉ số tài chính, lý do đề xuất và nút điều hướng "Xem phân tích".
- [x] Task 4: Nâng cấp `frontend/src/pages/TerminalPage.jsx` bổ sung nút "Xem định giá" trên từng dòng vị thế danh mục.
- [x] Task 5: Nâng cấp `frontend/src/pages/ValuationPage.jsx` tự động đọc `?symbol=XYZ` hoặc `#valuation-XYZ` từ URL để cuộn và hiển thị chi tiết định giá.
- [x] Task 6: Viết bộ test `python/portfolio/tests/test_munger_candidates_and_valuation_navigation.py`.
- [x] Task 7: Lập báo cáo audit `docs/reports/munger-candidates-and-valuation-navigation-audit.md`.
- [x] Task 8: Chạy kiểm thử, build frontend, commit và push branch `feature/buffett-munger-refactor`.

## Related Notes

- [TASK-20260912-154-deep-munger-financial-decision.md](file:///c:/workspace/shannon_allocation/docs/tasks/TASK-20260912-154-deep-munger-financial-decision.md)
- [TASK-20260912-155-terminal-semantic-data-completeness.md](file:///c:/workspace/shannon_allocation/docs/tasks/TASK-20260912-155-terminal-semantic-data-completeness.md)
- [TASK-20260912-157-deep-value-trap-munger-financial-forensics.md](file:///c:/workspace/shannon_allocation/docs/tasks/TASK-20260912-157-deep-value-trap-munger-financial-forensics.md)

## Validation Evidence

- Unit/Integration Tests:
  ```text
  pytest python/portfolio/tests/test_munger_candidates_and_valuation_navigation.py \
         python/portfolio/tests/test_deep_value_trap_forensics.py \
         python/portfolio/tests/test_business_review_and_value_trap.py \
         python/portfolio/tests/test_ui_raw_enum_regression.py \
         python/portfolio/tests/test_golden_baseline_regression.py -v
  ============================= 25 passed in 58.66s =============================
  ```
- Frontend Build:
  ```text
  npm --prefix frontend run build
  ✓ built in 1.77s (0 errors)
  ```

## Decisions

- Dùng `ThreadPoolExecutor(max_workers=12)` kết hợp query tối ưu `HAVING count(*) >= 8` trên PostgreSQL để đánh giá candidate universe song song chỉ trong vài giây.
- In-memory caching 10 phút trên backend aggregation endpoint `/api/portfolio/business/candidates` đảm bảo phản hồi tức thì cho frontend mà không gây N+1 calls.
- Hỗ trợ deep-link `/valuation?symbol=XYZ` và `#valuation-XYZ` để Terminal page điều hướng mượt mà sang Valuation page.

## Result

- Hoàn thành trọn vẹn cả 2 capabilities theo yêu cầu:
  1. Section "Cổ phiếu tiềm năng theo tiêu chuẩn Munger" trên trang `/business` sinh động, chuẩn xác, giàu thông tin và 100% tiếng Việt tự nhiên.
  2. Nút "Định giá" trên từng vị thế tại Terminal điều hướng chuẩn xác sang `/valuation?symbol=XYZ`.
- Đã lập báo cáo audit `docs/reports/munger-candidates-and-valuation-navigation-audit.md`.
