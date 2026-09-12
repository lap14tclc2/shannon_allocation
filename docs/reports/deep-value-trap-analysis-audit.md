# Audit Báo cáo Điều tra Tài chính Sâu: Deep Value-Trap Analysis (Munger Long-Term Financial Forensics)

**Ngày thực hiện:** 2026-09-12  
**Quy chuẩn áp dụng:** Charlie Munger Forensic Investing Methodology & Zettelkasten Workflow  
**Mã Task:** `TASK-20260912-157-deep-value-trap-munger-financial-forensics`  

---

## 1. Tổng quan & Phương pháp tiếp cận

Hệ thống Value Trap Engine của QPort được nâng cấp toàn diện từ mô hình đánh giá cờ nhị phân (Binary Flags / Enum Warnings) sang **Hệ thống Điều tra Pháp y Tài chính Dài hạn (Munger Long-Term Financial Forensics Investigation)**.

Mô hình mới áp dụng triết lý:
- **Evidence > Label**: Mọi kết luận đều đi kèm dữ liệu định lượng (kỳ phát hiện, số năm liên tiếp, giá trị đầu/cuối kỳ, CAGR, chênh lệch tốc độ tăng trưởng).
- **Trend > Snapshot**: Phân tích chuỗi dữ liệu BCTC lịch sử nhiều năm (FY2018 - FY2025).
- **Cause > Symptom**: Bóc tách nguyên nhân đọng vốn lưu động (Khoản phải thu vs Hàng tồn kho vs Nợ vay).
- **Counter-evidence > Confirmation bias**: Luôn tìm kiếm và ghi nhận các yếu tố phản bác warning (ví dụ: tiền mặt ròng an toàn, tăng trưởng phục hồi sau đáy chu kỳ).
- **Archetype Isolation**: Phân lập mô hình phi tài chính vs Định chế tài chính (Bank / Securities).

---

## 2. Trả lời các câu hỏi Audit cốt lõi

### Q1: Những forensic checks hiện tại là gì? Check nào đúng, sai, thiếu?
- **Đúng**:
  - Đối chiếu tăng trưởng Khoản phải thu vs Doanh thu (Receivables CAGR vs Revenue CAGR).
  - Đối chiếu tăng trưởng Hàng tồn kho vs Doanh thu (Inventory CAGR vs Revenue CAGR).
  - Tỷ lệ CFO / PAT nhiều năm, số năm CFO < PAT, số năm CFO âm.
  - Pha loãng cổ phiếu (Pha loãng thực chất ăn mòn EPS vs Chia cổ tức cổ phiếu phi kinh tế).
  - Đồng nhất thức kế toán và độ tin cậy BCTC.
  - Phân tích đòn bẩy nợ / thanh toán (Debt/Equity, Net Cash, Solvency).
  - Bảo vệ kịch bản Thận trọng (Bear Case IV Margin of Safety).
- **Trước đây sai / thiếu sót**:
  - *Sai sót cũ:* Áp dụng CFO/PAT và Vốn lưu động cho Ngân hàng (ACB) và Chứng khoán (VIX) dẫn đến false warning.
  - *Thiếu sót cũ:* Gán nhãn `STRUCTURAL_EVIDENCE` chỉ từ 1-2 cảnh báo định lượng nhẹ mà không xem xét chu kỳ kinh doanh hoặc bằng chứng phản bác.
  - *Thiếu sót cũ:* Rò rỉ enum tiếng Anh (`MODERATE_EARNINGS_QUALITY_RISK`, `RECEIVABLES_GROW_FASTER_THAN_REVENUE`, `POSSIBLY_STRUCTURAL`, `UNPROTECTED`) lên UI.
  - *Khắc phục:* Đã phân lập triệt để Archetype ngân hàng/chứng khoán, xây dựng ma trận bằng chứng có cấu trúc, phân loại chuẩn `LIKELY_CYCLICAL` vs `STRUCTURAL_EVIDENCE`, và loại bỏ 100% enum trên giao diện.

