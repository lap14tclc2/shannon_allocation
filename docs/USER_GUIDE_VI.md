# QPort — Hướng dẫn sử dụng đầy đủ (Tiếng Việt)

QPort là **hệ thống thông tin danh mục Buy & Hold cho cổ phiếu cơ sở Việt Nam**.
Hệ thống theo dõi những gì bạn thực sự sở hữu; không tự chọn cổ phiếu, không tự
phân bổ và không tự đặt lệnh.

> Nguyên tắc cốt lõi: **chỉ sự kiện sổ cái được ghi rõ mới thay đổi cổ phiếu hoặc tiền mặt**.

---

## 1. QPort theo dõi những gì?

QPort lưu và tính:

- số cổ phiếu thực tế đang sở hữu;
- giá vốn và tổng cost basis;
- tiền mặt khả dụng của danh mục;
- giá thị trường D1;
- giá trị thị trường và NAV;
- lãi/lỗ chưa thực hiện và đã thực hiện;
- cổ tức, phí và thuế;
- snapshot danh mục từng ngày;
- TWR và XIRR;
- drawdown hiện tại/lớn nhất;
- biến động 63 ngày/252 ngày;
- concentration, HHI và số vị thế hiệu dụng;
- tương quan và diversification ratio;
- đóng góp rủi ro và tham chiếu ERC;
- VaR/CVaR lịch sử và downside risk;
- tỷ trọng tham chiếu tùy chọn.

QPort không thay đổi danh mục chỉ vì một chỉ số, cảnh báo hoặc ngày trên lịch thay đổi.

---

## 2. Cài đặt và khởi động

### 2.1 Frontend

```bash
cd frontend
npm ci
npm run build
npm run build:ssr
```

### 2.2 Python

```bash
cd ../python
pip install -r requirements.txt
```

Bản cơ bản có thể dùng VNDIRECT.

Nếu muốn bật thêm Vnstock:

```bash
pip install -r requirements-vnstock.txt
```

### 2.3 Chạy server

```bash
python serve.py
```

Mở:

```text
http://127.0.0.1:8080/
```

Menu:

```text
Danh mục | Giao dịch | Hiệu suất | Rủi ro | Snapshot | Cài đặt | Hướng dẫn
```

Dùng nút `EN / VI` để đổi ngôn ngữ.

---

## 3. Database và dữ liệu quan trọng

Database mặc định:

```text
python/data/portfolio.sqlite3
```

Dữ liệu quan trọng nhất là **ledger/sổ cái**. Giá thị trường và snapshot là dữ
liệu dẫn xuất, có thể dựng lại.

Hãy backup database trước khi import hàng loạt hoặc thay đổi lớn.

Muốn dùng database khác:

```text
PORTFOLIO_DB=/duong-dan/portfolio.sqlite3
```

---

## 4. Nhập một danh mục đang có từ đầu

Giả sử broker đang hiển thị:

```text
ACB   19.210 CP   giá vốn TB 19.780 VND
DGC   10.000 CP   giá vốn TB 52.340 VND
FPT    3.000 CP   giá vốn TB 74.025 VND
Tiền mặt 50.000.000 VND
```

### Bước 1 — Nhập từng vị thế hiện có

Vào **Giao dịch**.

Chọn:

```text
Nhập vị thế ban đầu
```

Với mỗi mã, nhập:

- ngày;
- mã cổ phiếu;
- số cổ phiếu hiện có;
- giá vốn trung bình tại broker theo **VND đầy đủ**.

Ví dụ:

```text
Mã: FPT
Số CP: 3000
Giá / CP: 74025
```

`POSITION_IMPORT` tạo số cổ phiếu và cost basis nhưng không trừ tiền mặt trong QPort.

Nên dùng ngày mua/chuyển dữ liệu trung thực. Lịch sử Hiệu suất bắt đầu từ các ngày
được đại diện trong ledger; không nên bịa ngày cũ chỉ để có chart dài hơn.

### Bước 2 — Ghi tiền mặt khả dụng

