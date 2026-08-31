# Hướng Dẫn & Công Thức Tính Giá Trị Thực Cơ Sở (Intrinsic Value Formulas)
> **QPort Valuation Engine — Buffett & Munger Value Investing System**  
> **Tài liệu tham chiếu chuẩn:** `docs/specifications/INTRINSIC_VALUE_FORMULAS.md`  
> **Phiên bản:** 2.0.0-PROD

---

## I. Tổng Quan Triết Lý Định Giá (Core Philosophy)

Theo Warren Buffett & Charlie Munger:
> *"Giá trị thực của một doanh nghiệp là hiện giá của toàn bộ dòng tiền mặt có thể rút ra từ doanh nghiệp đó trong suốt thời gian tồn tại còn lại của nó, được chiết khấu về hiện tại theo một mức lãi suất phù hợp."* (Berkshire Hathaway 1986).

Hệ thống QPort phân loại các doanh nghiệp trên sàn chứng khoán Việt Nam thành các **Hình thái Kinh tế (Economic Archetypes)** và áp dụng các mô hình định giá nội tại chuyên biệt:

1. **Doanh nghiệp phi tài chính thông thường (FPT, MWG, VNM, PAN):** Mô hình **Two-Stage Owner Earnings DCF** (Chiết khấu Lợi nhuận Thực 2 giai đoạn).
2. **Doanh nghiệp chu kỳ hàng hóa (DGC, HPG, HSG, DCM):** Mô hình **Mid-Cycle Normalized Owner Earnings DCF** (Chiết khấu Lợi nhuận Trung vị Chu kỳ 7–10 năm).
3. **Ngân hàng thương mại & Tài chính (ACB, MBB, VCB, TCB):** Mô hình **Residual Income Model (RIM)** (Chiết khấu Thu nhập Thặng dư trên Vốn Chủ Sở Hữu).

---

## II. Khung Công Thức Chuẩn Hóa Lợi Nhuận Thực (Normalized Owner Earnings)

Trước khi đưa vào mô hình chiết khấu, dòng tiền cơ sở bắt buộc phải được chuẩn hóa:

$$\text{Owner Earnings (OE)} = \text{Lợi nhuận sau thuế (NI)} + \text{Khấu hao (D\&A)} - \text{CapEx duy trì (Maintenance CapEx)} \pm \Delta \text{Vốn lưu động (WC)}$$

Trong đó:
* **$\text{Maintenance CapEx}$:** Chi phí tái đầu tư tối thiểu để bảo toàn công suất/thị phần. Được ước tính thận trọng qua công thức $\min(\text{D\&A}, |\text{Total CapEx}|)$ hoặc tỷ lệ khấu hao TSCĐ.
* **$\Delta \text{Vốn lưu động (Working Capital)}$:** Đo lường dòng tiền bị giam hoặc giải phóng trong hàng tồn kho và công nợ. $\Delta \text{WC} = \text{CFO} - (\text{NI} + \text{D\&A})$.
* **Chuẩn hóa chu kỳ (Normalization):** Đối với doanh nghiệp chu kỳ hoặc có đột biến lệch pha dòng tiền (ví dụ `CASHFLOW_TIMING_CANDIDATE` của PAN), sử dụng **Trung vị chu kỳ (Mid-Cycle Median)** để loại bỏ nhiễu spike 1 năm.

---

## III. Công Thức Chi Tiết Cho Từng Nhóm Ngành & Ví Dụ Thực Tế

---

### 1. FPT (Doanh nghiệp Tăng trưởng Bền vững — Technology Compounder)

* **Hình thái kinh tế:** `TECHNOLOGY_SERVICES` / `STRUCTURAL_COMPOUNDER`
* **Mô hình định giá:** **Two-Stage Owner Earnings DCF**

#### Công thức toán học:
$$PV(\text{Stage 1}) = \sum_{t=1}^{5} \frac{OE_0 \times (1 + g)^t}{(1 + r)^t}$$

$$\text{Terminal Value}_5 = \frac{OE_5 \times (1 + g_{\text{terminal}})}{r - g_{\text{terminal}}}$$

$$PV(\text{Terminal Value}) = \frac{\text{Terminal Value}_5}{(1 + r)^5}$$

$$\text{Equity Value} = PV(\text{Stage 1}) + PV(\text{Terminal Value})$$

$$\text{Giá trị thực / CP (IV)} = \frac{\text{Equity Value}}{\text{Số cổ phiếu lưu hành}}$$

