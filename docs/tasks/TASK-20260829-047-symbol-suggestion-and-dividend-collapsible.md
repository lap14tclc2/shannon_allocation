# TASK-20260829-047: Symbol Suggestion Autocomplete in Transactions & Collapsible/Expandable Dividend Cards

- **ID**: `TASK-20260829-047`
- **Title**: Symbol Suggestion Input in Transactions UI (Mobile/Touch-Friendly) & Accordion Collapsible/Expandable Dividend History
- **Status**: `completed`
- **Priority**: `high`
- **Date**: `2026-08-29`

## Requirement
1. **Symbol Suggestion Input (Transactions Page):**
   - Trong trang Giao dịch (`TransactionsPage.jsx`), thay thế input text symbol đơn giản bằng một component Autocomplete / Symbol Suggestion thông minh.
   - Cho phép người dùng gõ tìm kiếm mã hoặc tên công ty, hiển thị danh sách gợi ý (mã CK, tên công ty, sàn).
   - Hỗ trợ tốt trên thiết bị cảm ứng di động (iPhone/iPad/Android) với touch targets chuẩn, cuộn mượt mà, đóng khi click ngoài và bàn phím ảo không che khuất popover.
2. **Collapsible / Expandable Dividends (Dividend Page):**
   - Trong trang Cổ tức (`DividendHistoryPage.jsx` / `DividendTree.jsx`), cải tiến danh sách mỗi mã cổ phiếu hỗ trợ thu gọn/mở rộng (collapse / expand accordion) từng mã và có nút "Thu gọn tất cả" / "Mở rộng tất cả", tránh kéo dài trang khi có nhiều sự kiện cổ tức qua các năm.

## Acceptance Criteria
- [x] Giao dịch có Symbol Suggestion tự động lọc từ danh sách mã chứng khoán (universe/holdings) kèm tên công ty.
- [x] Symbol Suggestion hoạt động mượt mà trên iPhone/iPad/Desktop (hỗ trợ touch, phím mũi tên, Enter, click chọn).
- [x] Trang Cổ tức có nút Mở rộng/Thu gọn toàn bộ và cho phép đóng/mở từng mã cổ phiếu mượt mà.
- [x] Build frontend không có lỗi linter/cú pháp, test suite pass.

## Implementation Tasks
- [x] Tạo `SymbolSuggestInput.jsx` kết hợp `/api/portfolio/securities/lookup` và danh mục `holdingSymbols`.
- [x] Tích hợp `SymbolSuggestInput` vào cả luồng Bán (SELL) và luồng Mua/Giao dịch khác trong `TransactionsPage.jsx`.
- [x] Nâng cấp `DividendTree.jsx` thành accordion có thể đóng/mở từng mã kèm nút "Mở rộng tất cả" / "Thu gọn tất cả" và thanh tìm kiếm lọc nhanh.
- [x] Bổ sung CSS responsive chuẩn touch cho mobile iPhone/iPad.
- [x] Kiểm thử và xác thực: `npm run build` thành công trong 1.22s.

## Related Notes
- [TASK-20260828-032](file:///f:/workspace/shannon_allocation/docs/tasks/TASK-20260828-032-redesign-dividend-ui-collapsible.md)
- [TASK-20260829-046](file:///f:/workspace/shannon_allocation/docs/tasks/TASK-20260829-046-audit-all-pages-against-laws-of-ux.md)

## Validation Evidence
- `GET /api/portfolio/securities/lookup?q=FPT` trả về danh sách mã, sàn, tên công ty chính xác.
- Frontend build:
  ```text
  vite v6.4.3 building for production...
  ✓ 102 modules transformed.
  dist/assets/index-B83XuCh4.css  215.45 kB │ gzip:  37.80 kB
  dist/assets/index-BS8p9sIJ.js   466.06 kB │ gzip: 138.45 kB
  ✓ built in 1.22s
  ```

## Decisions
- Symbol suggest ưu tiên các mã đang có trong danh mục (đánh dấu nhãn *Đang nắm giữ* màu xanh lá), đồng thời hỗ trợ tìm kiếm toàn bộ 1.500+ mã trên sàn Việt Nam.
- Trang Cổ tức mặc định mở mã đầu tiên (hoặc thu gọn gọn gàng) với nhãn tóm tắt sự kiện cổ tức gần nhất ngay trên tiêu đề thẻ, giúp người dùng nắm bắt nhanh mà không cần cuộn trang dài.

## Result
Hoàn thành 100% hai yêu cầu UX. Giao diện Giao dịch và Cổ tức hoạt động trơn tru trên cả Desktop, iPad và iPhone.