Có hai cách:

- Danh mục → **Quản lý tiền mặt → Nạp tiền**; hoặc
- Giao dịch → **Nạp tiền**.

Ví dụ:

```text
50.000.000 VND
```

Số dư tiền mặt trong ledger là nguồn sự thật cho tiền mặt khả dụng.

### Bước 3 — Chạy đồng bộ lần đầu

Quay lại **Danh mục** và bấm:

```text
Đồng bộ giá ngày
```

Lần sync đầu rất quan trọng. QPort sẽ:

1. lấy lịch sử D1 cho mọi mã từng xuất hiện trong ledger;
2. chuẩn hóa giá cổ phiếu Việt Nam về VND đầy đủ;
3. lưu market prices;
4. replay ledger theo các ngày lịch sử;
5. dựng lại snapshot từng ngày;
6. tạo TWR và lịch sử drawdown;
7. làm đầy trang Hiệu suất và Rủi ro.

Bạn **không cần tự tạo snapshot**.

---

## 5. Đối chiếu accounting trước khi tin analytics

Trước khi dùng Hiệu suất hoặc Rủi ro, hãy so bảng Danh mục với broker.

Với từng mã, kiểm tra:

```text
Số CP
Giá vốn TB
Giá hiện tại
Giá trị vốn
Giá trị thị trường
Lãi/lỗ chưa thực hiện
Tỷ suất
```

Công thức:

```text
Giá trị vốn          = Số CP × Giá vốn TB
Giá trị thị trường   = Số CP × Giá hiện tại
Lãi/lỗ chưa thực hiện= Giá trị thị trường - Giá trị vốn
Tỷ suất chưa thực hiện = Lãi/lỗ chưa thực hiện / Giá trị vốn
```

Ví dụ:

```text
FPT
Số CP        = 3.000
Giá vốn TB   = 74.025 VND
Giá hiện tại = 72.000 VND

Giá trị vốn          = 222.075.000 VND
Giá trị thị trường   = 216.000.000 VND
Lãi/lỗ chưa thực hiện=  -6.075.000 VND
Tỷ suất              ≈ -2,74%
```

Công thức toàn danh mục:

```text
NAV        = Tiền mặt + Σ Giá trị thị trường
Lãi/lỗ tổng= NAV - Dòng tiền ròng bên ngoài
```

Lãi/lỗ tổng là giá trị accounting **live**, không cần phải có snapshot mới tính được.

Nếu Giá, Giá trị vốn, Giá trị thị trường hoặc P/L không khớp broker, hãy dừng lại
và sửa ledger/data trước khi đọc Risk hoặc Performance.

---

## 6. Đơn vị giá và dữ liệu thị trường

QPort lưu giá cổ phiếu Việt Nam theo **VND đầy đủ trên mỗi cổ phiếu**.

Đúng:

```text
FPT = 72.000 VND
```

Sai:

```text
FPT = 72 VND
```

Chính sách provider:

```text
Vnstock nếu đã cài
       ↓ fallback
VNDIRECT
       ↓ lỗi
Giá đã lưu gần nhất + trạng thái CŨ/THIẾU
```

### Trạng thái dữ liệu

**HỢP LỆ** — các mã đang nắm giữ có dữ liệu mới nhất nhất quán.

**CŨ** — ít nhất một mã đang dùng giá đã biết của ngày trước.

**THIẾU** — không có giá cần thiết.

Không nên dùng giá stale để đối chiếu broker như thể đó là dữ liệu hiện tại đầy đủ.

---

## 7. Trang Danh mục

Các card phía trên gồm:

### NAV

Giá trị hiện tại:

```text
Tiền mặt + giá trị thị trường của tất cả vị thế
```

### Giá trị cổ phiếu

Tổng market value của cổ phiếu đang sở hữu.

### Tiền mặt

Tiền khả dụng từ ledger.

### Lãi/lỗ tổng

Mức thay đổi tài sản hiện tại so với dòng vốn ròng của nhà đầu tư.

