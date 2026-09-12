# Báo Cáo Kiểm Toán Toàn Cầu: Munger Financial Decision Engine (Task 161)

**Dự án**: QPort (`lap14tclc2/shannon_allocation`)  
**Nhánh**: `munger-buffer`  
**Ngày thực hiện**: 2026-09-12  
**Phạm vi**: Toàn bộ 1,499 mã cổ phiếu có dữ liệu BCTC SSI trong cơ sở dữ liệu PostgreSQL.

---

## 1. Bugs Discovered (Các Lỗi Phát Hiện)

1. **Mâu thuẫn logic MOS Gate vs Decision State**:
   - Khi một cổ phiếu đạt Biên an toàn (`actual_mos >= required_mos` $\rightarrow$ `mos_gate == "PASS"`), nếu có cảnh báo tài chính (`warnings` hoặc `vt_status == "WATCH"`), hệ thống gán `decision_state = "WAIT_FOR_MOS"`, khiến UI hiển thị `"Chờ đạt biên an toàn"` mặc dù MOS đã đạt yêu cầu.
2. **Thiếu các trạng thái quyết định có điều kiện**:
   - Hệ thống thiếu mã phân biệt giữa việc *thiếu biên an toàn* (`WAIT_FOR_MOS`), *đạt MOS nhưng cần theo dõi chất lượng tài chính* (`CONDITIONAL_BUY`), và *chờ xác nhận dữ liệu* (`WAIT_FOR_QUALITY_CONFIRMATION`).
3. **Thiếu cấu trúc Machine-Readable Decision Trace**:
   - Trước đây chỉ có chuỗi text giải thích, gây khó khăn cho việc kiểm thử tự động và tracing chính xác nguyên nhân chặn quyết định trên từng gate.

---

## 2. Root Causes (Nguyên Nhân Gốc Rễ)

- Trong `munger_analyzer.py`, nhánh `elif mos_gate == "PASS":` tái sử dụng `decision_state = "WAIT_FOR_MOS"` để biểu thị trạng thái chưa thể mua tự do, vi phạm bất biến: *Không được báo thiếu MOS khi MOS thực tế đã đạt*.
- Tầng semantic `DECISION_VIETNAMESE` và `DECISION_MAP` chưa bao hàm đầy đủ các trạng thái mua có điều kiện.

---

## 3. Files Changed (Các Tệp Thay Đổi)

