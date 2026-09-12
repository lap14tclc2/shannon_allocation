# TASK-20260912-156: Auto Corporate Action Position & Cost Basis Adjustment

- **ID**: TASK-20260912-156
- **Title**: Auto Corporate Action Position & Cost Basis Adjustment
- **Status**: completed
- **Priority**: high
- **Date**: 2026-09-12

---

## Requirement

1. Cung cấp cơ chế tự động chuẩn hóa số lượng cổ phiếu và giá vốn bình quân cho các vị thế trong danh mục sau các sự kiện chia tách cổ phiếu / cổ tức bằng cổ phiếu / thưởng cổ phiếu (Stock Dividend / Bonus Share / Stock Split).
2. Khi thực hiện chuẩn hóa:
   - Tổng vốn đầu tư (Total Invested Capital) được bảo toàn 100%.
   - Số lượng cổ phiếu tự động nhân với hệ số tích lũy chia tách $F = \prod (1 + r_i)$.
   - Giá vốn bình quân tự động chia cho hệ số $F$.
   - Lãi/lỗ (%) và (VND) phản ánh đúng thực tế, loại bỏ hiện tượng "lỗ ảo" do giá thị trường đã điều chỉnh kỹ thuật.
3. Tích hợp trực tiếp trên Terminal UI (qua nút "Tự động chuẩn hóa cổ tức" hoặc trong modal Sửa vị thế).
4. Viết unit tests kiểm thử logic tính toán hệ số và bảo toàn bất biến sổ cái.

## Context

- Backend: `portfolio/storage.py`, `portfolio/correctable_service.py`, `portfolio/service.py`, `app/main.py`.
- Frontend: `frontend/src/pages/TerminalPage.jsx`, `frontend/src/lib/api.js`.
- Database: `qport_finance.dividend_canonical`, `corporate_actions`.

## Acceptance Criteria

- [x] AC1: Backend endpoint `POST /api/portfolio/positions/{symbol}/auto-split-adjust` hoặc hàm dịch vụ tính đúng hệ số chia tách tích lũy từ `dividend_canonical` / `corporate_actions`.
- [x] AC2: Tổng vốn đầu tư trước và sau khi chuẩn hóa bằng nhau tuyệt đối.
- [x] AC3: Số lượng và giá vốn sau chuẩn hóa khớp với hệ số chia tách.
- [x] AC4: Terminal UI cho phép người dùng kích hoạt tự động chuẩn hóa 1-click hoặc xem trước số lượng/giá vốn đề xuất.
- [x] AC5: Toàn bộ unit tests pass, frontend build pass.

## Constraints and Invariants

1. Buy & Hold Information System: Không tự ý sinh lệnh Mua/Bán trên sàn.
2. Ledger Invariant: Tổng vốn đầu tư ban đầu không bị thay đổi; chỉ quy đổi tương đương giữa số lượng và giá vốn bình quân.

## Implementation Tasks

- [x] Task 1: Xây dựng service logic tính toán hệ số chia tách tích lũy (`cumulative_split_factor`) trong `CorrectablePortfolioService`.
- [x] Task 2: Thêm API endpoint `/api/portfolio/positions/{symbol}/auto-split-adjust` trong `app/main.py` và client api `frontend/src/lib/api.js`.
- [x] Task 3: Bổ sung nút/tùy chọn "Chuẩn hóa cổ tức cổ phiếu" trong `PositionForm` và bảng vị thế trên `TerminalPage.jsx`.
- [x] Task 4: Viết unit tests trong `python/portfolio/tests/test_auto_split_adjust.py`.
- [x] Task 5: Chạy test, build frontend, cập nhật task note sang `completed`, commit và push.

## Validation Evidence

- Unit tests: `python/portfolio/tests/test_auto_split_adjust.py` -> 2/2 passed in 4.86s.
- Suite tests: 27/27 passed in 16.07s.
- Frontend build: `npm --prefix frontend run build` -> 0 errors.

## Decisions

- Lấy các sự kiện `STOCK_DIVIDEND`, `BONUS_SHARE`, `SPLIT` từ `dividend_canonical` / `corporate_actions` có trạng thái xác thực (`VERIFIED` / `SINGLE_SOURCE`).
- Người dùng luôn có quyền xem trước số lượng và giá vốn mới trước khi áp dụng.

## Result

- Hoàn tất tính năng tự động chuẩn hóa số lượng và giá vốn sau chia tách/cổ tức cổ phiếu.
- Tích hợp nút ⚡ Chia tách trên từng dòng vị thế và banner gợi ý tự động điền trong modal Chỉnh sửa vị thế trên Terminal.