Nó phản ánh tác động kinh tế của:

- P/L chưa thực hiện;
- P/L đã thực hiện;
- cổ tức;
- phí/thuế;
- tiền mặt còn lại trong danh mục.

### Drawdown hiện tại

Mức giảm từ đỉnh của đường TWR. Sau khi lịch sử được dựng, luôn phải có số — kể
cả `0,00%` khi danh mục đang ở đỉnh mới.

### Biến động 252 ngày

Realized volatility năm hóa từ lịch sử giá đang lưu.

---

## 8. Quản lý tiền mặt

Trang Danh mục có card **Quản lý tiền mặt**.

### Nạp tiền

Chỉ dùng khi tiền thực sự có trong tài khoản/danh mục đang theo dõi. Thao tác tạo
sự kiện `CASH_DEPOSIT`.

### Rút tiền

Chỉ dùng khi tiền thực sự rời danh mục. Thao tác tạo `CASH_WITHDRAW` và không được
làm tiền mặt âm.

### MUA cần tiền đã được ghi nhận

Một sự kiện `BUY` sẽ bị từ chối nếu ledger không đủ tiền.

Đây là behavior có chủ ý: ghi funding trước, sau đó mới ghi giao dịch MUA.

---

## 9. Ghi các sự kiện danh mục thông thường

Dùng **Giao dịch** mỗi khi có sự kiện thật.

### MUA

Nhập số lượng khớp thực tế, giá khớp, phí và thuế.

### BÁN

Nhập execution thực tế. QPort không cho bán nhiều hơn số cổ phiếu đang sở hữu.

### Cổ tức tiền mặt

Dùng `CASH_DIVIDEND` cho số tiền thực tế nhận được. Khoản này tăng cash và là lợi
nhuận đầu tư, không phải vốn nạp thêm.

### Cổ tức cổ phiếu

Dùng `STOCK_DIVIDEND` với số cổ phiếu thực tế được ghi có. Cost basis không đổi,
nên giá vốn trung bình giảm tương ứng.

### Tách/gộp cổ phiếu

Dùng `SPLIT` với tỷ lệ cổ phiếu. Ví dụ tách 2:1 dùng ratio `2`.

### Phí độc lập

Dùng `FEE` cho phí danh mục không nằm trong BUY/SELL.

---

## 10. Sức khỏe danh mục

Portfolio Health là bản tổng hợp chẩn đoán, **không phải lệnh giao dịch**.

Bao gồm:

- tỷ suất tổng;
- drawdown hiện tại/lớn nhất;
- volatility 63D/252D;
- vị thế lớn nhất;
- số vị thế hiệu dụng;
- tương quan trung bình/lớn nhất;
- diversification ratio;
- mã đóng góp rủi ro lớn nhất;
- VaR/CVaR ngày lịch sử 95%;
- độ phủ dữ liệu rủi ro;
- số snapshot chính thức;
- tỷ trọng tiền mặt.

Các cảnh báo có thể gồm:

- dữ liệu stale;
- một mã >= 40% NAV;
- HHI cao;
- tương quan trung bình cao;
- drawdown >= 20%;
- volatility >= 35%;
- lịch sử rủi ro chưa đủ.

Cảnh báo nghĩa là **kiểm tra**, không có nghĩa là **bán**.

---

## 11. Trang Hiệu suất

Sau lần sync lịch sử đầu tiên thành công, trang Hiệu suất không nên còn trống.

### Lãi/lỗ tổng

P/L live từ NAV hiện tại và dòng vốn ròng bên ngoài.

### TWR

Time-weighted return loại ảnh hưởng của nạp/rút tiền.

Dùng TWR để trả lời:

> Bản thân danh mục đã hoạt động thế nào?

### XIRR

Lợi suất năm hóa có trọng số dòng tiền, dùng đúng ngày phát sinh tiền của bạn và
NAV hiện tại.

Dùng XIRR để trả lời:

> Tiền thực tế của tôi đã đạt lợi suất năm hóa bao nhiêu?

### Drawdown