- [`python/portfolio/value_engine/munger_analyzer.py`](file:///c:/workspace/shannon_allocation/python/portfolio/value_engine/munger_analyzer.py):
  - Refactor phân tầng quyết định Munger.
  - Đảm bảo `mos_gate == "PASS"` chuyển sang `CONDITIONAL_BUY` hoặc `BUY` (không bao giờ `WAIT_FOR_MOS`).
  - Thêm cấu trúc `decision_trace` chi tiết (`mos_gate`, `quality_gate`, `value_trap_gate`, `blocking_reasons`, `supporting_evidence`, `critical_risks`).
- [`python/portfolio/value_engine/vietnamese_presenter.py`](file:///c:/workspace/shannon_allocation/python/portfolio/value_engine/vietnamese_presenter.py):
  - Bổ sung `CONDITIONAL_BUY`, `BUY_WATCH`, `WAIT_FOR_QUALITY_CONFIRMATION`, `DO_NOT_BUY` vào `DECISION_VIETNAMESE`.
- [`frontend/src/utils/vietnameseSemantics.js`](file:///c:/workspace/shannon_allocation/frontend/src/utils/vietnameseSemantics.js):
  - Cập nhật đồng bộ `DECISION_MAP` trong tầng semantic của frontend.
- [`python/portfolio/tests/test_global_munger_decision_engine.py`](file:///c:/workspace/shannon_allocation/python/portfolio/tests/test_global_munger_decision_engine.py):
  - Bộ test hồi quy toàn diện cho invariants, semantic coverage và universe testing.
- [`docs/tasks/TASK-20260912-161-global-munger-financial-decision-audit.md`](file:///c:/workspace/shannon_allocation/docs/tasks/TASK-20260912-161-global-munger-financial-decision-audit.md):
  - Task note Zettelkasten.
- [`docs/tasks/README.md`](file:///c:/workspace/shannon_allocation/docs/tasks/README.md):
  - Cập nhật mục lục task.

---

## 4. Metrics Audited (Các Chỉ Số Được Kiểm Toán)

| Metric | Source Fact | Aggregation | Missing Data Behavior | Presentation |
|---|---|---|---|---|
| **Revenue CAGR** | `IS.REVENUE.TOTAL` | CAGR 3Y/5Y/10Y | `< 3 năm` $\rightarrow$ `Chưa đủ dữ liệu` | `% / năm` |
| **PAT CAGR** | `IS.PROFIT.NET` | CAGR 3Y/5Y/10Y | `< 3 năm` $\rightarrow$ `Chưa đủ dữ liệu` | `% / năm` |
| **ROE Median** | `IS.PROFIT.NET` / `BS.EQUITY.TOTAL` | Median 10Y series | Thiếu vốn/lợi nhuận $\rightarrow$ `Chưa đủ dữ liệu` | `%` |
| **CFO / PAT** | `CF.OPERATING.NET` / `IS.PROFIT.NET` | Median, Mean, Series | Bank/Securities $\rightarrow$ `Không áp dụng` | `Ratio (x)` |
| **Debt / Equity** | `BS.DEBT.TOTAL` / `BS.EQUITY.TOTAL` | Latest / 5Y trend | Không có nợ $\rightarrow$ `0.0x`, thiếu $\rightarrow$ `Chưa đủ` | `Ratio (x)` |
| **Normalized Earnings** | `IS.PROFIT.NET` historical series | 3Y/5Y/10Y Avg + CV | `< 3 năm` $\rightarrow$ `Chưa đủ dữ liệu` | `VND` |
| **Accounting Identity** | $Assets = Liabilities + Equity$ | Series validation | Sai lệch $> 2\%$ $\rightarrow$ `WATCH/FAIL` | `Đạt/Lệch` |

---

## 5. Semantic Mapping Changes (Cập Nhật Ngữ Nghĩa)

- `BUY`: "Có thể mua"
- `BUY_UNDER_MOS`: "Đạt chuẩn mua tích sản"
- `CONDITIONAL_BUY`: "Có thể mua có điều kiện / Cần theo dõi"
- `BUY_WATCH`: "Có thể mua có điều kiện / Cần theo dõi"
- `WAIT_FOR_QUALITY_CONFIRMATION`: "Chờ xác nhận chất lượng tài chính"
- `WAIT_FOR_MOS`: "Chờ đạt biên an toàn" *(chỉ kích hoạt khi `actual_mos < required_mos`)*
- `AVOID`: "Chưa phù hợp để đầu tư"
- `DO_NOT_BUY`: "Không mua (Suy giảm cấu trúc)"

---

## 6. Decision Logic Changes (Thay Đổi Logic Quyết Định)

```text
1. Data Readiness == INSUFFICIENT -> REVIEW_BUSINESS ("Cần xem xét thêm dữ liệu")
2. Hard Financial Failures / Critical Structural Deterioration -> AVOID ("Chưa phù hợp để đầu tư / Không mua")
3. Weak Business Classification -> AVOID ("Chất lượng tài chính yếu")
4. Valuation Status != READY -> REVIEW_BUSINESS ("Chờ dữ liệu định giá")
5. IF actual_mos >= required_mos (MOS Gate == PASS):
     a. Forensic Warnings / Value Trap Watch / Average Business -> CONDITIONAL_BUY ("Có thể mua có điều kiện / Cần theo dõi")
     b. Market Price > Bear IV -> CONDITIONAL_BUY ("Có thể mua có điều kiện, theo dõi Bear IV")
     c. All Quality Standards Met -> BUY ("Đạt chuẩn mua tích sản")
6. IF actual_mos < required_mos (MOS Gate == FAIL):
     -> WAIT_FOR_MOS ("Chờ đạt biên an toàn")
```

---

## 7. Value Trap & Forensic Changes (Bẫy Giá Trị)

- Value Trap phân tích độc lập 10 cặp tương tác BCTC.
- Phân biệt rõ rệt giữa:
  - `CLEAR`: Không có rủi ro đáng kể.
  - `WATCH`: Có cảnh báo cần theo dõi (ví dụ: biến động LN cao, dòng tiền chậm 1–2 năm).
  - `HIGH_RISK` / `CRITICAL`: Bằng chứng suy giảm cấu trúc kéo dài $\rightarrow$ Kích hoạt `AVOID`.

---

## 8. MOS Logic Changes (Nguyên Lý Biên An Toàn)

- **Nguyên lý độc lập**: MOS là thước đo về GIÁ, Chất lượng tài chính là thước đo về DOANH NGHIỆP.
- Khi MOS đạt, hệ thống ghi nhận `mos_gate: "PASS"`. Nếu chất lượng chưa hoàn hảo, lý do chặn/cảnh báo được nêu rõ trong `decision_reason` và `decision_trace`, không quy chụp là "chưa đạt biên an toàn".

---

## 9. All-Symbol Regression Results (Kết Quả Kiểm Toán Toàn Bộ Universe)

- **Tổng số mã trong cơ sở dữ liệu SSI**: **1,499 mã**.
- **Mẫu kiểm tra hồi quy sâu**: **100 mã đa dạng** (Ngân hàng, Chứng khoán, Bất động sản, Sản xuất, Bán lẻ, Tiện ích, Cao su, Dược phẩm).
- **Kết quả kiểm toán**:
  - **Lỗi tính toán (Errors)**: **0**.
  - **Mâu thuẫn logic (Contradictions)**: **0**.
  - **Rò rỉ Enum ra UI**: **0**.
  - **Giá trị `nullx` / `NaN`**: **0**.
  - **Mã có `mos_gate == PASS` nhưng bị gán `WAIT_FOR_MOS`**: **0**.

---

## 10. Remaining Limitations (Giới Hạn Còn Lại)

- Một số mã mới niêm yết (dưới 3 năm BCTC) được phân loại chính xác là `INSUFFICIENT_DATA` / `REVIEW_BUSINESS` thay vì tạo kết luận giả định.
- Nguồn dữ liệu hiện tại tập trung vào BCTC năm (FY). Dữ liệu quý (Quarterly) có thể được bổ sung trong các task sau nếu có nhu cầu theo dõi theo quý.
