# Báo Cáo Kiểm Toán: Deep Munger Financial Analysis & Terminal Upgrade (Task 160)

**Dự án**: QPort (`lap14tclc2/shannon_allocation`)  
**Nhánh**: `munger-buffer`  
**Ngày thực hiện**: 2026-09-12  
**Mục tiêu**: Nâng cấp toàn diện QPort Buffett Terminal thành một Financial Decision Terminal chuyên sâu theo phương pháp Charlie Munger.

---

## 1. Tổng Quan Kiến Trúc & Luồng Dữ Liệu

Toàn bộ quá trình đánh giá tài chính vận hành theo nguyên lý:
> *"Đo lường những gì BCTC chứng minh được. Không thêu dệt những gì BCTC không chứng minh được. Sử dụng tư duy nghịch đảo để tìm kiếm bằng chứng bác bỏ. Chỉ dùng định giá sau khi đã hiểu rõ kinh tế học doanh nghiệp và chất lượng tài chính."*

```text
SSI Canonical Facts (PostgreSQL)
  → Multi-Year History Builder (10-15 năm FY)
  → Financial Forensics & Accounting Consistency (10 cặp tương tác BCTC)
  → Archetype Analyzers (Bank, Securities, Normal Enterprise)
  → Normalized Earning Power (3Y/5Y/10Y Median & Earnings Volatility)
  → Structural vs Cyclical Deterioration
  → Value Trap Detector (Bằng chứng ủng hộ vs Bằng chứng chống lại)
  → Munger 8 Pre-Commitment Inversion Questions (Stress test định lượng)
  → Canonical Valuation Integration (Bear / Base / Bull & MOS)
  → Anti False-BUY Action Engine (Phân tách Rõ ràng Chất Lượng vs Thị Giá)
  → Vietnamese Presentation Layer (100% Thuần Việt Ngữ Nghĩa)
  → QPort Terminal UX (Thứ tự ra quyết định chuẩn mực)
```

---

## 2. Kết Quả Kiểm Toán 4 Cổ Phiếu Trọng Yếu (Golden Symbols Audit)

### 2.1. ACB — Ngân hàng Thương mại Cổ phần Á Châu
- **Archetype**: `BANK` (Ngân hàng thương mại)
- **Độ sâu lịch sử**: 15 năm (2011 – 2025), `DEEP_HISTORY`.
- **Sẵn sàng dữ liệu**: `READY` (Dữ liệu BCTC chuẩn hóa SSI đầy đủ).
- **Phân loại Compounder**: *Doanh nghiệp có tiềm năng tăng trưởng tích lũy* (`POTENTIAL_COMPOUNDER`).
- **Chất lượng tài chính**:
  - ROE trung vị 15 năm: **20.4%** (Rất ổn định).
  - Tăng trưởng LNST CAGR: **15.2%/năm**.
  - Tỷ lệ Nợ xấu / Cho vay: Được kiểm soát an toàn theo quy định ngành ngân hàng.
  - Hằng đẳng thức kế toán: Khớp trong 15/15 năm.
- **Bẫy giá trị**: `CLEAR` (Chưa phát hiện dấu hiệu bẫy giá trị đáng kể).
- **Lợi nhuận chuẩn hóa**:
  - LNST gần nhất: **16,846 tỷ VND**.
  - LNST chuẩn hóa 5 năm: **13,290 tỷ VND**.
  - Độ biến động lợi nhuận (CV): **47.3%**.
- **Định giá & Biên an toàn**:
  - Thị giá hiện tại: **21,900 VND**.
  - Base Intrinsic Value: **26,300 VND**.
  - MOS thực tế: **16.7%** (Chưa đạt mức MOS yêu cầu **25.0%**).
- **Phản biện luận điểm đầu tư (Munger 8 Questions)**:
  - *Q1 (Rủi ro luận điểm)*: `RESILIENT` — Không phát hiện rủi ro BCTC nghiêm trọng.
  - *Q2 (Suy yếu lợi thế)*: `RESILIENT` — ROE trung vị 20.4% khẳng định hiệu quả sử dụng vốn.
  - *Q3 (Stress test LN giảm 30%)*: `VULNERABLE` — MOS giảm xuống -19.0% nếu LN giảm 30%.
  - *Q4 (IV ước tính cao 30%)*: `VULNERABLE` — Giá hiện tại cao hơn IV điều chỉnh (18,410 đ).
  - *Q6 (Khóa giao dịch 5 năm)*: `RESILIENT` — Bảng cân đối vững chắc hỗ trợ nắm giữ dài hạn.
  - *Q8 (Tiêu chí bác bỏ thesis)*: Đã thiết lập 5 tiêu chí định lượng (ROE < 14%, Nợ xấu tăng đột biến, v.v.).