Tính từ TWR wealth index:

```text
Drawdown = TWR hiện tại / đỉnh TWR - 1
```

Do đó nạp/rút tiền không tạo đỉnh hay khoản lỗ giả.

### Các metric khác

- Daily / MTD / YTD;
- TWR năm hóa;
- ngày tốt nhất/xấu nhất;
- tỷ lệ ngày tăng;
- ngày bắt đầu/ngày mới nhất;
- số snapshot chính thức;
- P/L đã/chưa thực hiện;
- cổ tức và phí.

Nếu chart trống, bấm **Dựng lại lịch sử hiệu suất**. Nếu vẫn trống, kiểm tra ngày
trong ledger có nằm trong vùng lịch sử giá khả dụng hay không.

---

## 12. Trang Rủi ro

Toàn bộ Risk chỉ mang tính thông tin.

### Volatility 63D / 252D

Hai khung realized volatility ngắn và dài. Tỷ lệ 63D/252D cho biết rủi ro gần đây
có tăng so với baseline dài hơn hay không.

### HHI và số vị thế hiệu dụng

```text
HHI = Σ weight²
Số vị thế hiệu dụng = 1 / HHI
```

Danh mục có nhiều ticker vẫn có thể chỉ tương đương vài vị thế nếu vốn quá tập trung.

### Tương quan

QPort hiển thị tương quan trung bình và lớn nhất giữa các cặp mã. Tương quan cao
cho thấy số lượng ticker có thể đánh giá quá cao mức đa dạng hóa thật.

### Diversification ratio

So weighted individual volatility với portfolio volatility. Giá trị >1 thể hiện
lợi ích đa dạng hóa trong mẫu dữ liệu đo được.

### Đóng góp rủi ro

Cho biết từng mã đóng góp bao nhiêu vào variance ước tính của danh mục.

### Tham chiếu ERC

Chỉ là tỷ trọng tham khảo nếu muốn cân bằng đóng góp rủi ro. Đây không phải target
bắt buộc và không tạo giao dịch.

### VaR lịch sử 95%

Phân vị 5% của lợi suất danh mục ngày trong mẫu.

### CVaR lịch sử 95%

Lợi suất trung bình của các ngày nằm trong tail dưới ngưỡng VaR.

VaR/CVaR lịch sử không phải dự báo và không phải mức thua lỗ tối đa được đảm bảo.

### Độ phủ dữ liệu

Luôn xem coverage/missing symbols trước khi tin covariance và risk contribution.

---

## 13. Trang Snapshot

Snapshot là checkpoint tự động mỗi ngày gồm:

```text
ngày
holdings từ ledger
tiền mặt
giá đóng cửa
NAV
P/L ngày
lợi suất ngày
TWR index
drawdown
một số trường risk
chất lượng dữ liệu
```

### CHÍNH THỨC

Mọi mã đang active có giá chính xác cùng ngày giao dịch. Các dòng này được dùng
cho Performance chính thức.

### CŨ

Ít nhất một mã dùng giá đã biết của ngày trước. Dòng vẫn hiển thị để chẩn đoán
nhưng bị loại khỏi Performance chính thức.

### Tạo snapshot như thế nào?

Không nhập thủ công. Dùng:

```text
Danh mục → Đồng bộ giá ngày
```

hoặc:

```text
Snapshot → Đồng bộ & dựng lại snapshot
```

QPort tự dựng các checkpoint lịch sử khả dụng từ ngày trong ledger.

---

## 14. Trang Cài đặt

QPort cố ý có rất ít setting.

### Chính sách cố định

Đây không phải tham số để tune:

```text
Chế độ đầu tư       BUY & HOLD
Giao dịch tự động   TẮT
Thay đổi danh mục   Chỉ từ ledger event
Theo dõi hằng ngày  BẬT
```

### Chính sách dữ liệu

Chỉ để bạn hiểu nguồn dữ liệu; bình thường không cần chỉnh.

### Tham chiếu tỷ trọng tùy chọn

Mặc định có thể để:

