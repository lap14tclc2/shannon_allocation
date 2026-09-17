# TASK-20260917-178: Force Live Market Price Refresh on "Làm mới giá" button click

- **ID**: TASK-20260917-178
- **Title**: Gọi API lấy giá thị trường mới nhất trực tiếp từ sàn khi bấm nút "Làm mới giá"
- **Status**: completed
- **Priority**: high
- **Date**: 2026-09-17

---

## Requirement
Người dùng báo cáo: Khi bấm nút "Làm mới giá" trên giao diện danh mục (Terminal / Positions), hệ thống vẫn lấy lại giá cũ trong database thay vì gọi API lấy giá mới nhất từ sàn giao dịch (VNDirect / Vnstock).
Cần kích hoạt gọi API live fetch giá mới nhất trực tiếp khi người dùng bấm nút "Làm mới giá", lưu giá mới vào database và cập nhật lại toàn bộ bảng danh mục.

---

## Context
1. Hiện tại, `GET /api/portfolio/positions` gọi `svc.positions_view()`. Hàm này chỉ gọi `_sync_symbol` nếu ngày giao dịch gần nhất của mã trong database nhỏ hơn ngày hôm nay (`< today_str`).
2. Nếu trong ngày đã có một bản ghi giá (ví dụ giá mở cửa hoặc giá đóng cửa phiên trước được copy), logic kiểm tra coi như đã có dữ liệu và bỏ qua việc gọi API lấy giá mới.
3. Khi người dùng bấm nút "Làm mới giá" (hoặc truyền query param `refresh=true`), hệ thống cần:
   - Bỏ qua cache external và kiểm tra ngày cũ, gọi thẳng API provider (`VndirectProvider` / `AutoMarketData`) lấy giá mới nhất.
   - Upsert dữ liệu giá mới nhất vào bảng `market_prices` của user và shared schema `qport_finance.market_prices`.
   - Tính toán lại mark-to-market P&L và trả về dữ liệu danh mục cập nhật ngay lập tức.

---

## Acceptance Criteria
- [x] Endpoint `GET /api/portfolio/positions?refresh=true` hỗ trợ tham số `refresh=true` để kích hoạt force live price sync.
- [x] `positions_view(force_refresh=True)` duyệt qua các mã đang nắm giữ trong danh mục, gọi API lấy dữ liệu giá mới nhất trực tiếp từ provider (bỏ qua cache).
- [x] Dữ liệu giá mới được upsert vào cả `user_schema.market_prices` và `qport_finance.market_prices`.
- [x] `TerminalPage.jsx`: Nút "Làm mới giá" gọi `getPortfolioPositions(true)`, hiển thị trạng thái `Đang cập nhật giá mới…` và cập nhật lại bảng danh mục cùng lúc với dữ liệu phân tích Munger.
- [x] Unit tests và frontend build chạy thành công 100%.

---

## Constraints and Invariants
- `BUY_AND_HOLD_INFORMATION_SYSTEM`: Việc cập nhật giá chỉ thay đổi giá thị trường và lãi/lỗ chưa thực hiện (P&L), tuyệt đối không làm thay đổi số lượng cổ phiếu hay số dư tiền mặt.
- Phục hồi lỗi linh hoạt: Nếu API provider tạm thời timeout trên một mã cụ thể, giữ nguyên giá gần nhất và không làm crash toàn bộ endpoint.

---

## Implementation Tasks
- [x] Cập nhật `python/portfolio/market_data.py`: Hỗ trợ `force_refresh=True` trong `AutoMarketData.daily_history_with_source`.
- [x] Cập nhật `python/portfolio/service.py`: Hỗ trợ `force=True` trong `_sync_symbol` và upsert vào `qport_finance.market_prices`.
- [x] Cập nhật `python/portfolio/correctable_service.py`: Cập nhật `positions_view(force_refresh=True)`.
- [x] Cập nhật `app/main.py`: Hỗ trợ query parameter `refresh: bool = Query(default=False)` tại `/api/portfolio/positions`.
- [x] Cập nhật `frontend/src/lib/api.js`: `getPortfolioPositions(refresh = false)`.
- [x] Cập nhật `frontend/src/pages/TerminalPage.jsx`: Xử lý nút "Làm mới giá" với loading state và gọi force refresh.
- [x] Viết / cập nhật test trong `python/portfolio/tests/test_terminal_portfolio_positions.py`.

---

## Related Notes
- [TASK-20260916-163](file:///c:/workspace/shannon_allocation/docs/tasks/TASK-20260916-163-auto-fetch-latest-market-price-positions.md)
- [TASK-20260912-159](file:///c:/workspace/shannon_allocation/docs/tasks/TASK-20260912-159-terminal-decision-integrity.md)

---

## Validation Evidence
1. **Pytest Terminal Positions**:
   `$env:PYTHONPATH="python"; & "$HOME\.venv\Scripts\python.exe" -m pytest python/portfolio/tests/test_terminal_portfolio_positions.py`
   -> `24 passed in 10.70s`
2. **Live Python API Execution**:
   - `ACB`: 22,400.0 VND
   - `DGC`: 34,800.0 VND
   - `FPT`: 73,100.0 VND (lấy trực tiếp từ VNDirect)
3. **Frontend Build**:
   `npm run build` in `frontend/` -> `built in 3.25s` with 0 errors.

---

## Decisions
- Thêm cờ `force_refresh` xuyên suốt từ API request đến market data provider để đảm bảo lấy giá live thật sự khi người dùng bấm nút.

---

## Result
Đã kích hoạt thành công tính năng gọi API lấy giá thị trường mới nhất trực tiếp từ sàn khi bấm nút "Làm mới giá".
