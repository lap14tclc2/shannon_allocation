# Audit Report: Business Munger Candidates & Portfolio Valuation Navigation

**Task Reference**: [TASK-20260912-158-business-munger-candidates-valuation-navigation.md](../tasks/TASK-20260912-158-business-munger-candidates-valuation-navigation.md)  
**Date**: 2026-09-12  
**Status**: VERIFIED & COMPLETED  

---

## 1. Candidate Selection Logic Hiện Tại

QPort thực hiện tuyển chọn các ứng viên cổ phiếu tiềm năng dựa trên triết lý cốt lõi của Warren Buffett và Charlie Munger:
$$\text{Quality} \longrightarrow \text{Durability} \longrightarrow \text{Financial Strength} \longrightarrow \text{Accounting Integrity} \longrightarrow \text{Capital Allocation} \longrightarrow \text{Value Trap Risk} \longrightarrow \text{Valuation / MOS}$$

Candidate discovery engine (`python/portfolio/value_engine/munger_candidates.py`) hoạt động tự động từ kho dữ liệu BCTC chuẩn hóa SSI trong PostgreSQL (`qport_finance.canonical_facts`):
1. Quét toàn bộ các mã chứng khoán có lịch sử BCTC hợp lệ ($\ge 8$ facts FY, $\ge 2$ năm lịch sử).
2. Xây dựng hồ sơ định giá và ma trận chất lượng Munger đầy đủ (`build_canonical_valuation(symbol, compute_munger=True)`).
3. Áp dụng các cổng lọc loại trừ cứng (Hard Filtering Gates) và xếp hạng ứng viên dựa trên điểm chất lượng tổng hợp.

Tuyệt đối **không hard-code bất kỳ mã cổ phiếu nào** và **không dùng Margin of Safety (MOS) làm tiêu chí đơn lẻ để đẩy một doanh nghiệp yếu kém lên danh sách đề xuất**.

---

## 2. Các Tiêu Chí Được Sử Dụng

| Nhóm Tiêu Chí | Chỉ Số Đánh Giá | Điều Kiện Đạt Chuẩn Munger |
| :--- | :--- | :--- |
| **Hiệu quả sinh lời (Profitability)** | ROE trung vị nhiều năm | $\text{ROE} \ge 14.0\%$ (Xuất sắc nếu $\ge 20.0\%$) |
| **Tăng trưởng bền vững (Growth)** | CAGR LNST (Net Profit CAGR) | Tăng trưởng dương, bền vững $> 5\%$ qua chu kỳ |
| **Chất lượng dòng tiền (Earnings Quality)** | CFO / PAT | $\ge 0.85\times$ (dòng tiền kinh doanh thặng dư, chuyển hóa LN thành tiền) |
| **Sức khỏe bảng cân đối (Financial Health)** | Debt / Equity | D/E an toàn, không có áp lực nợ vay đột biến |
| **Pha loãng & Phân bổ vốn (Capital Allocation)** | Dilution & Reinvestment | Không phát hành pha loãng phá hủy giá trị (`FAIL`/`DESTRUCTIVE`) |
| **Nhất quán kế toán (Accounting Consistency)** | Forensics & Accruals | Đạt chuẩn kế toán nhất quán (`PASS`) |
| **Lịch sử dữ liệu (Data Depth)** | Số năm tài chính | $\ge 2$ năm FY đã kiểm toán |
| **Biên an toàn (Valuation & MOS)** | Base IV, Bear IV, MOS | So sánh giá thị trường với Giá trị nội tại cơ sở và Required MOS |

---

## 3. Cách Xử Lý Value Trap

