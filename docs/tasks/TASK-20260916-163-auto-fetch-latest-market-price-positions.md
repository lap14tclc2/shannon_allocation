# TASK-20260916-163 — Auto-Fetch Latest Market Price on Positions View

| Field | Value |
|---|---|
| status | in-progress |
| created | 2026-09-16 |
| task-id | TASK-20260916-163 |

---

## Requirement

Cập nhật hàm `positions_view()` trong `CorrectablePortfolioService` (và endpoint `/api/portfolio/positions`) để tự động đồng bộ/cập nhật giá thị trường mới nhất từ provider (AutoMarketData/VNDirect/Vnstock) cho các mã vị thế chưa có giá hoặc giá trong local store chưa phải là ngày mới nhất, giúp giao diện Terminal / Positions luôn hiển thị giá và lãi/lỗ cập nhật theo thị trường.

## Context

Hiện tại `positions_view()` chỉ gọi `self.store.latest_prices(symbols)` mà không kích hoạt đồng bộ giá online. Do đó nếu chưa bấm `POST /api/portfolio/sync` hoặc background sync chưa chạy, positions chỉ hiển thị giá cũ trong DB SQLite local.

## Acceptance Criteria

- [ ] `positions_view()` tự động kiểm tra và cập nhật giá mới nhất từ `AutoMarketData` / `_sync_symbol()` cho các mã nắm giữ.
- [ ] Không làm gãy fallback hay gây ngoại lệ 500 nếu provider bên ngoài lỗi hoặc offline (graceful fallback về giá lưu trữ sẵn hoặc unavailable).
- [ ] Giữ nguyên các bất biến hệ thống (Ledger invariant: giá không làm thay đổi số lượng cổ phiếu).
- [ ] Tất cả unit tests trong `python/portfolio/tests/test_terminal_portfolio_positions.py` và liên quan đều PASS.

## Constraints and Invariants

- BUY_AND_HOLD_INFORMATION_SYSTEM: Giá thị trường chỉ dùng để mark-to-market định giá và tính lãi lỗ, không bao giờ thay đổi số lượng cổ phiếu hay phát sinh giao dịch.
- Graceful degradation: nếu provider offline hoặc timeout, dùng giá gần nhất trong store hoặc đánh dấu UNAVAILABLE mà không làm crash API.

## Implementation Tasks

- [ ] Cập nhật `CorrectablePortfolioService.positions_view()` trong `python/portfolio/correctable_service.py` để sync giá mới nhất cho các symbol có vị thế `shares > 0`.
- [ ] Chạy test `test_terminal_portfolio_positions.py` và các test liên quan để verify.
- [ ] Ghi lại Validation Evidence và hoàn tất task.

## Related Notes

- [docs/tasks/TASK-20260912-150-terminal-portfolio-position-management.md](file:///c:/workspace/shannon_allocation/docs/tasks/TASK-20260912-150-terminal-portfolio-position-management.md)
- [python/portfolio/correctable_service.py](file:///c:/workspace/shannon_allocation/python/portfolio/correctable_service.py)

## Decisions

- Thực hiện đồng bộ giá trong `positions_view()` với try-except an toàn để đảm bảo tốc độ và không gián đoạn nếu mất kết nối mạng.

## Validation Evidence

- (Sẽ cập nhật sau khi chạy pytest)

## Result

- (Sẽ cập nhật khi hoàn tất)