### Q2: Metric nào đang N/A? Vì sao?
- Các metric vốn lưu động (Phải thu, Tồn kho, CFO/PAT) đối với Ngân hàng (`ACB`) và Công ty chứng khoán (`VIX`):
  - **Trạng thái:** `Không áp dụng` (thay vì `N/A` cụt ngủn hoặc `nullx`).
  - **Nguyên nhân minh bạch:** *"Mô hình tài chính đặc thù (Bank/Securities sử dụng dòng vốn huy động và tín dụng/tự doanh đặc thù)"*.
- Các metric thiếu dữ liệu lịch sử (dưới 2-3 năm):
  - **Trạng thái:** `Chưa đủ dữ liệu`.
  - **Nguyên nhân minh bạch:** Nêu rõ số năm thực tế có trong cơ sở dữ liệu so với ngưỡng tối thiểu yêu cầu.

### Q3: Canonical source nào được sử dụng? Period nào được sử dụng?
- **Nguồn dữ liệu:** PostgreSQL database table `canonical_financial_facts` (chuẩn hóa từ nguồn BCTC kiểm toán SSI).
- **Period:** Chuỗi Annual/FY lịch sử (ưu tiên từ FY2018 đến FY2025, tối thiểu 3 năm gần nhất cho CAGR 3Y).

### Q4: Các warning có bằng chứng đủ mạnh không?
- Mọi warning trong Evidence Matrix đều có:
  - Tên rủi ro tiếng Việt chuẩn mực.
  - Giai đoạn phát hiện (Period).
  - Số năm liên tiếp diễn ra.
  - Giá trị đầu kỳ & cuối kỳ (VND).
  - CAGR của chỉ số & CAGR của doanh thu đối chiếu.
  - Chênh lệch tốc độ tăng (% gap).
  - Xu hướng (Trend) & Mức độ dai dẳng (Persistence).
  - Tác động 3 chiều: Lợi nhuận (Earnings), Dòng tiền (Cash flow), Vốn lưu động (Working capital).
  - Bằng chứng phản bác (Counter-evidence).
  - Kết luận điều tra pháp y (Forensic Conclusion).

### Q5: Phân biệt Structural vs Cyclical có hợp lý không?
- **Rất hợp lý**: Hệ thống không kết luận `STRUCTURAL_EVIDENCE` từ một chỉ số đơn lẻ.
- Để bị xếp loại `STRUCTURAL_EVIDENCE`, doanh nghiệp phải có:
  1. Gian lận hoặc sai lệch BCTC nghiêm trọng (`accounting_status == 'FAIL'`), HOẶC
  2. Rủi ro mất khả năng thanh toán nợ (`balance_sheet_status == 'SOLVENCY_RISK'`), HOẶC
  3. Pha loãng phá hủy giá trị kéo dài (`dilution_status == 'DESTRUCTIVE'`), HOẶC
  4. Có ít nhất 3 tín hiệu suy giảm cấu trúc đồng thời (vừa ROE suy giảm, vừa EPS suy giảm, vừa phình to tài sản/vốn đọng) mà không có tín hiệu phục hồi sau chu kỳ đáy.
- Doanh nghiệp suy giảm nhưng có đệm tiền mặt ròng an toàn hoặc LNST năm gần nhất hồi phục mạnh (> +20% YoY) được phân loại chính xác là `LIKELY_CYCLICAL` (Suy giảm có tính chu kỳ).

### Q6: UI còn enum nào không?
- **Hoàn toàn KHÔNG**. Hệ thống frontend `vietnameseSemantics.js` và `munger_forensics.py` cùng `value_trap.py` đã loại bỏ triệt để các mã enum thô. Toàn bộ hiển thị đạt 100% ngữ nghĩa tiếng Việt chuẩn chuyên ngành tài chính.