Hệ thống tích hợp trực tiếp bộ điều tra chuyên sâu **Deep Value-Trap Forensics (Task 148/157)**:
- **Loại trừ tuyệt đối (Hard Reject)**: Nếu doanh nghiệp có trạng thái `HIGH_RISK` hoặc phân loại suy giảm cấu trúc tài chính `STRUCTURAL_EVIDENCE` (ví dụ: CFO/PAT âm kéo dài kết hợp nợ vay tăng phi mã, khoản phải thu vượt doanh thu, lợi nhuận bình thường hóa sụt giảm nghiêm trọng), mã đó lập tức bị loại khỏi danh sách ứng viên, **bất kể định giá P/E rẻ hay MOS cao đến đâu**.
- **Cảnh báo chu kỳ (`WATCH`)**: Nếu chỉ có biến động mang tính chu kỳ (`CYCLICAL_DETERIORATION`) với các bằng chứng phản biện lành mạnh (như ROE lịch sử cao, tài sản ròng vững chắc), mã vẫn được giữ lại nhưng được gắn nhãn *"Cần theo dõi chu kỳ"* và ghi chú rõ trong phần giải thích lý do đề xuất.

---

## 4. API / Backend Thay Đổi

1. **Module Mới**: `python/portfolio/value_engine/munger_candidates.py`
   - Hàm `compute_all_munger_candidates(force_refresh=False)`: Quét và tính toán toàn bộ danh sách ứng viên từ canonical facts với cơ chế thực thi đa luồng song song (`ThreadPoolExecutor`) và in-memory caching 10 phút.
   - Hàm `get_munger_candidates(tier, search, limit)`: Cung cấp API lọc theo tier (`EXCEPTIONAL`, `HIGH_QUALITY`, `INVESTABLE`), tìm kiếm và phân trang.
   - Hàm `_generate_candidate_rationale_vi()`: Tạo đoạn văn bản giải thích lý do đề xuất hoàn toàn bằng tiếng Việt tự nhiên, chuẩn mực tài chính, bảo toàn định dạng các thuật ngữ viết tắt (ROE, CAGR, CFO/PAT).
2. **Endpoints Mới trong `app/main.py`**:
   - `GET /api/portfolio/business/candidates`: Endpoint chuẩn theo REST namespace của Business page.
   - `GET /api/portfolio/business-candidates`: Endpoint alias tương thích ngược.

---

## 5. Frontend Thay Đổi

1. **`frontend/src/lib/api.js`**:
   - Bổ sung hàm API wrapper `getMungerCandidates(tier, search, limit)` kết nối trực tiếp endpoint aggregation backend.
2. **`frontend/src/pages/BusinessPage.jsx`**:
   - Thêm section mới **"Cổ phiếu tiềm năng theo tiêu chuẩn Munger"** nằm ngay phía trên danh sách toàn bộ doanh nghiệp.
   - Tab lọc theo phân hạng chất lượng: `Tất cả`, `Chất lượng xuất sắc`, `Chất lượng cao`, `Đáng xem xét`.
   - Candidate Card Grid trực quan hiển thị đầy đủ:
     - Badge phân loại chất lượng (`Chất lượng xuất sắc`, `Chất lượng cao`, `Đáng xem xét`).
     - Giá thị trường, Giá trị nội tại (Base IV), Biên an toàn (MOS), Biên an toàn yêu cầu.
     - 6 chỉ số tài chính cốt lõi: ROE, Tăng trưởng LNST, CFO/PAT, Nợ/Vốn CSH, Đánh giá Bẫy giá trị, Khuyến nghị hành động.
     - Đoạn văn bản **Lý do được đề xuất** chi tiết, mạch lạc.
     - Nút **"Xem phân tích chi tiết →"** điều hướng trực tiếp tới `/business/{SYMBOL}`.
3. **`frontend/src/pages/TerminalPage.jsx`**:
   - Bổ sung nút **"Định giá"** (`table-btn table-btn-val`) vào nhóm thao tác của từng vị thế nắm giữ trong bảng danh mục đầu tư.
   - Click nút sẽ điều hướng trực tiếp tới `/valuation?symbol={p.symbol}`.
4. **`frontend/src/pages/ValuationPage.jsx`**:
   - Bổ sung tính năng tự động bắt query parameter `?symbol=XYZ` hoặc hash `#valuation-XYZ`.
   - Tự động kích hoạt tab/card của mã tương ứng và cuộn mượt (smooth scroll) tới vị trí định giá của cổ phiếu được chọn.
