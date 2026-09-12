# TASK-20260912-147: Deep Audit and Fix N/A / Null Metrics across 12-Dimension Financial Engine

- **ID**: TASK-20260912-147
- **Title**: Deep Audit and Fix N/A / Null Metrics across 12-Dimension Financial Engine
- **Status**: completed
- **Priority**: high
- **Date**: 2026-09-12

---

## Requirement

Rà soát toàn bộ pipeline tính toán 12 chiều Financial Quality / Munger Analysis, loại bỏ triệt để các trạng thái raw `null`, `undefined`, `NaN`, `nullx`, `N/A` mơ hồ, `0.0%` giả tạo, `not applicable` thô trên UI.

Mục tiêu cốt lõi:
1. Tạo một Normalization & Diagnostics Layer trước API/UI để phân loại 100% metric thành: `VALUE`, `NOT_APPLICABLE`, `INSUFFICIENT_DATA`, `DATA_MISSING`, `CALCULATION_ERROR`.
2. Không bao giờ biến `null` thành `0` hoặc `0.0%`.
3. Khắc phục tận gốc (Root Cause) công thức tính Revenue Growth, PAT Growth, CFO/PAT, Debt/Equity, Profit Volatility trong backend (`munger_history_builder.py`, `munger_archetype_analyzers.py`, `munger_analyzer.py`).
4. Giữ nguyên tính độc lập giữa các mô hình đặc thù (`BANK`, `SECURITIES`, `NORMAL_ENTERPRISE`).
5. Chuẩn hóa toàn bộ nhãn tiếng Việt tại lớp centralized mapping (`vietnamese_presenter.py` và `vietnameseSemantics.js`).
6. Cập nhật `BusinessPage.jsx` và các UI component để hiển thị nhãn tiếng Việt chuẩn thay vì chuỗi thô.
7. Đạt 100% test regression trên 4 mã thử nghiệm **ACB**, **DGC**, **FPT**, **VIX**.

---

## Context

Trên branch `feature/buffett-munger-refactor`, phân tích 12 chiều Munger của QPort hiện tại thỉnh thoảng xuất các nhãn như `Debt/Equity: nullx`, `Tăng trưởng LNST: 0.0%`, `CFO/PAT: N/A`. Cần nâng cấp đồng bộ từ Data Lineage đến API Serialization và presentation layer để đáp ứng chuẩn tài chính cao cấp.

---

## Acceptance Criteria

- [x] Không có chuỗi `null`, `undefined`, `None`, `NaN`, `nullx`, `not applicable`, `N/A`, `UNKNOWN` thô xuất hiện trên UI end-user.
- [x] Dữ liệu thiếu (null) không bị chuyển đổi thành 0 hay 0.0% giả.
- [x] Tăng trưởng doanh thu và LNST được tính đúng từ lịch sử SSI/canonical khi có đủ >=2 năm.
- [x] Tỷ lệ CFO/PAT được tính đúng từ dòng tiền kinh doanh lịch sử và net profit.
- [x] Debt/Equity hiển thị chuẩn dạng `1.25x` cho doanh nghiệp sản xuất/thương mại, `Không áp dụng cho ngân hàng` cho Bank, `Thương lượng đòn bẩy tài chính` cho Securities.
- [x] Biến động lợi nhuận chỉ được tính khi có đủ chuỗi lịch sử (>=3 năm); nếu thiếu dữ liệu phải báo rõ lý do.
- [x] Centralized Vietnamese Presentation layer quy đổi tất cả trạng thái metric thành tiếng Việt tự nhiên.
- [x] Chạy regression test thành công 100% cho 4 golden symbols (ACB, DGC, FPT, VIX).
- [x] Build frontend `npm run build` thành công.

---

## Constraints and Invariants

