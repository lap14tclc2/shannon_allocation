# QPort Buffett–Munger Value Investing Rule Engine Specification
> **Version:** 2.0.0-PROD  
> **Philosophy:** *Buy & Hold Information System — Economic Reality over Accounting Appearance*  
> **Target Universe:** All Listed Companies on Vietnamese Exchanges (HOSE, HNX, UPCoM)

---

## I. 10 Nguyên Tắc Bất Biến (Hard Invariants)

1. **Circle of Competence (Vòng tròn năng lực):** Chỉ định giá khi mô hình kinh doanh có thể hiểu được và dòng tiền đủ độ dự đoán. Nếu dòng tiền phụ thuộc vào yếu tố bất khả tri, trả về `UNVALUABLE`, tuyệt đối không cố bịa ra Fair Value.
2. **Think Like an Owner (Tư duy người chủ):** Cổ phiếu là quyền sở hữu một phần doanh nghiệp thực tế, không phải tờ vé số đánh bạc theo giá ngày mai.
3. **Demonstrated Earning Power (Năng lực sinh lời đã được chứng minh):** Đánh giá dựa trên chuỗi số liệu tài chính lịch sử đã kiểm chứng (5–10 năm), không dựa vào lời hứa tương lai hay câu chuyện tái cơ cấu kỳ diệu.
4. **Durable Economic Moat (Hào kinh tế bền vững):** Một năm ROE > 20% do đỉnh chu kỳ hàng hóa không phải là Moat. Lợi thế cạnh tranh phải bảo vệ được tỷ suất sinh lời vượt trội trên vốn đầu tư ($ROIC > Cost\ of\ Capital$) qua nhiều năm.
5. **Return on Incremental Invested Capital (iROIC):** Tăng trưởng chỉ tạo ra giá trị khi $Incremental\ ROIC > Hurdle\ Rate$. Tăng trưởng thâm dụng vốn với sinh lời thấp là hành vi phá hủy giá trị.
6. **Balance Sheet Resilience (Pháo đài tài chính):** Bảng cân đối kế toán phải đủ sức sống sót qua những thời kỳ đen tối nhất. Đòn bẩy tài chính phải được đo lường tương thích theo từng hình thái kinh tế.
7. **Management as Capital Allocator (Phân bổ vốn là thước đo quản trị):** Đánh giá ban lãnh đạo qua hiệu quả sử dụng từng đồng lợi nhuận giữ lại để gia tăng giá trị nội tại trên mỗi cổ phần, không phải mở rộng quy mô doanh thu/tài sản cơ học.
8. **Growth is a Variable of Value (Tăng trưởng là một biến số của giá trị):** Tăng trưởng không đối lập với giá trị. $g = Reinvestment\ Rate \times Incremental\ ROIC$.
9. **Intrinsic Value = Discounted Future Cash Economics:** Giá trị nội tại là hiện giá của toàn bộ dòng tiền kinh tế có thể rút ra trong tương lai của doanh nghiệp, không phải mục tiêu P/E hay giá mục tiêu của công ty chứng khoán.
10. **Margin of Safety (Biên an toàn là luật bắt buộc):** Biên an toàn phải bù đắp được sự bất định về ngành, rủi ro chu kỳ và cấu trúc vốn. $MOS = \frac{Intrinsic\ Value - Price}{Intrinsic\ Value}$.

---

## II. Quy Chuẩn Xử Lý Dữ Liệu Toàn Thị Trường (Universal Data Normalization Rules)

| Quy tắc | Chính sách bắt buộc của QPort |
|---|---|
| **Financial History** | Ưu tiên 10 năm tài chính kiểm toán; tối thiểu 5 năm để Quality Score có hiệu lực. |
| **Accounting Statements** | Báo cáo tài chính Hợp nhất (Consolidated) > Báo cáo Công ty Mẹ (Standalone). |
| **Audit Requirement** | Số liệu năm kiểm toán là nguồn Canonical chính thức. |
| **Quarterly TTM** | Số liệu quý dùng cho TTM, không thay thế chuỗi năm lịch sử. |
| **CapEx Cash Flow** | Dòng tiền chi mua sắm TSCĐ luôn được quy chuẩn về số dương kinh tế $|CapEx|$. |
| **Free Cash Flow (FCF)** | $FCF = CFO - |CapEx|$, tuyệt đối không cộng ngược CapEx vào FCF. |
| **Stock Dividends / Bonus** | Cổ tức bằng cổ phiếu & cổ phiếu thưởng không bị tính là pha loãng kinh tế thực (True Economic Dilution). |
| **Banks / Financials** | Tuyệt đối không dùng dòng tiền hoạt động (CFO) hay FCFF công nghiệp để định giá ngân hàng. |

