# QPort TODO

Các TODO dưới đây là chủ đích kiến trúc, chưa được triển khai trong nhánh hiện tại.

## Persistence

- [ ] **Migrate Vercel Neon → spreadsheet-backed persistence.**
  - Xác định spreadsheet backend cụ thể và giới hạn API/quota trước khi migration.
  - Giữ nguyên isolation theo user, thứ tự giao dịch, correction/audit history, corporate actions và daily snapshots.
  - Thiết kế concurrency/locking và atomic-write strategy trước khi cho phép nhiều request cùng ghi dữ liệu.
  - Có export/import validator để đối chiếu NAV, holdings, cash, tax lots, P/L và lịch sử giao dịch trước/sau migration.
  - Có rollback path; không xóa Neon trước khi dữ liệu spreadsheet được kiểm chứng đầy đủ.

## Symbol lifecycle khi bán hết

- [ ] **Xử lý toàn bộ dữ liệu liên quan khi số lượng một symbol về 0.**
  - Symbol không còn xuất hiện trong danh sách `đang nắm giữ`, nhưng tuyệt đối không xóa lịch sử giao dịch.
  - Giữ tax lots đã đóng, realized P/L, cổ tức/quyền đã phát sinh, corporate actions, snapshot và bằng chứng dùng để tính performance.
  - Xác định policy dừng/giảm tần suất refresh market data và dividend data cho vị thế đã đóng.
  - Trang lịch sử phải vẫn truy cập được dữ liệu của symbol đã bán hết khi cần audit/reconciliation.
  - Nếu mua lại cùng symbol, phải tái sử dụng lịch sử an toàn và không tạo duplicate corporate-action/dividend events.
  - Bổ sung test cho vòng đời `BUY → SELL hết → closed → BUY lại` và kiểm chứng cost basis/performance không bị thay đổi ngược lịch sử.