5. **CSS Enhancements**:
   - `frontend/src/pages/BusinessPage.css`: Thiết kế typography, badge, pill, grid và rationale block cao cấp theo triết lý Munger.
   - `frontend/src/terminal-page.css`: Bổ sung style nút `table-btn-val` hài hòa với giao diện quant terminal.

---

## 6. Route Valuation Hiện Tại

- Canonical route của trang định giá trong hệ thống QPort: `/valuation`
- Deep-link điều hướng theo từng mã cổ phiếu: `/valuation?symbol={SYMBOL}` hoặc `/valuation#valuation-{SYMBOL}`
- Khi user click nút **"Định giá"** tại Terminal page, router đưa user đến đúng URL canonical kèm ticker, trang `ValuationPage` tự động hiển thị đầy đủ kịch bản Base IV, Bear IV, Bull IV, MOS, Normalized Earnings và các giả định định giá đã tính toán từ backend.

---

## 7. Semantic Mapping Audit (Không Còn Enum / N/A Leak)

| Mã Enum / Raw Code | Hiển thị Giao Diện Tiếng Việt (UI Semantic) |
| :--- | :--- |
| `EXCEPTIONAL` | **Chất lượng xuất sắc** |
| `HIGH_QUALITY` | **Chất lượng cao** |
| `INVESTABLE` | **Đáng xem xét** |
| `REVIEW_BUSINESS` | **Cần xem xét thêm** |
| `WATCH` | **Cần theo dõi** |
| `CLEAR` | **Chưa thấy dấu hiệu bẫy giá trị** |
| `STRUCTURAL_EVIDENCE` | **Suy giảm cấu trúc tài chính** |
| `CYCLICAL_DETERIORATION` | **Suy giảm mang tính chu kỳ** |
| `BUY` / `BUY_MORE` | **Có thể mua tích lũy** |
| `WAIT_FOR_MOS` | **Chờ đạt biên an toàn** |
| `HOLD` | **Tiếp tục nắm giữ / Theo dõi** |
| `BANK` / `SECURITIES` CFO/PAT | **Không áp dụng (Bank/Securities)** |
| Missing / Incomplete data | **Chưa đủ dữ liệu để đánh giá** |

Toàn bộ các chuỗi lỗi thô như `null`, `undefined`, `nullx`, `N/A`, `UNKNOWN`, `INSUFFICIENT_DATA`, `PASS`, `FAIL` đã được loại bỏ hoàn toàn khỏi giao diện người dùng.

---

## 8. Performance & N+1 Audit

- **Không có N+1 Request từ Browser**: Toàn bộ trang `/business` chỉ thực hiện duy nhất 1 request gọi `GET /api/portfolio/business/candidates` để lấy danh sách đã được tổng hợp và tính toán sẵn từ backend.
- **Tối ưu hóa Server-Side Multi-threading**: Backend sử dụng `ThreadPoolExecutor(max_workers=12)` kết hợp query tối ưu `HAVING count(*) >= 8` trên PostgreSQL, rút ngắn thời gian tính toán toàn bộ universe xuống còn vài giây.
- **In-Memory TTL Caching**: Kết quả được lưu bộ nhớ đệm (TTL 10 phút), các lượt tải trang tiếp theo phản hồi tức thì (< 20ms).

---

## 9. Test Results

Tất cả 25 unit & integration tests trong hệ sinh thái kiểm thử đã chạy thành công 100%:

```text
pytest python/portfolio/tests/test_munger_candidates_and_valuation_navigation.py \
       python/portfolio/tests/test_deep_value_trap_forensics.py \
       python/portfolio/tests/test_business_review_and_value_trap.py \
       python/portfolio/tests/test_ui_raw_enum_regression.py \
       python/portfolio/tests/test_golden_baseline_regression.py -v

============================= test session starts =============================
platform win32 -- Python 3.12.10, pytest-9.1.1
collected 25 items

python/portfolio/tests/test_munger_candidates_and_valuation_navigation.py::test_munger_candidates_generation_and_ranking PASSED [  4%]
python/portfolio/tests/test_munger_candidates_and_valuation_navigation.py::test_munger_candidates_filtering_and_rationale PASSED [  8%]
python/portfolio/tests/test_munger_candidates_and_valuation_navigation.py::test_munger_candidates_disqualifies_severe_value_trap PASSED [ 12%]
python/portfolio/tests/test_munger_candidates_and_valuation_navigation.py::test_get_munger_candidates_api_wrapper PASSED [ 16%]
python/portfolio/tests/test_munger_candidates_and_valuation_navigation.py::test_frontend_valuation_and_candidates_contract PASSED [ 20%]
python/portfolio/tests/test_deep_value_trap_forensics.py::test_golden_symbols_deep_value_trap_forensics PASSED [ 24%]
python/portfolio/tests/test_deep_value_trap_forensics.py::test_distressed_value_trap_structural_deterioration PASSED [ 28%]
python/portfolio/tests/test_deep_value_trap_forensics.py::test_cyclical_deterioration_with_counter_evidence PASSED [ 32%]
python/portfolio/tests/test_deep_value_trap_forensics.py::test_bank_and_securities_archetype_isolation PASSED [ 36%]
python/portfolio/tests/test_business_review_and_value_trap.py::test_business_review_high_quality_company_with_evidence PASSED [ 40%]
python/portfolio/tests/test_business_review_and_value_trap.py::test_business_review_single_positive_owner_earnings_not_automatic_pass PASSED [ 44%]
python/portfolio/tests/test_business_review_and_value_trap.py::test_value_trap_missingness_preservation PASSED [ 48%]
python/portfolio/tests/test_business_review_and_value_trap.py::test_value_trap_structural_classification_does_not_overstate PASSED [ 52%]
python/portfolio/tests/test_business_review_and_value_trap.py::test_value_trap_uses_financial_history PASSED [ 56%]
python/portfolio/tests/test_ui_raw_enum_regression.py::test_ui_raw_enum_regression_golden_symbols PASSED [ 60%]
python/portfolio/tests/test_golden_baseline_regression.py::test_baseline_symbols_acb_dgc_fpt_ledger_invariants PASSED [ 64%]
python/portfolio/tests/test_golden_baseline_regression.py::test_golden_scenario_1_buy PASSED [ 68%]
python/portfolio/tests/test_golden_baseline_regression.py::test_golden_scenario_2_buy_more PASSED [ 72%]
python/portfolio/tests/test_golden_baseline_regression.py::test_golden_scenario_3_build_reserve_first PASSED [ 76%]
python/portfolio/tests/test_golden_baseline_regression.py::test_golden_scenario_4_high_volatility_not_sell PASSED [ 80%]
python/portfolio/tests/test_golden_baseline_regression.py::test_golden_scenario_5_value_trap_high_risk_not_buy PASSED [ 84%]
python/portfolio/tests/test_golden_baseline_regression.py::test_golden_scenario_6_accounting_unreliable_sell_review PASSED [ 88%]
python/portfolio/tests/test_golden_baseline_regression.py::test_golden_scenario_7_solvency_failure_avoid PASSED [ 92%]
python/portfolio/tests/test_golden_baseline_regression.py::test_golden_scenario_8_position_capacity_exceeded PASSED [ 96%]
python/portfolio/tests/test_golden_baseline_regression.py::test_golden_scenario_9_no_material_issue_hold PASSED [100%]

============================= 25 passed in 58.66s =============================
```

Frontend production build (`npm --prefix frontend run build`):
```text
✓ 115 modules transformed.
dist/index.html                   1.86 kB │ gzip:   0.82 kB
dist/assets/index-BpQoWY_z.css  269.18 kB │ gzip:  45.91 kB
dist/assets/index-CAC5Q2Za.js   751.83 kB │ gzip: 206.55 kB
✓ built in 1.77s
```

---

## 10. Remaining Gaps & Future Enhancements

- **Real-time Price Refresh Integration**: Khi giá thị trường biến động trong phiên, cache 10 phút của candidates sẽ được cập nhật lại theo chu kỳ để đảm bảo MOS phản ánh sát nhất diễn biến thị trường.
- **Screener Filter Interactivity**: Có thể mở rộng thêm bộ lọc tùy chỉnh theo ngành hoặc theo mức MOS tối thiểu trực tiếp trên giao diện Munger Candidates.
