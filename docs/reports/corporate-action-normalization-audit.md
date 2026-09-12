# QPort Corporate Action & Share-Basis Normalization Audit Report

**Date**: 2026-09-12  
**Branch**: `feature/buffett-munger-refactor`  
**Standard**: QPort Canonical Economic Accounting & Valuation Standard  

---

## 1. Executive Summary

Hệ thống QPort đã hoàn thành đợt kiểm tra và chuẩn hóa toàn diện (**Corporate Action & Share-Basis Normalization**) cho toàn bộ pipeline dữ liệu tài chính, giá lịch sử, cổ tức và mô hình định giá:
- **Nguyên lý cốt lõi**: Hành vi tách cổ phiếu (`STOCK_SPLIT`), gộp cổ phiếu (`REVERSE_SPLIT`), thưởng cổ phiếu (`BONUS_SHARE`) hay chia cổ tức bằng cổ phiếu (`STOCK_DIVIDEND`) thuần túy mang tính phi kinh tế (**Non-Economic Share Events**) — chia chiếc bánh sở hữu thành nhiều lát nhỏ hơn, không làm thay đổi giá trị kinh tế thực của doanh nghiệp.
- **Bảo toàn tính nhất quán**: Mọi chỉ số tài chính tính trên mỗi cổ phần (`EPS`, `DPS`, `BVPS`, `Historical Price`) được quy đổi đồng nhất về **cơ sở cổ phần hiện hành (Current Share Basis)**.
- **Không tạo tăng trưởng / suy giảm giả tạo**: Tốc độ tăng trưởng EPS chuẩn hóa khớp hoàn toàn với tốc độ tăng trưởng Lợi nhuận sau thuế của doanh nghiệp ($CAGR(EPS_{norm}) \equiv CAGR(\text{Net Profit})$).
- **Chống điều chỉnh giá hai lần (Anti Double-Adjustment)**: Phân biệt rõ nguồn giá đã điều chỉnh (`PROVIDER_ADJUSTED` như VNDIRECT/VNSTOCK dchart) và nguồn giá thô (`RAW_PRICE`).
- **Chống cộng trùng cổ tức (Zero Double Counting)**: Khẳng định và chứng minh toán học rằng các mô hình dòng tiền tự do (DCF, EPV, RIM) không cộng thêm cổ tức vào giá trị định giá.

---

## 2. Current Architecture & Data Flow

```
[SSI BCTC / TCBS XLSX / VNDirect]
               │
               ▼
   [Raw Financial Observations]
               │
               ▼
   [Canonical Facts DB (FY2011–FY2025)]
               │
               ▼
[Corporate Action Normalizer (TASK-152)]
   ├── Share-Basis Normalization (EPS, DPS, BVPS)
   ├── Anti Double-Adjustment Engine (Prices)
   ├── Total Dividend Economics Preservation
   └── Clean Surplus Retained Earnings Check
               │
               ▼
 [Valuation Engine (DCF, EPV, RIM, SOTP)]
               │
               ▼
[Vietnamese Semantic Presentation Layer]
```

---

## 3. Detailed Normalization Principles

### 3.1. Raw vs Adjusted Price
- **Raw Price**: Giá giao dịch thực tế tại thời điểm $t$ trên sàn giao dịch. Khi có chia tách $k:1$, giá trên sàn sẽ giảm theo tỷ lệ $k$.
- **Adjusted Price**: Giá đã được nhà cung cấp dữ liệu (VNDirect, VNSTOCK dchart API) điều chỉnh lùi quá khứ để chuỗi giá liên tục, phản ánh đúng tỷ suất sinh lời của nhà đầu tư nắm giữ.
- **QPort Invariant**: Nếu dữ liệu đầu vào đã là `PROVIDER_ADJUSTED`, hệ thống **TUYỆT ĐỐI KHÔNG** áp dụng hệ số chia tách thêm một lần nữa.

### 3.2. Share Basis & EPS Normalization
- Khi số lượng cổ phiếu tăng từ $S_{old}$ lên $S_{current}$ qua các đợt chia thưởng:
  $$\text{EPS}_{\text{normalized}}(t) = \frac{\text{Lợi nhuận sau thuế}(t)}{S_{\text{current}}}$$
- Công thức này đảm bảo:
  $$\frac{\text{EPS}_{\text{normalized}}(T)}{\text{EPS}_{\text{normalized}}(t)} = \frac{\text{Lợi nhuận sau thuế}(T)}{\text{Lợi nhuận sau thuế}(t)}$$
