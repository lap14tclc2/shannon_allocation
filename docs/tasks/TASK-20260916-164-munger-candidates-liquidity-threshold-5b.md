# TASK-20260916-164 — Munger Candidates Liquidity Threshold >= 5B VND/day & Volume Calculation Logic

| Field | Value |
|---|---|
| status | completed |
| created | 2026-09-16 |
| task-id | TASK-20260916-164 |

---

## Requirement

1. Làm rõ và giải thích logic tính khối lượng (volume) & giá trị giao dịch (trading value turnover) của các mã chứng khoán.
2. Cập nhật logic đánh giá thanh khoản (`classify_liquidity`) và lọc ứng viên đầu tư (`/api/portfolio/business-candidates`) theo chuẩn giá trị giao dịch bình quân >= 5.0 tỷ VND/ngày (ngưỡng `LIQUIDITY_ACCEPTABLE` đạt chuẩn).
3. Hỗ trợ query parameter `min_val_billion` trên endpoint `GET /api/portfolio/business-candidates` và client `getMungerCandidates()` trong frontend.

## Context

Người dùng yêu cầu tìm kiếm và giải thích logic lấy volume giao dịch của mã chứng khoán, đồng thời cập nhật logic lấy các công ty có giá trị giao dịch > 5 tỷ đồng/ngày trên endpoint `/api/portfolio/business-candidates?tier=all&search=6&limit=50`.

## Acceptance Criteria

- [x] Logic tính khối lượng & giá trị giao dịch được ghi nhận chuẩn xác từ bảng PostgreSQL `qport_finance.market_prices` (lấy 20 & 60 phiên gần nhất, tính `close * volume`).
- [x] `classify_liquidity()` nâng ngưỡng `LIQUIDITY_ACCEPTABLE` từ 1.0 tỷ lên >= 5.0 tỷ VND/ngày (hoặc volume >= 200k cp/ngày), các mã dưới 5.0 tỷ được phân loại `LIQUIDITY_WEAK`.
- [x] Endpoint `GET /api/portfolio/business-candidates` và `get_munger_candidates()` hỗ trợ `min_val_billion` (float).
- [x] Client `frontend/src/lib/api.js:getMungerCandidates()` hỗ trợ `minTradingValue`.
- [x] Toàn bộ test suite `test_munger_liquidity_gate.py` và `test_munger_candidates_and_valuation_navigation.py` PASS.

## Constraints and Invariants

- Bất biến sổ cái & BUY_AND_HOLD_INFORMATION_SYSTEM: Dữ liệu thanh khoản chỉ dùng cho mục đích cảnh báo và lọc quy mô giải ngân, không làm thay đổi sổ cái hay số lượng cổ phiếu.
- Độc lập: Thanh khoản không làm ghi đè đánh giá chất lượng tài chính cốt lõi (Munger Moat/ROE).

## Implementation Tasks

- [x] Cập nhật `python/portfolio/value_engine/liquidity_evaluator.py`: nâng ngưỡng phân loại `LIQUIDITY_ACCEPTABLE` lên >= 5.0 tỷ VND/ngày.
- [x] Cập nhật `python/portfolio/value_engine/munger_candidates.py`: thêm `min_val_billion` và fix hàm rationale generator.
- [x] Cập nhật `app/main.py`: nhận query param `min_val_billion` tại `/api/portfolio/business-candidates`.
- [x] Cập nhật `frontend/src/lib/api.js`: thêm tham số `minTradingValue`.
- [x] Viết unit tests trong `python/portfolio/tests/test_munger_liquidity_gate.py`.

## Related Notes

- [docs/tasks/TASK-20260912-162-munger-liquidity-gate-and-semantic-audit.md](file:///c:/workspace/shannon_allocation/docs/tasks/TASK-20260912-162-munger-liquidity-gate-and-semantic-audit.md)
- [python/portfolio/value_engine/liquidity_evaluator.py](file:///c:/workspace/shannon_allocation/python/portfolio/value_engine/liquidity_evaluator.py)
- [python/portfolio/value_engine/munger_candidates.py](file:///c:/workspace/shannon_allocation/python/portfolio/value_engine/munger_candidates.py)

## Decisions

- Sử dụng giá trị giao dịch bình quân 20 phiên (`avg_trading_value_20d_billion = sum(close * volume) / 20 / 1e9`) làm thước đo chuẩn xác nhất cho thanh khoản thị trường tại Việt Nam (thay vì chỉ dùng khối lượng cổ phiếu thuần túy, tránh sai lệch giữa cổ phiếu thị giá 10k và 100k).

## Validation Evidence

```text
pytest python/portfolio/tests/test_munger_liquidity_gate.py python/portfolio/tests/test_munger_candidates_and_valuation_navigation.py
======================== 13 passed, 2 skipped in 0.71s ========================
```

## Result

- Hoàn thành thiết lập cổng lọc cứng: toàn bộ cổ phiếu có giá trị giao dịch bình quân < 5.0 tỷ VNĐ/ngày (như CMF 0.04B, HLB 0.04B, các mã < 5B) bị loại bỏ khỏi danh sách ứng viên Munger.
- Mặc định API `/api/portfolio/business-candidates` chỉ trả về các cổ phiếu có thanh khoản >= 5.0 tỷ VNĐ/ngày.