```text
Tắt — Buy & Hold thuần
```

Chỉ bật nếu muốn:

- nhãn MUA THÊM / GIỮ / XEM XÉT;
- gợi ý chỉ MUA để dùng tiền mặt khả dụng.

Khi bật, nhập tỷ trọng cho tất cả mã active và tổng phải đúng 100%.

Tỷ trọng tham chiếu:

- không hết hạn theo năm;
- không tự tính lại;
- không tạo giao dịch.

---

## 15. Routine hằng ngày

Sau khi thị trường đóng cửa:

1. Mở Danh mục.
2. Đồng bộ giá ngày hoặc để scheduler 15:30 chạy.
3. Kiểm tra dữ liệu HỢP LỆ/CŨ/THIẾU.
4. Đối chiếu NAV/P&L khi cần.
5. Xem cảnh báo Sức khỏe danh mục.
6. Dùng Hiệu suất để hiểu return/drawdown.
7. Dùng Rủi ro để hiểu tập trung/đa dạng hóa.
8. Chỉ ghi transaction khi có sự kiện danh mục thực tế.

Ngày bình thường QPort chủ yếu là hệ thống **quan sát**.

---

## 16. Scheduler

Mặc định:

```text
15:30 Asia/Ho_Chi_Minh vào ngày làm việc
```

Tắt scheduler khi chạy server:

```bash
python serve.py --no-daily-sync
```

Windows Task Scheduler / cron:

```bash
python -m portfolio.cli sync
```

---

## 17. Backup và phục hồi

Backup định kỳ:

```text
python/data/portfolio.sqlite3
```

Nếu market price/snapshot bị hỏng nhưng ledger còn đúng, dữ liệu dẫn xuất có thể
được dựng lại bằng sync.

Không nên sửa trực tiếp ledger rows trong SQLite.

---

## 18. Troubleshooting

### Lãi/lỗ tổng luôn bằng 0

Kiểm tra:

- holdings/cost basis đã nhập;
- đã có giá hiện tại;
- cash deposit/withdraw khớp tài khoản đang theo dõi;
- NAV khớp broker.

Công thức live:

```text
Lãi/lỗ tổng = NAV - dòng vốn ròng bên ngoài
```

### Drawdown không có lịch sử

Chạy sync/rebuild và kiểm tra ngày trong ledger có overlap với lịch sử giá D1.

### Performance chart trống

Bấm **Dựng lại lịch sử hiệu suất**, sau đó xem trang Snapshot có dòng CHÍNH THỨC không.

### Tiền mặt bằng 0

Ghi tiền thật ở Danh mục → Quản lý tiền mặt hoặc bằng sự kiện Nạp tiền.

### P/L sai xấp xỉ 1.000 lần

Kiểm tra đơn vị giá: phải là `72.000 VND`, không phải `72`.

### Risk CHƯA CÓ/MỘT PHẦN

Xem Rủi ro → Chất lượng dữ liệu. Một số mã có thể chưa đủ lịch sử return.

### Snapshot CŨ

Ít nhất một mã active không có giá chính xác ở ngày đó. Snapshot này cố ý không
được dùng trong Performance chính thức.

---

## 19. Checklist trước khi tin QPort

```text
[ ] Số cổ phiếu khớp broker
[ ] Giá vốn TB khớp broker
[ ] Giá dùng VND đầy đủ
[ ] Giá trị vốn = shares × cost
[ ] Market value = shares × price
[ ] Tiền mặt khớp tài khoản theo dõi
[ ] NAV khớp broker ở mức hợp lý
[ ] P/L chưa thực hiện khớp methodology broker ở mức hợp lý
[ ] Hiểu rõ trạng thái dữ liệu
[ ] Có snapshot chính thức sau sync
[ ] Risk coverage đủ trước khi đọc risk metrics
[ ] Có backup database
```

Khi accounting đã reconcile, Hiệu suất, Drawdown và Rủi ro mới thực sự trở thành
thông tin hữu ích thay vì chỉ là những con số trang trí.
