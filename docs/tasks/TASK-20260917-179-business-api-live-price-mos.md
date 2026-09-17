# TASK-20260917-179: Live Market Price Fetch in Business Analysis API to compute accurate MOS

- **ID**: TASK-20260917-179
- **Title**: API Business phải lấy giá thị trường hiện tại trực tiếp từ sàn để tính Biên an toàn (MOS)
- **Status**: completed
- **Priority**: high
- **Date**: 2026-09-17

---

## Requirement
Người dùng yêu cầu: API Business (`GET /api/portfolio/business/{symbol}`) phải lấy giá thị trường hiện tại trực tiếp từ sàn giao dịch để tính Biên an toàn (MOS) chính xác theo thời gian thực thay vì sử dụng giá cũ trong database.

---

## Context
Khi người dùng truy cập trang phân tích Business Workspace (`/business/{symbol}`), endpoint `GET /api/portfolio/business/{symbol}` gọi `build_canonical_valuation(ticker)` để tính toán định giá và phân tích Munger.
Trước đây, hệ thống chỉ đọc giá từ bảng `market_prices` trong database nếu đã có sẵn (kể cả giá cũ nhiều ngày trước), dẫn đến MOS và các cổng quyết định Munger bị tính theo thị giá cũ.

Cần bổ sung logic tự động gọi `AutoMarketData.daily_history_with_source(ticker, ..., force_refresh=True)` khi phân tích chi tiết mã trên Business Workspace, cập nhật giá mới vào database và tính toán lại MOS theo thị giá mới nhất.

---

## Acceptance Criteria
- [x] Endpoint `GET /api/portfolio/business/{symbol}` gọi live market price fetch trực tiếp từ sàn qua `AutoMarketData` (bỏ qua cache).
- [x] Giá mới nhất được ghi vào cả `svc.store.market_prices` và `qport_finance.market_prices`.
- [x] MOS (`actual_mos_pct`), giá hiện tại (`current_price`), và toàn bộ quyết định Munger phản ánh đúng thị giá mới nhất.
- [x] Unit tests và frontend build chạy thành công 100%.

---

## Constraints and Invariants
- `BUY_AND_HOLD_INFORMATION_SYSTEM`: Không làm thay đổi số dư giao dịch hay số lượng cổ phiếu nắm giữ.
- Error resilience: Nếu nhà cung cấp dữ liệu giá tạm thời lỗi mạng trên một mã, fallback an toàn về giá gần nhất đã lưu mà không gây lỗi 500.

---

## Implementation Tasks
- [x] Cập nhật `app/main.py`: Thêm live market price fetch trong `api_portfolio_business`.
- [x] Cập nhật `python/portfolio/canonical_valuation.py`: Đảm bảo giá live được ưu tiên khi tính toán MOS.
- [x] Viết test xác nhận trong `python/portfolio/tests/test_business_api_live_price.py`.

---

## Related Notes
- [TASK-20260917-178](file:///c:/workspace/shannon_allocation/docs/tasks/TASK-20260917-178-force-live-market-price-refresh.md)
- [TASK-20260912-158](file:///c:/workspace/shannon_allocation/docs/tasks/TASK-20260912-158-business-munger-candidates-valuation-navigation.md)

---

## Validation Evidence
1. **Live Business API Execution**:
   - `FPT`: Live Price 73,600.0 VND, Base IV 95,282.6 VND, MOS 22.76% (tính chính xác theo giá live hiện tại).
2. **Pytest Suite**:
   `$env:PYTHONPATH="python"; & "$HOME\.venv\Scripts\python.exe" -m pytest python/portfolio/tests/test_business_api_live_price.py`
   -> `1 passed in 15.47s`
3. **Frontend Build**:
   `npm run build` in `frontend/` -> `built in 4.52s` with 0 errors.

---

## Decisions
- Fetch live market price ngay tại đầu endpoint `api_portfolio_business` để cả `runtime_decision` và `build_canonical_valuation` đều đồng bộ trên cùng một thị giá live mới nhất.

---

## Result
Đã kích hoạt thành công tính năng tự động tải giá thị trường live từ sàn khi gọi API Business, đảm bảo MOS và phân tích Munger luôn phản ánh thị giá chính xác nhất.