### Q7: Có hard-code ticker nào không?
- **Hoàn toàn KHÔNG**. Logic phân tách chỉ dựa trên `archetype` (`BANK`, `SECURITIES`, `NON_FINANCIAL`), `industry`, và các công thức toán học/logic BCTC phổ quát áp dụng cho mọi mã cổ phiếu trên thị trường chứng khoán Việt Nam.

---

## 3. Ma trận nghiệm thu 14 Acceptance Criteria (AC Matrix)

| Tiêu chí (Acceptance Criteria) | Kết quả | Chi tiết thẩm định |
| :--- | :---: | :--- |
| **AC1: Deep evidence, không chỉ status** | **PASS** | Cung cấp Scorecard 14 mục, Evidence Matrix chi tiết từng biến số, Top 3 rủi ro tài chính. |
| **AC2: Warning có đầy đủ metric + period + magnitude + interpretation** | **PASS** | Mọi warning có đầy đủ: giai đoạn, số năm, CAGR, % chênh lệch, tác động và kết luận. |
| **AC3: Có Counter-evidence** | **PASS** | Luôn tìm kiếm bằng chứng phản biện (tiền mặt ròng, phục hồi LNST, ROE duy trì, EPS bảo toàn). |
| **AC4: Phân biệt Cyclical / Structural bằng nhiều bằng chứng** | **PASS** | Đánh giá tổ hợp 3+ tín hiệu cấu trúc hoặc lỗi trọng yếu mới kích hoạt kết luận cấu trúc. |
| **AC5: Không enum backend nào xuất hiện trực tiếp trên UI** | **PASS** | Regex test và audit code xác nhận 0% enum rò rỉ. Toàn bộ dùng tiếng Việt. |
| **AC6: Không còn nullx** | **PASS** | Toàn bộ các hệ số format an toàn, fallback về chuỗi giải thích có nghĩa khi không có giá trị. |
| **AC7: N/A phải có nguyên nhân rõ ràng** | **PASS** | Phân biệt rõ "Không áp dụng (Mô hình tài chính đặc thù)" vs "Chưa đủ dữ liệu lịch sử". |
| **AC8: Áp dụng generic cho toàn bộ universe** | **PASS** | Không phụ thuộc vào bất kỳ mã cổ phiếu cụ thể nào; áp dụng theo Archetype chung. |
| **AC9: Không hard-code ticker** | **PASS** | Không có câu lệnh `if symbol == 'FPT'` hay tương tự trong toàn bộ engine logic. |
| **AC10: Không dùng qualitative UNKNOWN làm blocker** | **PASS** | Hoạt động độc lập ở chế độ financial-statements-only, không bị block bởi Moat/Management UNKNOWN. |
| **AC11: Không phá valuation** | **PASS** | Tích hợp liền mạch với Buffett-Munger policy engine, giữ nguyên công thức định giá cơ sở. |
| **AC12: Test đầy đủ và regression suite phải pass** | **PASS** | Toàn bộ 20/20 test cases trong bộ test mới và golden baseline regression đều PASS 100%. |
| **AC13: Frontend build pass** | **PASS** | `npm --prefix frontend run build` hoàn thành với 0 errors. |
| **AC14: Audit report kết luận rõ PASS/FAIL từng AC** | **PASS** | Báo cáo đầy đủ 14/14 tiêu chí PASS. |

---

## 4. Kết luận Pháp y

Hệ thống Value Trap Analysis của QPort đã hoàn thành việc nâng cấp thành một công cụ **Điều tra Pháp y Tài chính Chuẩn mực Munger**, bảo đảm hỗ trợ nhà đầu tư nhận diện đúng bản chất bẫy giá trị, tránh các cạm bẫy "cổ phiếu giá rẻ nhưng cấu trúc tài chính xói mòn", đồng thời không bỏ lỡ các cơ hội đầu tư phục hồi chu kỳ lành mạnh.