#### Tham số & Giả định định giá FPT:
* **Lợi nhuận thực cơ sở ($OE_0$):** $~7.800\text{ tỷ ₫}$ (LNST ~9.500 tỷ, D&A ~2.200 tỷ, CapEx duy trì ~2.200 tỷ, $\Delta$WC ổn định).
* **Tăng trưởng Giai đoạn 1 ($g$ - 5 năm):** $15.0\%/\text{năm}$ (xuất khẩu phần mềm + chuyển đổi số toàn cầu).
* **Tỷ suất chiết khấu ($r$):** $10.5\%/\text{năm}$ (Cost of Equity cho doanh nghiệp pháo đài tiền mặt, beta thấp).
* **Tăng trưởng dài hạn ($g_{\text{terminal}}$):** $3.5\%/\text{năm}$.
* **Số CP lưu hành:** $1.460.000.000\text{ CP}$.

#### Kết quả tính toán minh họa:
1. $PV(\text{5 năm dòng tiền}) \approx 39.500\text{ tỷ ₫}$.
2. $PV(\text{Giá trị cuối kỳ}) \approx 138.000\text{ tỷ ₫}$.
3. $\text{Equity Value} \approx 177.500\text{ tỷ ₫}$.
4. $\mathbf{IV_{\text{FPT}}} \approx \frac{177.500\text{ tỷ}}{1.460\text{M CP}} = \mathbf{121.500\text{ ₫/CP}}$.
5. **Biên an toàn yêu cầu ($MoS$):** $20\%$ (doanh nghiệp đạt điểm chất lượng `EXCEPTIONAL` > 85 điểm).

---

### 2. VNM (Bò Sữa Tiền Mặt Tiêu Dùng — Mature Consumer Cash Cow)

* **Hình thái kinh tế:** `CONSUMER_FOOD_BEVERAGE` / `MATURE_CASH_COW`
* **Mô hình định giá:** **Owner Earnings DCF kết hợp Dividend Discount Model (DDM)**

#### Đặc thù tính toán:
VNM đã bước vào giai đoạn bão hòa của ngành sữa nội địa, tăng trưởng chậm nhưng tỷ lệ trả cổ tức tiền mặt rất cao (70–90% LNST), năng lực sinh tiền đều đặn như "trái phiếu coupon thả nổi".

#### Tham số & Giả định định giá VNM:
* **Lợi nhuận thực cơ sở ($OE_0$):** $~9.200\text{ tỷ ₫}$ (LNST ~9.000 tỷ + D&A ~1.800 tỷ - Maint CapEx ~1.600 tỷ).
* **Tăng trưởng Giai đoạn 1 ($g$):** $4.0\%/\text{năm}$ (tăng trưởng ổn định theo tiêu dùng và mở rộng thị trường xuất khẩu).
* **Tỷ suất chiết khấu ($r$):** $10.0\%/\text{năm}$ (doanh nghiệp hàng tiêu dùng thiết yếu, dòng tiền cực kỳ dễ đoán).
* **Tăng trưởng vĩnh viễn ($g_{\text{terminal}}$):** $3.0\%/\text{năm}$.
* **Số CP lưu hành:** $2.089.955.000\text{ CP}$.

#### Kết quả tính toán minh họa:
1. $PV(\text{5 năm dòng tiền}) \approx 37.800\text{ tỷ ₫}$.
2. $PV(\text{Giá trị cuối kỳ}) \approx 110.500\text{ tỷ ₫}$.
3. $\text{Equity Value} \approx 148.300\text{ tỷ ₫}$.
4. $\mathbf{IV_{\text{VNM}}} \approx \frac{148.300\text{ tỷ}}{2.090\text{M CP}} = \mathbf{71.000\text{ ₫/CP}}$.
5. **Biên an toàn yêu cầu ($MoS$):** $20\% - 25\%$.

---

### 3. MWG (Bán Lẻ Chuỗi Tiêu Dùng — Retail Compounder)

* **Hình thái kinh tế:** `CONSUMER_RETAIL`
* **Mô hình định giá:** **Owner Earnings DCF (với Bộ lọc chuẩn hóa Vốn lưu động Bách Hóa Xanh/Thế Giới Di Động)**

#### Đặc thù tính toán:
MWG có đặc tính vốn lưu động biến động lớn theo quý (tích trữ hàng tồn kho trước mùa vụ Tết / mở rộng chuỗi Bách Hóa Xanh). Công thức chuẩn hóa triệt tiêu đột biến hàng tồn kho ngắn hạn để đưa về **Core Owner Earnings**.

