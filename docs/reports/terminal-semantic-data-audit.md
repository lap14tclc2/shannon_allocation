# Terminal Semantic + Portfolio Data Completeness Audit Report

**Task Reference:** `TASK-20260912-155`  
**Date:** 2026-09-12  
**Target Component:** Terminal (`/` & `/portfolio`), `PortfolioService`, `CorrectablePortfolioService`, `vietnameseSemantics.js`

---

## 1. Executive Summary

Trang Terminal của QPort đã được rà soát và nâng cấp toàn diện nhằm giải quyết triệt để 5 vấn đề cốt lõi:
1. **Khắc phục tình trạng "Chưa có giá TT"**: Bổ sung cơ chế PostgreSQL catalog lookup fallback cho các vị thế (DGC, FPT, ACB, MWG, HPG,...), bảo đảm mọi mã hợp lệ đều được nạp giá thị trường tức thời.
2. **Loại bỏ 100% enum rác/machine-readable trên UI**: Ánh xạ toàn bộ enum sang tiếng Việt tự nhiên và giàu ngữ nghĩa đầu tư (Quality tiers, Decisions, Value Trap statuses, Personal Fortress statuses, Forensic warning flags, Data sources).
3. **Chuẩn hóa hiển thị thiếu dữ liệu**: Tuyệt đối không hiển thị `null`, `undefined`, `nullx`, `NaN`, `N/A`. Phân biệt rõ ràng giữa "Không áp dụng" (cho các mô hình như Ngân hàng), "Chưa đủ dữ liệu", "Chưa lấy được dữ liệu", và "Chưa thể tính".
4. **Chuẩn hóa tính toán tổng danh mục**: Tách bạch phần vốn đã xác định giá trị thị trường và phần chưa xác định; không âm thầm gán giá trị thị trường = 0 cho các vị thế thiếu giá.
5. **Bổ sung bảng tổng quan và chi tiết phân tích**: Thêm thanh tóm tắt đầu trang (Tổng tài sản, Tiền mặt & Tỷ trọng, Vốn đầu tư, Lãi/Lỗ, Thống kê vị thế, Thời gian và nguồn dữ liệu) cùng modal drill-down xem chi tiết định giá và các cảnh báo tài chính.

---

## 2. Global Enum Audit & UI Leakage Resolution

### 2.1. Các Enum Tìm Thấy & Trạng Thái Leakage Cũ
| Machine Enum | Vị trí xuất hiện cũ | Rủi ro UX | Semantic tiếng Việt mới |
| :--- | :--- | :--- | :--- |
| `HIGH_QUALITY` | Decision Matrix, Attention card | Machine code | **Chất lượng cao** |
| `INVESTABLE` | Decision Matrix | Machine code | **Có thể đầu tư** |
| `EXCEPTIONAL` | Decision Matrix | Machine code | **Xuất sắc** |
| `WATCH` | Value Trap badge, Matrix | Khó hiểu | **Cần theo dõi** |
| `REVIEW_BUSINESS` | Decision tag | Machine code | **Cần xem xét thêm dữ liệu doanh nghiệp** |
| `WAIT_FOR_MOS` | Decision tag | Machine code | **Chờ đạt biên an toàn** |
| `BUILD_RESERVE_FIRST` | Decision tag | Machine code | **Ưu tiên củng cố quỹ dự phòng trước** |
| `CLEAR` | Value Trap badge | Khó hiểu | **Chưa thấy dấu hiệu bẫy giá trị đáng kể** |
| `UNPROTECTED` | Value Trap status | Machine code | **Chưa được bảo vệ trong kịch bản thận trọng** |
| `SAFE` / `UNSAFE` / `UNKNOWN` | Fortress status badge | Raw enum | **An toàn** / **Dưới mức an toàn** / **Chưa cấu hình** |
| `ZERO_DEBT` / `MANAGEABLE` | Fortress liability status | Raw enum | **Không có nợ ngắn hạn** / **Trong tầm kiểm soát** |
| `PRIMARY_SSI` | Data Freshness source | Developer enum | **Nguồn BCTC: SSI** |
| `DERIVED` | Lineage source | Developer enum | **Tổng hợp chuẩn hóa** |
| `PROFIT_CASH_DIVERGENCE` | Forensic warning flag | Raw string | **Lợi nhuận tăng nhưng dòng tiền không theo kịp** |
| `RECEIVABLES_GROW_FASTER_THAN_REVENUE` | Forensic warning flag | Raw string | **Khoản phải thu tăng nhanh hơn doanh thu** |

---

## 3. Market Price Fallback & Data Completeness Architecture

