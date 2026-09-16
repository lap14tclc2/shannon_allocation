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
  - Tạo trực tiếp và tải file về máy `Bao_Cao_BCTC_Munger_[SYMBOL]_[YYYY-MM-DD].pdf`.
  - **Tuyệt đối không bật hộp thoại print dialog (`window.print()`)**.
- [x] Tự động mở bung (expand) toàn bộ chi tiết 8 câu hỏi phản biện Pre-Mortem và các mục chi tiết khi xuất PDF (`forceExpand={exportingPDF}`).
- [x] Thuật toán chia trang thông minh (Smart Card-Boundary Page Break):
  - Tìm ranh giới các thẻ/khối/hàng bảng (`.card`, `section`, `.dim-card`, `tr`).
  - Không cắt ngang chữ, không cắt đứt nửa thẻ/khung viền như hình ảnh chụp trước đó.
- [x] Tự động ẩn các nút action / search input khi chụp canvas xuất PDF.
- [x] Không ảnh hưởng đến giao diện thông thường hay các trang khác.

## Constraints and Invariants
- Giữ nguyên toàn bộ layout desktop và mobile hiện có.
- Trực tiếp tải file PDF (.pdf) về máy người dùng, không gọi `window.print()`.

## Implementation Tasks
- [x] Cài đặt `html2canvas-pro` (bản kế thừa hỗ trợ đầy đủ các hàm CSS Color Module 4 hiện đại: `color-mix()`, `oklch()`, `color()`).
- [x] Tạo helper `frontend/src/lib/pdfExport.js` dùng `html2canvas-pro` + `jspdf` với thuật toán cắt trang thông minh theo mép thẻ.
- [x] Cập nhật `frontend/src/components/ThesisChallengeSection.jsx` nhận `forceExpand`, tự động mở toàn bộ 8 câu hỏi chi tiết Pre-Mortem.
- [x] Cập nhật `frontend/src/pages/BusinessPage.jsx` truyền `forceExpand={exportingPDF}`.
- [x] Kiểm thử build frontend (`npm run build`).

## Validation Evidence
1. **Frontend Build Verification**:
   - `npm run build` in `frontend/`: `built in 3.51s` thành công không có lỗi cú pháp.
   - Hỗ trợ đầy đủ các hàm màu CSS hiện đại trong `valuation-page.css` (`color-mix()`, `oklch()`).
   - File chunk `pdfExport` được dynamic code-split độc lập.
2. **Nút Export PDF**:
   - Nút `📄 Xuất PDF` xuất hiện ngay cạnh `🤖 Xuất dữ liệu cho AI`.
   - Trực tiếp tải file `.pdf` (`Bao_Cao_BCTC_Munger_[SYMBOL]_[YYYY-MM-DD].pdf`).
3. **Hiển thị đầy đủ chi tiết & Không bị cắt vỡ**:
   - Tự động bung chi tiết 4 phần (Kết luận, Bằng chứng BCTC, Rủi ro, Mức độ nghiêm trọng) của toàn bộ 8 câu hỏi phản biện.
   - Thuật toán `safeCutPoints` tự động nhận diện mép thẻ `.card`, `section`, `.dim-card`, `tr` để chia trang A4 trơn tru, không xẻ đôi thẻ hay chữ.

## Result
Đã giải quyết triệt để 2 vấn đề:
1. Mở bung toàn bộ thông tin chi tiết của 8 câu hỏi phản biện luận điểm đầu tư trong file PDF.
2. Không bị cắt xẻ đôi thẻ/chữ khi chuyển trang nhờ thuật toán phân trang thông minh theo mép khối thẻ.