#### Tham số & Giả định định giá MWG:
* **Lợi nhuận thực chuẩn hóa ($OE_0$):** $~4.800\text{ tỷ ₫}$ (LNST phục hồi ~4.200 tỷ + D&A ~2.100 tỷ - CapEx mở mới/duy trì ~1.500 tỷ).
* **Tăng trưởng Giai đoạn 1 ($g$):** $12.0\%/\text{năm}$ (động lực từ điểm hòa vốn & tăng trưởng của Bách Hóa Xanh + EraBlue).
* **Tỷ suất chiết khấu ($r$):** $11.0\%/\text{năm}$ (ngành bán lẻ chịu tác động của sức mua vĩ mô).
* **Tăng trưởng vĩnh viễn ($g_{\text{terminal}}$):** $3.5\%/\text{năm}$.
* **Số CP lưu hành:** $1.463.000.000\text{ CP}$.

#### Kết quả tính toán minh họa:
1. $PV(\text{5 năm dòng tiền}) \approx 22.100\text{ tỷ ₫}$.
2. $PV(\text{Giá trị cuối kỳ}) \approx 72.800\text{ tỷ ₫}$.
3. $\text{Equity Value} \approx 94.900\text{ tỷ ₫}$.
4. $\mathbf{IV_{\text{MWG}}} \approx \frac{94.900\text{ tỷ}}{1.463\text{M CP}} = \mathbf{64.800\text{ ₫/CP}}$.
5. **Biên an toàn yêu cầu ($MoS$):** $25\% - 30\%$.

---

### 4. DGC (Chu Kỳ Hóa Chất Cơ Bản — Cyclical Commodity Chemical)

* **Hình thái kinh tế:** `BASIC_MATERIALS_CHEMICALS` / `CYCLICAL_COMMODITY`
* **Mô hình định giá:** **Mid-Cycle Normalized Owner Earnings DCF**

#### Nguyên tắc cốt lõi (UFVS Invariant):
* **Tuyệt đối không lấy LNST đỉnh chu kỳ 2022 (6.037 tỷ ₫) làm gốc tăng trưởng vĩnh viễn.**
* **Không lấy LNST đáy chu kỳ 2019 (570 tỷ ₫) để định giá phá sản.**
* Lấy **Trung vị chu kỳ (Mid-cycle Median)** của giai đoạn comparable regime (2018–2025):

$$OE_{\text{mid-cycle}} = \operatorname{median}(OE_{2018}, OE_{2019}, OE_{2020}, OE_{2021}, OE_{2022}, OE_{2023}, OE_{2024}, OE_{2025})$$

#### Tham số & Giả định định giá DGC:
* **Lợi nhuận thực trung vị chu kỳ ($OE_{\text{normalized}}$):** $~3.100\text{ tỷ ₫}$ (phản ánh mặt bằng giá P4 và quy mô sản xuất sau khi đưa Nghi Sơn vào hoạt động).
* **Tăng trưởng chu kỳ trung bình ($g$):** $5.0\%/\text{năm}$ (tăng trưởng theo nhu cầu bán dẫn và pin xe điện thế giới).
* **Tỷ suất chiết khấu ($r$):** $12.0\%/\text{năm}$ (bù đắp rủi ro biến động giá hàng hóa thế giới).
* **Tăng trưởng vĩnh viễn ($g_{\text{terminal}}$):** $3.0\%/\text{năm}$.
* **Số CP lưu hành:** $379.800.000\text{ CP}$.

#### Kết quả tính toán minh họa:
1. $PV(\text{5 năm dòng tiền}) \approx 13.200\text{ tỷ ₫}$.
2. $PV(\text{Giá trị cuối kỳ}) \approx 30.500\text{ tỷ ₫}$.
3. $\text{Equity Value} \approx 43.700\text{ tỷ ₫}$.
4. $\mathbf{IV_{\text{DGC}}} \approx \frac{43.700\text{ tỷ}}{380\text{M CP}} = \mathbf{115.000\text{ ₫/CP}}$.
5. **Biên an toàn yêu cầu ($MoS$):** $\ge 40\%$ (bắt buộc theo luật đối với cổ phiếu chu kỳ cao).

---

### 5. ACB (Ngân Hàng Thương Mại — Commercial Bank)

* **Hình thái kinh tế:** `COMMERCIAL_BANK`
* **Mô hình định giá:** **Residual Income Model (RIM - Thu Nhập Thặng Dư)**

#### Tại sao không dùng DCF cho Ngân Hàng?
Ngân hàng không có dòng tiền hoạt động (CFO) hay CapEx theo cách hiểu công nghiệp. Tiền là nguyên vật liệu đầu vào và sản phẩm đầu ra. Giá trị của ngân hàng phụ thuộc vào:
1. **Giá trị sổ sách ($BVPS_0$):** Nền tảng vốn tự có hiện tại.
2. **Khả năng tạo ROE vượt trội so với Chi phí vốn ($ROE_t - r_e$):** Thu nhập thặng dư thuộc về cổ đông.

