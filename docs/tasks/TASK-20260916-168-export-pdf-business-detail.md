# TASK-20260916-168: Export PDF Feature on Business Analysis Detail Page

## Metadata
- **ID**: `TASK-20260916-168`
- **Title**: Export PDF Feature on Business Analysis Detail Page
- **Status**: completed
- **Priority**: medium
- **Date**: 2026-09-16
- **Branch**: `feature/buffett-munger-refactor`

---

## Requirement
Người dùng yêu cầu bổ sung nút **"Xuất PDF"** nằm ngay bên cạnh nút **"Xuất dữ liệu cho AI"** trong trang chi tiết phân tích BCTC Munger (`/business/:symbol`).

## Context & Architecture
- Hiện tại, trang chi tiết `BusinessPage.jsx` có nút `Xuất dữ liệu cho AI` (`🤖 Xuất dữ liệu cho AI`) tải về file Markdown tổng hợp BCTC 12 chiều, bẫy giá trị, sức mạnh lợi nhuận chuẩn hóa và payload JSON cho AI.
- Người dùng cần một nút xuất định dạng PDF chuyên nghiệp để lưu trữ hoặc in ấn/chia sẻ báo cáo phân tích BCTC Munger cho doanh nghiệp đang xem.
- Giải pháp chuẩn mực:
  1. Thêm nút `Xuất PDF` (`📄 Xuất PDF`) bên cạnh `Xuất dữ liệu cho AI` với loading state và disabled state tương ứng.
  2. Triển khai hàm `handleExportPDF`:
     - Tự động đặt tên tài liệu in ấn chuẩn: `Bao_Cao_Munger_[SYMBOL]_[YYYY-MM-DD]`.
     - Kích hoạt in trình duyệt `window.print()` (hỗ trợ Lưu thành PDF / Save as PDF với đầy đủ font chữ tiếng Việt, màu sắc, bảng biểu).
  3. Thêm bộ quy tắc `@media print` trong CSS:
     - Ẩn thanh điều hướng `AppNav`, thanh tìm kiếm, các nút bấm hành động (`Xuất dữ liệu cho AI`, `Xuất PDF`), các element không cần thiết khi in.
     - Bảo toàn màu sắc bảng biểu, badge xếp hạng và thẻ tài chính (`print-color-adjust: exact`).
     - Tránh ngắt trang dở dang giữa chừng ở các thẻ và bảng phân tích (`break-inside: avoid`).

## Acceptance Criteria
- [x] Nút `Xuất PDF` (`📄 Xuất PDF`) xuất hiện ngay bên cạnh nút `Xuất dữ liệu cho AI` trên header trang chi tiết `/business/:symbol`.
- [x] Khi click, gọi hàm `handleExportPDF`:
  - Thiết lập tiêu đề in ấn chuẩn hoá cho file PDF: `Bao_Cao_BCTC_Munger_[SYMBOL]_[YYYY-MM-DD]`.
  - Mở hộp thoại in / Save as PDF của trình duyệt.
- [x] Stylesheet `@media print` tối ưu hóa trang in:
  - Ẩn thanh điều hướng, ô tìm kiếm và các nút bấm.
  - Giữ nguyên màu sắc, background các badge và layout chuyên nghiệp (`-webkit-print-color-adjust: exact`).
  - Tránh ngắt trang dở dang (`break-inside: avoid`).
- [x] Không ảnh hưởng đến giao diện thông thường hay các trang khác.

## Constraints and Invariants
- Giữ nguyên toàn bộ layout desktop và mobile hiện có.
- Không thêm dependency bên ngoài không cần thiết.

## Implementation Tasks
- [x] Cập nhật `frontend/src/pages/BusinessPage.jsx`:
  - Thêm state `exportingPDF`.
  - Viết hàm `handleExportPDF`.
  - Render nút `Xuất PDF` bên cạnh nút `Xuất dữ liệu cho AI`.
- [x] Bổ sung CSS `@media print` trong `frontend/src/ui-polish.css` cho `BusinessPage`.
- [x] Kiểm thử build frontend (`npm run build`) và automated test suite.

## Validation Evidence
1. **Frontend Build Verification**:
   - `npm run build` in `frontend/`: `built in 1.75s` thành công không có lỗi cú pháp.
2. **Nút Export PDF**:
   - Nút `📄 Xuất PDF` xuất hiện ngay cạnh `🤖 Xuất dữ liệu cho AI`.
   - Gọi `handleExportPDF()`, đặt tên tệp in tự động `Bao_Cao_BCTC_Munger_[SYMBOL]_[YYYY-MM-DD]` và kích hoạt `window.print()`.
3. **Print Stylesheet (@media print)**:
   - Ẩn các thanh điều hướng (`AppNav`), nút bấm action (`.export-ai-btn`, `.export-pdf-btn`), input tìm kiếm.
   - Giữ nguyên toàn bộ màu sắc thẻ và bảng điểm Munger 12 chiều, thẻ định giá và bẫy giá trị.
4. **Automated Tests**:
   - `pytest`: 13 passed in 10.63s.

## Result
Đã hoàn thành thêm nút "Xuất PDF" bên cạnh "Xuất dữ liệu cho AI" với trải nghiệm in ấn / Lưu thành PDF chuẩn mực, đẹp mắt và sắc nét.