- **Quyết định hành động**: **Chờ biên an toàn** (`WAIT_FOR_MOS`).
  - *Lý do*: Doanh nghiệp đạt chuẩn chất lượng BCTC nhưng thị giá hiện tại chưa chiết khấu đủ mức Biên an toàn yêu cầu (MOS 16.7% < 25.0%).

---

### 2.2. DGC — Công ty Cổ phần Tập đoàn Hóa chất Đức Giang
- **Archetype**: `NORMAL_ENTERPRISE` (Doanh nghiệp sản xuất / Hóa chất)
- **Độ sâu lịch sử**: 15 năm (2011 – 2025), `DEEP_HISTORY`.
- **Sẵn sàng dữ liệu**: `READY`.
- **Phân loại Compounder**: *Doanh nghiệp tích lũy giá trị dài hạn* (`COMPOUNDER`).
- **Chất lượng tài chính**:
  - ROE trung vị 15 năm: **23.4%** (Vượt trội).
  - CFO / PAT trung vị: **0.95x** (Khả năng chuyển hóa tiền mặt xuất sắc).
  - Hàng tồn kho & Khoản phải thu: Tăng trưởng đồng pha với doanh thu, không phát hiện ứ đọng vốn lưu động.
- **Bẫy giá trị**: `CLEAR` (Không có dấu hiệu suy giảm cấu trúc).
- **Lợi nhuận chuẩn hóa**:
  - LNST gần nhất: **3,250 tỷ VND**.
  - LNST chuẩn hóa 5 năm: **3,410 tỷ VND** (Doanh nghiệp đang ở vùng bình thường sau giai đoạn sốt giá phốt pho vàng).
- **Định giá & Biên an toàn**:
  - Thị giá hiện tại: **48,000 VND**.
  - Base Intrinsic Value: **70,000 VND** (MOS Base = **31.4%**).
  - Bear Intrinsic Value: **45,953 VND**.
- **Kịch bản Thận trọng (Bear Case Gate)**:
  - Thị giá hiện tại (48,000 đ) cao hơn Bear IV (45,953 đ). Munger Engine kích hoạt nguyên tắc bảo toàn vốn tuyệt đối.
- **Quyết định hành động**: **Chờ biên an toàn** (`WAIT_FOR_MOS`).
  - *Lý do*: Đạt biên an toàn cơ sở nhưng thị giá chưa nằm dưới kịch bản thận trọng Bear IV.

---

### 2.3. FPT — Công ty Cổ phần FPT
- **Archetype**: `NORMAL_ENTERPRISE` (Công nghệ thông tin & Viễn thông)
- **Độ sâu lịch sử**: 15 năm (2011 – 2025), `DEEP_HISTORY`.
- **Sẵn sàng dữ liệu**: `READY`.
- **Phân loại Compounder**: *Doanh nghiệp tích lũy giá trị dài hạn* (`COMPOUNDER`).
- **Chất lượng tài chính**:
  - ROE trung vị: **20.9%**.
  - Tăng trưởng LNST CAGR 10 năm: **18.5%/năm**.
  - Dòng tiền kinh doanh (CFO): Dương liên tục qua tất cả các năm.
- **Bẫy giá trị**: `WATCH` (Cảnh báo biến động nhẹ do tăng trưởng mạnh tài sản và khoản phải thu theo quy mô dự án phần mềm toàn cầu).
- **Lợi nhuận chuẩn hóa**:
  - LNST gần nhất: **9,376 tỷ VND**.
  - LNST chuẩn hóa 5 năm: **6,669 tỷ VND**.
  - Độ biến động (CV): **64.1%** (Tăng trưởng dốc).
- **Định giá & Biên an toàn**:
  - Thị giá hiện tại: **72,700 VND**.
  - Base Intrinsic Value: **95,283 VND** (MOS Base = **23.7%** vs Yêu cầu **20.0%**).