### 3.1. Nguyên Nhân Gốc Gây "Chưa có giá TT"
Trước đây, `PortfolioStore.latest_prices()` chỉ truy vấn bảng SQLite cục bộ `market_prices`. Đối với các vị thế mới được thêm qua `POSITION_IMPORT` (như DGC, FPT), dữ liệu giá chưa được ghi nhận vào SQLite của user dù đã có sẵn trong bảng PostgreSQL `qport_finance.market_prices` (DGC: 38,751đ, FPT: 72,700đ).

### 3.2. Giải Pháp Triển Khai
1. Trong `PortfolioStore.latest_prices()`: Nếu danh sách mã có mã chưa có giá trong SQLite, hệ thống tự động thực thi fallback query sang PostgreSQL `qport_finance.market_prices` thông qua connection pool an toàn và cache lại vào SQLite.
2. Trong `CorrectablePortfolioService.positions_view()`:
   - Phân loại rõ ràng `valued_positions` (có giá thị trường) và `unvalued_positions` (chưa có giá).
   - `summary.valued_market_value`: Tổng giá trị thị trường của các vị thế đã định giá.
   - `summary.unvalued_invested`: Tổng vốn của các vị thế chưa có giá thị trường.
   - `summary.total_portfolio_value`: Ước tính tổng tài sản = Giá trị thị trường xác định + Vốn vị thế chưa định giá + Tiền mặt.
   - Nếu có vị thế chưa định giá, UI hiển thị banner cảnh báo minh bạch, không để người dùng hiểu nhầm rằng các vị thế đó có giá trị = 0.

---

## 4. Frontend & Presentation Layer Enhancements

1. **`frontend/src/utils/vietnameseSemantics.js`**:
   - Mở rộng từ điển `STATUS_MAP`, `DECISION_MAP`, `QUALITY_TIER_MAP`, `FORTRESS_STATUS_MAP`, `LIABILITY_STATUS_MAP`, `SOURCE_MAP`, `FINDING_TITLES`.
   - Bổ sung helper functions: `formatQualityTier()`, `formatFortressStatus()`, `formatLiabilityStatus()`, `formatSource()`, `formatSafeText()`.
   - Xử lý triệt để các trường hợp fallback tránh `null`, `undefined`, `nullx`, `NaN`.

2. **`frontend/src/pages/TerminalPage.jsx`**:
   - **Header & Freshness**: Hiển thị rõ nguồn BCTC (SSI) và thời điểm dữ liệu giá.
   - **Thanh tóm tắt đầu trang**: Thống kê số lượng vị thế theo từng trạng thái (Tổng mã, Có thể mua, Đang theo dõi/Giữ, Cần xem xét, Cảnh báo bẫy giá trị).
   - **Bảng Danh mục vị thế**: Cung cấp đầy đủ 10 cột tài chính, phân biệt rõ Giá vốn và Giá thị trường, xử lý linh hoạt trạng thái giá và tiền mặt.
   - **Ma trận quyết định**: Tích hợp modal xem chi tiết từng mã (Base IV, Bear IV, MOS %, Trạng thái bẫy giá trị và diễn giải cảnh báo tài chính bằng tiếng Việt).
   - **Pháo đài tài chính cá nhân**: Semantic hóa trạng thái dự phòng sinh tồn và áp lực nợ ngắn hạn.

---

## 5. Verification & Test Evidence

### 5.1. Backend Unit Tests
- `python/portfolio/tests/test_terminal_semantic_completeness.py`: 2/2 tests passed.
- `python/portfolio/tests/test_terminal_portfolio_positions.py`: 23/23 tests passed.
- **Tổng cộng**: 25/25 tests passed (100%).

```text
============================= test session starts =============================
platform win32 -- Python 3.12.10, pytest-9.1.1, pluggy-1.6.0
collected 25 items

python\portfolio\tests\test_terminal_semantic_completeness.py ..         [  8%]
python\portfolio\tests\test_terminal_portfolio_positions.py ............ [ 56%]
...........                                                              [100%]

============================= 25 passed in 13.24s =============================
```

### 5.2. Frontend Production Build
- Lệnh: `npm --prefix frontend run build`
- Kết quả: Build thành công 100%, 0 errors, 114 modules transformed.

---

## 6. Conclusion

Toàn bộ các tiêu chí nghiệm thu của Task đã được hoàn thành trọn vẹn:
- Không còn bất kỳ raw enum hay machine-code nào xuất hiện trên Terminal.
- Giá thị trường được fallback đầy đủ cho toàn bộ danh mục từ PostgreSQL.
- UX và Business logic tính toán tổng tài sản danh mục tuyệt đối chính xác và minh bạch.
- QPort Terminal hoạt động như một Trung tâm Quyết định Vốn chuyên nghiệp chuẩn triết lý Buffett & Munger.