1. Triết lý Buy & Hold (`BUY_AND_HOLD_INFORMATION_SYSTEM`).
2. Ledger Invariant: Biến động giá không thay đổi số lượng cổ phiếu.
3. KHÔNG hard-code giá trị tài chính cho bất kỳ mã nào.
4. KHÔNG hạ thấp tiêu chuẩn chất lượng để pass test (không default 0, không default PASS).
5. Phân tách rõ ràng giữa 3 mô hình doanh nghiệp (`BANK`, `SECURITIES`, `NORMAL_ENTERPRISE`).

---

## Implementation Tasks

- [x] Task 1: Audit & fix metric calculation root causes in `munger_archetype_analyzers.py` (CAGRs, CFO/PAT, Debt/Equity, Volatility).
- [x] Task 2: Implement Metric Data Diagnostic Object & Status Normalizer in `munger_models.py` & `munger_analyzer.py`.
- [x] Task 3: Centralize Vietnamese semantic mappings in `vietnamese_presenter.py` and `vietnameseSemantics.js`.
- [x] Task 4: Upgrade `BusinessPage.jsx` metric rendering helpers (`formatPct`, `formatVND`, `formatX`, `formatMetricValue`).
- [x] Task 5: Build regression tests for N/A & Null metric integrity across golden symbols (ACB, DGC, FPT, VIX).
- [x] Task 6: Audit and execute golden symbol pipeline audit script.
- [x] Task 7: Run frontend build `npm run build` and verify 0 build errors.

---

## Related Notes

- [TASK-20260912-146](file:///c:/workspace/shannon_allocation/docs/tasks/TASK-20260912-146-deep-financial-forensics-and-munger-pre-mortem.md)
- [munger_analyzer.py](file:///c:/workspace/shannon_allocation/python/portfolio/value_engine/munger_analyzer.py)
- [munger_archetype_analyzers.py](file:///c:/workspace/shannon_allocation/python/portfolio/value_engine/munger_archetype_analyzers.py)
- [vietnamese_presenter.py](file:///c:/workspace/shannon_allocation/python/portfolio/value_engine/vietnamese_presenter.py)
- [vietnameseSemantics.js](file:///c:/workspace/shannon_allocation/frontend/src/utils/vietnameseSemantics.js)

---

## Validation Evidence

```bash
# 1. Targeted Munger & N/A Null Metric Regression Tests
& "$HOME\.venv\Scripts\python.exe" -m pytest python/portfolio/tests/test_na_null_metrics_regression.py python/portfolio/tests/test_munger_financial_analysis.py python/portfolio/tests/test_munger_thesis_challenge.py python/portfolio/tests/test_vietnamese_semantics.py python/portfolio/tests/test_munger_pipeline_regression.py -o pythonpath=python
==> 35 passed in 1.79s

# 2. Golden Symbol Audit CLI Execution
& "$HOME\.venv\Scripts\python.exe" python/portfolio/audit_golden_symbols.py
==> ACB, DGC, FPT, VIX audit completed passing all data lineage invariants.

# 3. Frontend Production Build
npm --prefix frontend run build
==> dist/assets/index-Dy9GJ733.js built in 1.57s (exit code 0)
```

---

## Decisions

- Chuẩn hóa toàn bộ các metric 12 chiều thành object có cấu trúc `{value, status, reason, formatted_vi}` để API & Frontend tiêu thụ an toàn.
- Thay thế hoàn toàn hàm `formatPct` và `formatVND` thô ở React component bằng centralized helper `formatMetricValue(value, type)` từ `vietnameseSemantics.js`.

---

## Result

Hoàn tất audit và sửa tận gốc các nguyên nhân gây ra nhãn `N/A`, `nullx`, `0.0%` giả tạo. Đã bổ sung diagnostics presentation layer trong `vietnamese_presenter.py` và `vietnameseSemantics.js`, bảo vệ 100% tính nguyên vẹn dữ liệu cho ngân hàng (ACB), chứng khoán (VIX) và doanh nghiệp sản xuất (DGC, FPT). Các bài test regression 35/35 đều pass tuyệt đối và build frontend thành công.