---

## III. Hệ Thống Điểm Chất Lượng Doanh Nghiệp (Buffett Quality Score - Thang 100)

Hệ thống chấm điểm Business Quality Score dựa trên 7 trụ cột định lượng và định tính:

1. **Business Predictability (10 điểm):** Độ ổn định doanh thu & biên lợi nhuận qua các năm.
2. **Economic Moat (20 điểm):** Lợi thế cạnh tranh bền vững (Thương hiệu, Chi phí thấp, Chuyển đổi, Mạng lưới, Quy mô, Giấy phép).
3. **Return + Reinvestment Economics (20 điểm):** $ROIC \ge 15\%$, $ROIC\ Spread > 0$, $iROIC > Hurdle\ Rate$.
4. **Financial Strength & Fortress (15 điểm):** $Net\ Debt / EBITDA$, khả năng thanh toán lãi vay, pháo đài tiền mặt ròng.
5. **Earnings & Cash Quality (10 điểm):** Tỷ lệ chuyển hóa tiền mặt 5 năm ($CFO / Net\ Profit \ge 80\%$).
6. **Capital Allocation Discipline (15 điểm):** Bảo toàn tỷ lệ sở hữu, chính sách cổ tức hợp lý, tái đầu tư hiệu quả.
7. **Governance & Shareholder Alignment (10 điểm):** Minh bạch thông tin, tỷ lệ sở hữu của ban lãnh đạo, giao dịch bên liên quan lành mạnh.

### Bảng Xếp Hạng Chất Lượng:
- **90 – 100:** `EXCEPTIONAL` (Doanh nghiệp xuất sắc hiếm có)
- **80 – 89:** `HIGH_QUALITY` (Doanh nghiệp chất lượng cao)
- **70 – 79:** `INVESTABLE` (Doanh nghiệp đạt chuẩn đầu tư giá trị)
- **60 – 69:** `WATCH` (Cần theo dõi thêm chu kỳ)
- **< 60:** `LOW_QUALITY` (Chưa đạt chuẩn chất lượng)

---

## IV. Phân Loại 21 Hình Thái Kinh Tế (21 Economic Archetypes & Overlays)

```
                            COMPANY CLASSIFIER
                                     │
           ┌─────────────────────────┴─────────────────────────┐
           ▼                                                   ▼
     NON-FINANCIAL                                         FINANCIAL
     ├── Structural Compounders (FPT, MWG, VNM)           ├── Commercial Banks (MBB, ACB, VCB)
     ├── Cyclicals / Commodities (HPG, DGC, DCM)          ├── Securities Firms (SSI, VCI, HCM)
     ├── Utilities & Infrastructure (GAS, POW, REE, GMD)  └── Insurance Underwriters (BVH, PVI, BMI)
     ├── Real Estate Developers & Industrial Parks (VHM, KBC)
     └── Aviation, Shipping & Logistics (VJC, HVN, HAH)
```

### Chi Tiết Mô Hình Định Giá Cho Từng Hình Thái:
1. **Ngân Hàng Thương Mại (Commercial Banks):**
   - *Mô hình chính:* **Residual Income Model (RIM)**:
     $$V_0 = BVPS_0 + \sum_{t=1}^5 \frac{BVPS_{t-1} \times (ROE_t - r_e)}{(1 + r_e)^t} + \frac{BVPS_5 \times (ROE_{\text{term}} - r_e)}{(r_e - g) \times (1 + r_e)^5}$$
   - *Sanity Check:* Justified P/B: $\frac{ROE - g}{r_e - g}$.
   - *MOS Tối thiểu:* $25\% - 30\%$.

2. **Công Ty Chứng Khoán (Securities Firms):**
   - *Mô hình chính:* Normalized ROE Residual Income + Normalized P/B qua chu kỳ thanh khoản thị trường.
   - *MOS Tối thiểu:* $30\% - 35\%$.

3. **Bảo Hiểm (Insurance Underwriters):**
   - *Mô hình chính:* Adjusted Book Value + Float Cost Analysis + DDM.
   - *MOS Tối thiểu:* $25\% - 35\%$.