- **Quyết định hành động**: **Chờ biên an toàn** (`WAIT_FOR_MOS`).
  - *Lý do*: Mức giá đạt MOS cơ sở nhưng hệ thống phát hiện rủi ro định giá dựa trên mức đỉnh lợi nhuận gần nhất, khuyến nghị kiên nhẫn tích lũy ở vùng giá có biên đệm an toàn cao hơn.

---

### 2.4. VIX — Công ty Cổ phần Chứng khoán VIX
- **Archetype**: `SECURITIES` (Công ty chứng khoán)
- **Độ sâu lịch sử**: 15 năm (2011 – 2025), `DEEP_HISTORY`.
- **Sẵn sàng dữ liệu**: `READY`.
- **Phân loại Compounder**: *Chất lượng doanh nghiệp còn yếu* (`WEAK_BUSINESS`).
- **Chất lượng tài chính**:
  - Độ biến động lợi nhuận (CV): **218.9%** (Cực kỳ thất thường theo chu kỳ thị trường chứng khoán).
  - LNST gần nhất (5,410 tỷ) cao gấp **3.3 lần** mức bình thường hóa 5 năm (1,617 tỷ). Chạm đỉnh chu kỳ định giá FVTPL.
- **Bẫy giá trị**: `CLEAR` về mặt gian lận, nhưng rủi ro chu kỳ cực cao.
- **Định giá & Biên an toàn**:
  - MOS lý thuyết theo P/E hiện tại: **54.9%** (Rất cao nếu nhìn máy móc).
- **Anti False-BUY Gate**:
  - Engine Munger phát hiện: Mặc dù MOS > 50%, nhưng chất lượng tài chính thuộc nhóm yếu (`WEAK_BUSINESS`) với biến động lợi nhuận > 200%.
- **Quyết định hành động**: **Chưa phù hợp để đầu tư** (`AVOID`).
  - *Lý do*: Không đạt tiêu chuẩn chất lượng kinh doanh bền vững để tích sản dài hạn theo triết lý Munger.

---

## 3. Bảng Tổng Hợp Kiểm Toán UI / Semantic / Data Integrity

| Hạng mục kiểm tra | Tiêu chuẩn Munger | Trạng thái thực tế | Bằng chứng kiểm tra |
|---|---|---|---|
| **Raw Enum Leakage** | 0 machine enums trên UI | **PASS (0 phát hiện)** | Quét ripgrep toàn bộ `frontend/src`: 100% enums qua mapping `vietnameseSemantics.js` |
| **Null / Nullx / NaN** | 0 giá trị thô không xử lý | **PASS (0 phát hiện)** | Formatters chuẩn hóa fallback `Chưa đủ dữ liệu`, `Không áp dụng`, `Chưa có giá` |
| **N/A bừa bãi** | Có dữ liệu là phải tính | **PASS** | Phân biệt rõ thiếu dữ liệu vs không áp dụng theo archetype |
| **Portfolio Assets Formula** | Stock Market Value + Cash | **PASS** | `summary.valued_market_value + cashReserve`, tỷ trọng tính trên Total Assets |
| **Position Actions** | Thêm, Sửa, Xóa, Sửa Cash | **PASS** | Modal CRUD hoạt động chính xác, lưu trữ state bền vững |
| **Valuation Navigation** | Nút Xem định giá trên từng dòng | **PASS** | Trỏ tới `/valuation?symbol={SYM}` và tự động focus thẻ định giá |
| **Notable Candidates** | Gợi ý ứng viên động | **PASS** | Section `TerminalCandidatesSection` nạp từ `getMungerCandidates()` không hard-code |
| **Munger 8 Inversion** | Tự động trả lời định lượng | **PASS** | 8 câu hỏi với Stress scenario, IV overstatement, Durability, Invalidation triggers |
| **Vite Frontend Build** | Build production thành công | **PASS** | `npm --prefix frontend run build` hoàn thành trong 1.69s (0 lỗi) |
| **Backend Test Suite** | 100% tests PASS | **PASS** | 10/10 tests PASS trong 111s |

---

## 4. Kết Luận & Cam Kết

Hệ thống QPort Terminal trên nhánh `munger-buffer` đã hoàn thành toàn bộ các yêu cầu của Task 160. Toàn bộ trải nghiệm đầu tư được chuyển đổi thành một cỗ máy hỗ trợ quyết định kỷ luật, trung thực với dữ liệu BCTC và kiên định theo triết lý đầu tư giá trị của Warren Buffett và Charlie Munger.
