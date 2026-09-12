# TASK-20260912-153: Improve QPort Terminal User Guide

- **ID**: TASK-20260912-153
- **Title**: Improve QPort Terminal User Guide
- **Status**: completed
- **Priority**: high
- **Date**: 2026-09-12

---

## Requirement

1. Cập nhật trang Hướng dẫn / User Guide của QPort (`frontend/src/pages/GuidePage.jsx`) để người dùng mới có thể hiểu và sử dụng QPort Terminal mà không cần đọc source code.
2. Bổ sung section chuyên sâu "QPort Terminal", giải thích rõ ràng mục tiêu và khả năng của Terminal: xem danh mục, thêm/sửa/xóa vị thế, cập nhật số lượng, giá vốn, quản lý tiền mặt và chạy các thao tác phân tích hiện có.
3. Cung cấp hướng dẫn Quick Start từng bước (Bước 1 -> Bước 9) với hành động cụ thể và kết quả mong đợi.
4. Minh họa bằng ví dụ danh mục thực tế rõ ràng (FPT, ACB, Tiền mặt) và ghi chú đây là ví dụ minh họa, không hard-code.
5. Giải thích chi tiết các trường nhập liệu (Symbol, Quantity, Average Cost) và các validation thực tế (mã chữ/số 2-10 ký tự, số lượng > 0, giá vốn >= 1,000 VND đầy đủ).
6. Giải thích rõ ràng thao tác Xóa vị thế và cảnh báo phân tách: Xóa vị thế khỏi danh mục không đồng nghĩa với xóa dữ liệu tài chính của mã khỏi database.
7. Hướng dẫn quản lý tiền mặt: Tiền mặt là tài sản trong portfolio, không phải mã cổ phiếu.
8. Giải thích các trường thông tin hiển thị trên bảng Terminal (Mã, SL, Giá vốn, Giá TT, Vốn đầu tư, Giá trị TT, Lãi/Lỗ, Tỷ trọng, Tiền mặt, Tổng danh mục).
9. Giải thích mối quan hệ dữ liệu: Portfolio -> Selected symbol -> Financial data (SSI BCTC canonicalized) -> Buffett/Munger analysis -> Valuation -> Decision support.
10. Bổ sung subsection "Nguồn dữ liệu tài chính" (dữ liệu BCTC SSI đã import vào database, tập trung báo cáo thường niên lịch sử).
11. Giải thích hệ thống phân tích Buffett/Munger và kiểm tra Bẫy giá trị (Value Trap) hoàn toàn bằng tiếng Việt ngữ nghĩa (semantic), tuyệt đối không để rò rỉ mã enum kỹ thuật.
12. Bổ sung bảng so sánh chức năng thực tế giữa Terminal và Web UI.
13. Bổ sung mục "Các lỗi thường gặp" (8 lỗi kinh điển của nhà đầu tư mới).
14. Bổ sung subsection "Giá cổ phiếu sau chia tách & Cổ tức".
15. Đảm bảo giao diện responsive, thẩm mỹ, mượt mà trên cả desktop và mobile, build frontend PASS.

## Context

- Trang Guide hiện tại (`frontend/src/pages/GuidePage.jsx`) phục vụ route `/guide`.
- QPort Terminal tại `/` (hoặc `/terminal`) hỗ trợ quản lý vị thế danh mục (thêm, sửa, xóa, tiền mặt) kết hợp trực tiếp với Pháo đài tài chính cá nhân và Ma trận quyết định Buffett–Munger.
- Toàn bộ presentation layer tuân thủ thuần tiếng Việt, không chứa raw machine code hay enum backend.

## Acceptance Criteria

- [x] AC1: User mới đọc Guide có thể hiểu QPort Terminal dùng để làm gì.
- [x] AC2: User biết cách xem portfolio trong Terminal.
- [x] AC3: User biết cách thêm vị thế (Symbol Suggest autocomplete, validation).
- [x] AC4: User biết nhập quantity (số lượng cổ phiếu thực tế).
- [x] AC5: User biết nhập average cost (giá vốn bình quân đơn vị VND đầy đủ).
- [x] AC6: User biết sửa/xóa vị thế và phân biệt rõ xóa position vs dữ liệu BCTC.
- [x] AC7: User hiểu cách quản lý tiền mặt trong danh mục.
- [x] AC8: User hiểu dữ liệu danh mục độc lập với dữ liệu BCTC doanh nghiệp.
- [x] AC9: User hiểu nguồn dữ liệu tài chính đến từ BCTC SSI đã canonicalize.
- [x] AC10: User hiểu 12 chiều chất lượng & phân tích định giá Buffett/Munger.
- [x] AC11: Tuyệt đối không có backend enum xuất hiện trực tiếp trong User Guide.
- [x] AC12: Không có `N/A`, `nullx`, `undefined` trong nội dung hướng dẫn nếu có semantic tương ứng.
- [x] AC13: Giao diện responsive trên cả desktop và mobile.
- [x] AC14: Frontend build pass (`npm run build`).

## Constraints and Invariants

- Không thay đổi business logic, API, database, valuation hay portfolio engine.
- Sử dụng tiếng Việt chuẩn mực tài chính, rõ ràng và dễ tiếp cận.

## Implementation Tasks

- [x] Task 1: Thiết kế cấu trúc các section mới và mở rộng cho `frontend/src/pages/GuidePage.jsx`.
- [x] Task 2: Cập nhật styling trong `frontend/src/guide-friendly.css` hỗ trợ bảng so sánh, code blocks, callouts, warning boxes, pills TOC.
- [x] Task 3: Viết đầy đủ nội dung 12 sections theo đúng yêu cầu và tiêu chí nghiệm thu.
- [x] Task 4: Kiểm tra và xác nhận không có enum leakage hay chuỗi rác kỹ thuật.
- [x] Task 5: Chạy kiểm thử build frontend (`npm --prefix frontend run build` - PASS).
- [x] Task 6: Cập nhật task note sang `verified` -> `completed` và cập nhật `docs/tasks/README.md`.
- [x] Task 7: Commit và push lên `origin/feature/buffett-munger-refactor`.

## Validation Evidence

- **Frontend build test**:
  ```bash
  npm --prefix frontend run build
  # Output:
  # vite v6.4.3 building for production...
  # ✓ 114 modules transformed.
  # ✓ built in 1.80s
  ```
- **Enum Leakage Check**: Grep kiểm tra trên `GuidePage.jsx` không phát hiện bất kỳ mã enum backend nào (`PROFIT_CASH_DIVERGENCE`, `UNKNOWN`, `NOT_APPLICABLE`, `nullx`, v.v.).

## Decisions

- Bổ sung thanh điều hướng nhanh dạng viên thuốc (`guide-nav-pills`) ở đầu trang giúp người dùng nhảy tức thì đến các chủ đề mong muốn trên cả thiết bị di động và máy tính để bàn.
- Phân biệt rõ ràng bằng cảnh báo màu cam (warning callout) giữa việc Xóa vị thế cá nhân trên Terminal và Kho dữ liệu BCTC doanh nghiệp.
- Mọi thuật ngữ Value Trap được diễn đạt trọn vẹn bằng tiếng Việt chuẩn ngữ nghĩa tài chính.

## Result

- Trang Guide được đại tu hoàn chỉnh, cung cấp hướng dẫn rõ ràng, trực quan, chuyên nghiệp cho người dùng mới và người dùng hiện tại về QPort Terminal.
- Toàn bộ 14 Acceptance Criteria đạt 100%.