4. **Doanh Nghiệp Hợp Thành Giá Trị Bền Vững (Structural Compounders - FPT, VNM):**
   - *Mô hình chính:* Owner Earnings DCF 3 Kịch bản + EPV.
   - *MOS Tối thiểu:* $20\% - 25\%$.

5. **Doanh Nghiệp Chu Kỳ / Hàng Hóa (Commodities / Cyclicals - HPG, DGC, DCM):**
   - *Mô hình chính:* 5–10Y Mid-Cycle Normalized Owner Earnings DCF + Trough Balance Sheet Check.
   - *MOS Tối thiểu:* $40\%+$.

6. **Điện, Nước, Tiện Ích Hạ Tầng (Utilities & Regulated Infrastructure - GAS, POW, REE):**
   - *Mô hình chính:* Contracted Cash Flow DCF + Dividend Discount Model (DDM).
   - *MOS Tối thiểu:* $20\% - 30\%$.

7. **Bất Động Sản Dân Dụng & KCN (Real Estate Developers & Industrial Parks):**
   - *Mô hình chính:* Revalued Net Asset Value (RNAV) / Project DCF + Adjusted P/B.
   - *MOS Tối thiểu:* $35\% - 50\%$.

8. **Hàng Không & Vận Tải Biển (Airlines & Shipping - HVN, VJC):**
   - *Mô hình chính:* Through-cycle EBITDAR / Fleet NAV. Nếu biến động không thể dự báo $\rightarrow$ Đánh dấu `UNVALUABLE`.
   - *MOS Tối thiểu:* $45\% - 50\%$.

---

## V. Động Học Biên An Toàn (Dynamic Margin of Safety Engine)

Biên an toàn yêu cầu được tính toán tự động:
$$\text{Required MOS} = \text{Base MOS}_{\text{Sector}} + \text{Cyclicality Penalty} + \text{Leverage Penalty} + \text{Confidence Penalty} - \text{Predictability Discount}$$

- **Giới hạn cận:** $20\% \le \text{Required MOS} \le 50\%$.

---

## VI. Bộ Quy Tắc Từ Chối Cứng (Hard Reject Rules)

Khi kích hoạt các cờ sau, hệ thống lập tức khóa định giá và chuyển sang trạng thái cảnh báo, không phát sinh kết luận mua:
- `CIRCLE_OF_COMPETENCE_FAIL`: Mô hình kinh doanh không thể dự báo hoặc phụ thuộc vào yếu tố ngẫu nhiên.
- `ACCOUNTING_UNRELIABLE`: BCTC có ý kiến ngoại trừ, nghi vấn kiểm toán hoặc dòng tiền âm kéo dài bất thường dù lãi lớn.
- `SOLVENCY_RISK`: Áp lực nợ ngắn hạn vượt quá thanh khoản tạo tiền mặt trong kỳ suy thoái.
- `UNNORMALIZABLE_EARNINGS`: Chu kỳ lợi nhuận quá ngắn (<3 năm dữ liệu) hoặc biến động cực đoan không thể chuẩn hóa.

---

## VII. Hệ Thống Khuyến Nghị Giá Trị Cuối Cùng (Final Value Statuses)

| Trạng thái | Tiêu chuẩn đạt được |
|---|---|
| `HIGH_CONVICTION_VALUE` | Quality Score $\ge 80$, Moat $\ge$ NARROW, Financial Fortress PASS, Không có Hard Reject, và MOS thực tế $\ge$ Required MOS. |
| `ATTRACTIVE` | Doanh nghiệp đạt chuẩn đầu tư, thị giá chiết khấu tốt dưới giá trị nội tại Base. |
| `FAIRLY_VALUED` | Thị giá nằm quanh vùng giá trị nội tại hợp lý ($-15\% \le MOS \le 15\%$). |
| `WATCH` | Doanh nghiệp tốt nhưng giá chưa đủ rẻ hoặc cần thêm thời gian theo dõi chu kỳ. |
| `AVOID_QUALITY` | Doanh nghiệp có vấn đề về chất lượng quản trị, đòn bẩy hoặc hiệu quả vốn yếu kém. |
| `UNVALUABLE` | Nằm ngoài vòng tròn năng lực, dữ liệu không thể chuẩn hóa dòng tiền tin cậy. |