#### Công thức toán học (Mô hình Edwards-Bell-Ohlson):
$$\text{Residual Income}_t = (ROE_t - r_e) \times BVPS_{t-1}$$

$$\text{Giá trị thực / CP (IV)} = BVPS_0 + \sum_{t=1}^{5} \frac{\text{Residual Income}_t}{(1 + r_e)^t} + \frac{\text{Residual Income}_5 \times (1 + g)}{(r_e - g) \times (1 + r_e)^5}$$

#### Tham số & Giả định định giá ACB:
* **Giá trị sổ sách hiện tại ($BVPS_0$):** $~20.500\text{ ₫/CP}$.
* **ROE bền vững dự phóng ($ROE$):** $20.0\%/\text{năm}$ (ACB liên tục duy trì ROE 19–24% qua 10 năm nhờ quản trị rủi ro nợ xấu xuất sắc và CASA cao).
* **Chi phí vốn chủ sở hữu ($r_e$):** $12.0\%/\text{năm}$ (Hurdle rate ngành ngân hàng).
* **Chênh lệch tạo giá trị ($\text{Spread} = ROE - r_e$):** $20.0\% - 12.0\% = +8.0\%/\text{năm}$.
* **Tăng trưởng dài hạn ($g$):** $4.0\%/\text{năm}$.
* **Số CP lưu hành:** $4.466.000.000\text{ CP}$.

#### Kết quả tính toán minh họa:
1. Giá trị sổ sách gốc: $20.500\text{ ₫}$.
2. Hiện giá thu nhập thặng dư 5 năm: $+7.800\text{ ₫}$.
3. Hiện giá thu nhập thặng dư cuối kỳ: $+5.200\text{ ₫}$.
4. $\mathbf{IV_{\text{ACB}}} = 20.500 + 7.800 + 5.200 = \mathbf{33.500\text{ ₫/CP}}$.
5. **Biên an toàn yêu cầu ($MoS$):** $25\% - 30\%$.

---

## IV. Bảng Tổng Hợp So Sánh 5 Doanh Nghiệp Mẫu

| Tiêu chí | FPT | VNM | MWG | DGC | ACB |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Hình thái kinh tế** | Technology Compounder | Consumer Cash Cow | Retail Compounder | Commodity Cyclical | Commercial Bank |
| **Mô hình định giá** | Two-Stage OE DCF | OE DCF + DDM | OE DCF (Adj. WC) | Mid-Cycle OE DCF | Residual Income (RIM) |
| **Dòng tiền cơ sở** | $OE_0 = 7.800\text{ tỷ}$ | $OE_0 = 9.200\text{ tỷ}$ | $OE_{\text{core}} = 4.800\text{ tỷ}$ | $OE_{\text{norm}} = 3.100\text{ tỷ}$ | $BVPS_0 = 20.500\text{ ₫}$ |
| **Tăng trưởng $g$** | $15.0\%$ | $4.0\%$ | $12.0\%$ | $5.0\%$ | $ROE = 20.0\%$ |
| **Chiết khấu ($r$ / $r_e$)** | $10.5\%$ | $10.0\%$ | $11.0\%$ | $12.0\%$ | $r_e = 12.0\%$ |
| **Giá trị thực cơ sở** | **121.500 ₫** | **71.000 ₫** | **64.800 ₫** | **115.000 ₫** | **33.500 ₫** |
| **Biên an toàn (MoS)** | $20\%$ | $20\%$ | $25\%$ | $\mathbf{40\%}$ | $25\%$ |
| **Vùng Mua An Toàn** | $\le 97.000\text{ ₫}$ | $\le 56.800\text{ ₫}$ | $\le 48.600\text{ ₫}$ | $\le 69.000\text{ ₫}$ | $\le 25.100\text{ ₫}$ |

---

## V. Quy Tắc Kiểm Soát & Bất Biến (System Invariants)

1. **Không trừ Net Debt 2 lần:** Khi dòng tiền cơ sở xuất phát từ Net Income (đã trừ chi phí lãi vay), Equity Value là kết quả trực tiếp của chiết khấu, không được phép trừ thêm Net Debt.
2. **Không ngoại lệ theo mã cổ phiếu:** Mọi mã đều tuân theo chuẩn phân loại hình thái và thuật toán UFVS khách quan.
3. **Chỉ công bố khi đạt chuẩn Quality:** Nếu Quality Score < 60 (`LOW_QUALITY`), hệ thống ẩn phần định giá chi tiết và hiển thị cảnh báo để bảo vệ kỷ luật đầu tư giá trị.