- Doanh nghiệp tăng trưởng thực 4x sẽ thể hiện đúng 4x trên EPS chuẩn hóa, không bị hiện tượng "fake EPS crash" do số lượng cổ phiếu tăng lên.

### 3.3. DPS Normalization & Dividend Economics
- Cổ tức tiền mặt lịch sử khi quy đổi về cơ sở cổ phần hiện hành:
  $$\text{DPS}_{\text{normalized}}(t) = \frac{\text{Tổng tiền mặt chi trả cổ tức}(t)}{S_{\text{current}}} = \text{DPS}_{\text{raw}}(t) \times \frac{S(t)}{S_{\text{current}}}$$
- **Tổng dòng tiền cổ tức chi trả không đổi**:
  $$\text{DPS}_{\text{normalized}}(t) \times S_{\text{current}} \equiv \text{Tổng tiền cổ tức}(t)$$

### 3.4. Double Count Protection in Valuation Engine
- **DCF / Owner Earnings**: Định giá dòng tiền tự do thuộc về chủ sở hữu trước khi phân phối. Cổ tức là hình thức phân phối của dòng tiền này, không được cộng thêm vào Equity Value.
- **Bank Residual Income Model (RIM)**:
  $$\text{Giá trị vốn CSH} = \text{Book Value}_0 + \sum_{t=1}^N \frac{(\text{ROE}_t - r_e) \times \text{Book Value}_{t-1}}{(1 + r_e)^t} + \text{Terminal Value}$$
  Theo hạch toán thặng dư sạch (Clean Surplus), $\text{Book Value}_t = \text{Book Value}_{t-1} + \text{Net Income}_t - \text{Dividends}_t$. Cổ tức đã được trừ khỏi Book Value và phản ánh vào dòng tiền trả cho cổ đông; không cộng thêm cổ tức vào mô hình.

### 3.5. Portfolio Position Invariant
- Khi có sự kiện tách cổ phiếu $k:1$ hoặc thưởng cổ phiếu:
  - $\text{Số lượng mới} = \text{Số lượng cũ} \times k$
  - $\text{Giá vốn mới} = \frac{\text{Giá vốn cũ}}{k}$
  - $\text{Tổng vốn đầu tư} = \text{Số lượng mới} \times \text{Giá vốn mới} \equiv \text{Số lượng cũ} \times \text{Giá vốn cũ}$
- Giá trị kinh tế và sổ cái được bảo toàn nguyên vẹn 100%.

---

## 4. Golden Symbols Audit Results

| Mã | Sự kiện quyền | Số CP ban đầu | Số CP hiện hành | Hệ số biến động | Price Adj | EPS Adj | DPS Adj | Double-Count Risk | Status |
|:---|:---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| **FPT** | Cổ phiếu thưởng & Cổ tức CP (15%/năm) | 396,000,000 cp | 1,460,000,000 cp | 3.69x | PASS | PASS | PASS | NO | **PASS** |
| **VIX** | Phát hành tăng vốn & Cổ tức CP | 100,000,000 cp | 1,450,000,000 cp | 14.50x | PASS | PASS | PASS | NO | **PASS** |
| **ACB** | Cổ tức cổ phiếu (15–25%/năm) | 937,000,000 cp | 4,466,000,000 cp | 4.77x | PASS | PASS | PASS | NO | **PASS** |
| **DGC** | Cổ phiếu thưởng & Cổ tức CP | 107,000,000 cp | 379,000,000 cp | 3.54x | PASS | PASS | PASS | NO | **PASS** |

---

## 5. UI Presentation & Semantic Mapping

Toàn bộ thuật ngữ kỹ thuật được ánh xạ sang ngôn ngữ tài chính tiếng Việt:
- `STOCK_SPLIT` $\to$ **"Chia cổ phiếu"**
- `REVERSE_SPLIT` $\to$ **"Chia tách ngược"**
- `BONUS_SHARE` $\to$ **"Cổ phiếu thưởng"**
- `STOCK_DIVIDEND` $\to$ **"Cổ tức cổ phiếu"**
- `CASH_DIVIDEND` $\to$ **"Cổ tức tiền mặt"**
- `ADJUSTED_PRICE` $\to$ **"Giá đã điều chỉnh"**
- `RAW_PRICE` $\to$ **"Giá chưa điều chỉnh"**

Không hiển thị các chuỗi `N/A`, `null`, `nullx`, `UNKNOWN` đối với các trường hợp giải thích đối chiếu thiếu dữ liệu.
