# TASK-20260917-177: Thay filter thanh khoản thành các ngưỡng giá trị giao dịch (> 1 tỷ, > 5 tỷ, > 10 tỷ, > 20 tỷ)

- **ID**: TASK-20260917-177
- **Title**: Thay đổi bộ lọc thanh khoản thành các ngưỡng giá trị giao dịch thực tế (> 1 tỷ, > 5 tỷ, > 10 tỷ, > 20 tỷ)
- **Status**: completed
- **Priority**: high
- **Date**: 2026-09-17

---

## Requirement
Người dùng yêu cầu thay đổi bộ lọc thanh khoản (liquidity filter) trên giao diện thành các ngưỡng giá trị giao dịch:
`> 1 tỉ, > 5 tỷ, > 10 tỷ, > 20 tỷ` (kèm tùy chọn Tất cả).

---

## Context
Hiện tại, trên `BusinessPage.jsx`, bộ lọc thanh khoản đang chia theo nhãn phân loại cũ (`LIQUIDITY_STRONG`, `LIQUIDITY_ACCEPTABLE`, `LIQUIDITY_WEAK`, `LIQUIDITY_INSUFFICIENT_DATA`), và trên `ScreenerPage.jsx` danh sách ngưỡng chưa đủ mức 20 tỷ.
Đồng thời, trong backend `munger_candidates.py`, logic sàn thanh khoản cứng `< 5.0 tỷ/ngày` cần được hạ xuống `< 1.0 tỷ/ngày` để cho phép các cổ phiếu đạt mức `> 1 tỷ` hiển thị khi người dùng lọc theo mức này.

---

## Acceptance Criteria
- [x] `BusinessPage.jsx`: Bộ lọc thanh khoản ứng viên Munger hiển thị các tab: `Tất cả`, `> 1 tỷ`, `> 5 tỷ`, `> 10 tỷ`, `> 20 tỷ`.
- [x] `ScreenerPage.jsx`: Thêm tùy chọn `≥ 20 Tỷ / ngày` đầy đủ theo thứ tự `≥ 20 Tỷ`, `≥ 10 Tỷ`, `≥ 5 Tỷ`, `≥ 1 Tỷ`, `Tất cả`.
- [x] `frontend/src/lib/api.js`: `getMungerCandidates()` tự động map giá trị thanh khoản số (`1`, `5`, `10`, `20`) sang param `min_val_billion`.
- [x] `python/portfolio/value_engine/munger_candidates.py`:
  - Cho phép đánh giá ứng viên có thanh khoản từ `1.0 tỷ/ngày` trở lên (buffer SQL `0.8 tỷ/ngày`).
  - `get_munger_candidates()` lọc theo `min_val_billion` chính xác khi người dùng chọn tab tương ứng.
- [x] Unit tests và frontend build chạy thành công 100%.

---

## Constraints and Invariants
- `BUY_AND_HOLD_INFORMATION_SYSTEM`: Không thay đổi các tiêu chí chất lượng cơ bản của Buffett-Munger.
- Zero raw enum leakage.
- Đảm bảo hiệu năng API sub-second qua cache và multi-threading an toàn.

---

## Implementation Tasks
- [x] Cập nhật `python/portfolio/value_engine/munger_candidates.py` để hỗ trợ ngưỡng từ 1.0B VND/day.
- [x] Cập nhật `python/portfolio/tests/test_munger_liquidity_gate.py` tương ứng.
- [x] Cập nhật `frontend/src/lib/api.js` cho `getMungerCandidates`.
- [x] Cập nhật `frontend/src/pages/BusinessPage.jsx` với các tab `> 1 tỷ`, `> 5 tỷ`, `> 10 tỷ`, `> 20 tỷ`.
- [x] Cập nhật `frontend/src/pages/ScreenerPage.jsx` thêm tùy chọn `20 tỷ`.
- [x] Chạy unit tests và build frontend để xác nhận.

---

## Related Notes
- [TASK-20260916-164](file:///c:/workspace/shannon_allocation/docs/tasks/TASK-20260916-164-munger-candidates-liquidity-threshold-5b.md)
- [TASK-20260912-162](file:///c:/workspace/shannon_allocation/docs/tasks/TASK-20260912-162-munger-liquidity-gate-and-semantic-audit.md)

---

## Validation Evidence
1. **Pytest Liquidity Gate**:
   `$env:PYTHONPATH="python"; & "$HOME\.venv\Scripts\python.exe" -m pytest python/portfolio/tests/test_munger_liquidity_gate.py`
   -> `10 passed in 0.69s`
2. **Frontend Build**:
   `npm run build` in `frontend/` -> `built in 3.53s` with 0 errors.

---

## Decisions
- Dùng `min_val_billion` (1, 5, 10, 20) làm giá trị filter trực tiếp từ các tab thanh khoản.

---

## Result
Đã hoàn thành việc cập nhật toàn bộ hệ thống bộ lọc thanh khoản theo các ngưỡng giá trị giao dịch thực tế `> 1 tỷ`, `> 5 tỷ`, `> 10 tỷ`, `> 20 tỷ` trên `BusinessPage`, `ScreenerPage`, client API và backend engine.
