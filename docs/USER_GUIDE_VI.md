# QPort — Hướng dẫn sử dụng đầy đủ (Tiếng Việt)

Tài liệu này bắt đầu từ máy/database trống và đi đến routine vận hành hằng ngày.

QPort là **hệ thống thông tin Buy & Hold cho danh mục cổ phiếu cơ sở Việt Nam**. Đây không phải hệ thống giao dịch tự động.

> Nguyên tắc cốt lõi: **chỉ các sự kiện được ghi rõ trong ledger mới thay đổi số cổ phiếu hoặc tiền mặt**. Giá thị trường, risk metrics, kết quả research, thời gian hoặc mốc cuối năm không bao giờ tự tạo giao dịch danh mục.

---

## 1. QPort làm gì

Operational QPort theo dõi:

- cổ phiếu thực tế đang sở hữu và tiền mặt;
- giá vốn trung bình và cost basis;
- giá thị trường hằng ngày;
- market value và NAV;
- lãi/lỗ đã thực hiện và chưa thực hiện;
- cổ tức, phí, thuế được ghi vào ledger;
- TWR và XIRR;
- drawdown và volatility;
- concentration và risk contribution;
- optional strategic reference weights dài hạn;
- gợi ý chỉ MUA để dùng tiền mặt hiện có;
- daily snapshots bất biến theo ngày.

QPort **không tự động**:

- mua hoặc bán cổ phiếu;
- xoay vòng mã;
- rebalance hằng năm;
- giảm equity vì volatility tăng;
- áp kết quả optimizer vào live portfolio.

Các công cụ nghiên cứu được cô lập dưới `/research`.

---

## 2. Yêu cầu môi trường

Khuyến nghị:

- Python 3.11+
- Node.js 22+
- npm
- Internet để đồng bộ dữ liệu thị trường

Database operational mặc định được lưu local.

Đường dẫn mặc định:

```text
python/data/portfolio.sqlite3
```

Thư mục runtime này không được commit vào Git.

---

## 3. Cài đặt từ đầu

Lấy code và checkout nhánh Buy & Hold:

```bash
git fetch origin
git checkout refactor-buy-hold
git pull origin refactor-buy-hold
```

Build frontend:

```bash
cd frontend
npm ci
npm run build
npm run build:ssr
```

Cài Python dependencies:

```bash
cd ../python
python -m pip install --upgrade pip
pip install -r requirements.txt
```

### Optional: bật Vnstock

Base system có thể chạy với VNDIRECT fallback. Nếu muốn dùng thêm Vnstock:

```bash
pip install -r requirements-vnstock.txt
```

Chính sách market data mặc định:

```text
Vnstock nếu cài được và truy cập được
        ↓ lỗi
VNDIRECT daily history
        ↓ lỗi
last stored price + trạng thái stale/missing rõ ràng
```

---

## 4. Khởi động QPort

Từ thư mục `python`:

```bash
python serve.py
```

Mở:

```text
http://127.0.0.1:8080/
```

Navigation operational:

```text
Danh mục | Giao dịch | Hiệu suất | Rủi ro | Ảnh chụp | Cài đặt | Hướng dẫn | Nghiên cứu
```

---

## 5. Chuyển English / Vietnamese

Dùng nút `EN` / `VI` trên thanh navigation.

Ngôn ngữ đã chọn được lưu trong browser cookie `qport_lang` và được dùng lại ở lần mở app sau.

Nếu chưa từng chọn ngôn ngữ, QPort dùng `Accept-Language` của browser làm mặc định ban đầu và fallback về English nếu không nhận diện được.

Các màn hình operational QPort hỗ trợ English và Vietnamese. Các màn hình optimizer/detail cũ trong Research Lab là legacy tooling nên có thể vẫn còn label tiếng Anh.

---

# PHẦN A — TẠO DANH MỤC BAN ĐẦU

## 6. Bắt đầu với database trống

Database mới phải hiển thị không có holdings. Đây là behavior đúng.

QPort không tự tạo sample portfolio và không suy ra số cổ phiếu từ market data.

Nguồn sự thật là ledger.

---

## 7. Nhập các vị thế đang sở hữu

Vào:

```text
Giao dịch → Ghi nhận sự kiện danh mục
```

Với mỗi cổ phiếu đã sở hữu trước khi bắt đầu dùng QPort, chọn:

```text
Nhập vị thế ban đầu
```

Các field bắt buộc:

- Ngày
- Mã
- Số cổ phiếu
- Giá / cổ phiếu (VND)

Trong `Nhập vị thế ban đầu`, **Price là giá vốn trung bình/cổ phiếu mà bạn muốn QPort theo dõi**, không phải giá thị trường hôm nay.

Ví dụ:

```text
Mã: FPT
Số CP: 3,000
Giá vốn TB: 74,025 VND
```

Nhập:

```text
Loại sự kiện: Nhập vị thế ban đầu
Mã: FPT
Số CP: 3000
Giá/CP: 74025
```

QPort tạo:

```text
cost basis = 3,000 × 74,025
           = 222,075,000 VND
```

Opening import được xem như external portfolio contribution cho mục đích đo hiệu suất. Nó không giả vờ rằng QPort từng có cash rồi thực hiện một lệnh BUY trong quá khứ.

### Quan trọng

Luôn nhập giá theo **VND đầy đủ**:

```text
Đúng:  72,000
Sai:   72
```

Một số provider dữ liệu Việt Nam có thể trả dạng exchange-style như `72.0`; QPort chuẩn hóa giá provider về full VND trước khi định giá.

---

## 8. Nhập tiền mặt ban đầu

Nếu danh mục đang theo dõi có cash, nhập riêng:

```text
Loại sự kiện: Nạp tiền
Số tiền: 50,000,000 VND
```

Không đưa vào QPort phần tiền broker nằm ngoài phạm vi danh mục bạn muốn theo dõi.

Phạm vi portfolio phải nhất quán theo thời gian.

---

## 9. Kiểm tra trạng thái ban đầu trước khi tiếp tục

Sau khi nhập hết holdings và cash, quay về Danh mục.

Trước khi tin P/L, kiểm tra:

1. đủ tất cả ticker;
2. số cổ phiếu khớp broker;
3. giá vốn trung bình khớp cost basis bạn muốn theo dõi;
4. cash khớp số dư tiền thuộc phạm vi portfolio.

Ứng dụng cố ý không cung cấp update/delete API thông thường cho ledger history. Hãy kiểm tra dữ liệu kỹ trước khi submit.

Nếu nhập sai một historical event làm ledger sai đáng kể, ưu tiên restore database backup đúng thay vì tạo một giao dịch giả để che lỗi.

---

# PHẦN B — MARKET DATA VÀ DAILY SNAPSHOT

## 10. Đồng bộ market data lần đầu

Tại Danh mục bấm:

```text
Đồng bộ giá ngày
```

Hoặc command line:

```bash
cd python
python -m portfolio.cli sync
```

Với mỗi ticker đang nắm giữ, QPort cố gắng:

1. tải đủ D1 history cho analytics;
2. normalize OHLC về canonical VND;
3. lưu market prices local;
4. tính portfolio risk diagnostics;
5. mark-to-market danh mục;
6. tạo/cập nhật daily snapshot.

---

## 11. Kiểm tra bảng Holdings

Với mỗi position, kiểm tra các cột:

```text
Số CP
Giá vốn TB
Giá hiện tại
Giá trị vốn
Giá trị thị trường
Lãi/lỗ chưa thực hiện
Tỷ suất
Tỷ trọng
Đóng góp rủi ro
Trạng thái
```

Các identity kế toán:

```text
Giá trị vốn
= Số CP × Giá vốn TB

Giá trị thị trường
= Số CP × Giá thị trường hiện tại

Lãi/lỗ chưa thực hiện
= Giá trị thị trường − Giá trị vốn

Tỷ suất chưa thực hiện
= Lãi/lỗ chưa thực hiện / Giá trị vốn
```

Ví dụ:

```text
FPT
Số CP             3,000
Giá vốn TB       74,025 VND
Giá thị trường   72,000 VND

Giá trị vốn      222,075,000 VND
Giá trị TT       216,000,000 VND
Lãi/lỗ            -6,075,000 VND
Tỷ suất                -2.74%
```

Nếu giá hiển thị là `72 VND` thay vì khoảng `72,000 VND`, dừng lại và kiểm tra normalization trước khi tin NAV hoặc P/L.

---

## 12. Hiểu trạng thái dữ liệu

### VALID / HỢP LỆ

Tất cả ticker đang nắm giữ có cùng latest trading date và snapshot có thể được đánh dấu official.

### STALE / CŨ

Ít nhất một ticker có stored price cũ hơn ticker mới nhất.

QPort vẫn có thể hiển thị estimated portfolio state để chẩn đoán, nhưng không nên coi dữ liệu stale là official performance evidence.

### MISSING / THIẾU

Ít nhất một ticker không có usable stored market price.

Cần kiểm tra provider/symbol trước khi tin valuation.

---

## 13. Official snapshot và non-official snapshot

Một daily snapshot kết hợp:

```text
immutable ledger state
+
stored market prices
+
derived portfolio analytics
```

Chỉ snapshot có dữ liệu tươi/đầy đủ mới được đánh dấu official.

Performance chart chỉ sử dụng official snapshots.

Mục tiêu là không để một lỗi provider tạm thời biến thành một điểm NAV chính thức giả.

---

# PHẦN C — GHI NHẬN HOẠT ĐỘNG DANH MỤC THỰC TẾ

## 14. Tham chiếu các loại event

### POSITION_IMPORT — Nhập vị thế ban đầu

Chỉ dùng khi thiết lập/migrate một vị thế đã sở hữu trước khi QPort theo dõi.

Tác động:

```text
shares += quantity
cost basis += quantity × price
external contributions += cùng cost basis
```

Không tiêu thụ cash.

---

### CASH_DEPOSIT — Nạp tiền

Dùng khi tiền mới thực sự đi vào tracked portfolio.

Tác động:

```text
cash += amount
external contributions += amount
```

External deposits được neutralize trong TWR.

---

### BUY — Khớp lệnh mua

Chỉ ghi sau khi broker thực sự khớp lệnh MUA.

Cần:

- ticker;
- quantity;
- execution price;
- optional fee;
- optional tax.

Tác động gần đúng:

```text
position cost basis += gross purchase + buy fee
shares += quantity
cash -= gross purchase + fee + tax
```

QPort từ chối BUY nếu tracked cash bị âm. Hãy ghi funding trước.

---

### SELL — Khớp lệnh bán

Chỉ ghi sau khi broker thực sự khớp lệnh BÁN.

QPort từ chối SELL lớn hơn số cổ phiếu ledger đang sở hữu.

Realized P/L dùng average cost hiện tại và execution costs.

---

### CASH_WITHDRAW — Rút tiền

Dùng khi tiền rời khỏi tracked portfolio.

Tác động:

```text
cash -= amount
external withdrawals += amount
```

Đây là external flow, không phải investment loss.

---

### CASH_DIVIDEND — Cổ tức tiền mặt

Ghi số tiền thực tế đã được credit vào tracked portfolio.

Khuyến nghị: nhập **số tiền net thực nhận từ broker account** để QPort không phải tự đoán tax treatment.

Tác động:

```text
cash += amount
dividend income += amount
```

---

### STOCK_DIVIDEND — Cổ tức cổ phiếu

Ghi đúng số cổ phiếu mới thực tế được credit.

Tác động:

```text
shares += credited shares
cost basis không đổi
average cost giảm cơ học
```

Ví dụ:

```text
Trước: 3,000 shares
Cổ tức CP được credit: 450 shares
Sau:   3,450 shares
```

---

### SPLIT — Tách/gộp cổ phiếu

Nhập multiplicative ratio `new shares / old shares`.

Ví dụ tách 2-for-1:

```text
ratio = 2
```

Tác động:

```text
shares *= ratio
cost basis không đổi
average cost thay đổi ngược với ratio
```

---

### FEE — Phí độc lập

Dùng cho phí portfolio-level không nằm trong BUY/SELL.

Tác động:

```text
cash -= amount
fees_and_taxes += amount
```

---

## 15. Kỷ luật ledger

Hãy xem ledger như lịch sử kế toán, không phải scratchpad.

Quy tắc:

- không nhập một suggested trade trước khi thực sự khớp;
- dùng quantity/price đã được broker xác nhận;
- ghi fee/tax nhất quán;
- ghi corporate action khi cash/shares thực sự được credit;
- không tạo BUY/SELL giả để ép dashboard về con số mong muốn.

---

# PHẦN D — ĐỌC DASHBOARD

## 16. NAV

NAV hiện tại:

```text
NAV = cash + Σ(position shares × current market price)
```

Biến động giá thay đổi NAV và market value, nhưng **không** thay đổi số cổ phiếu.

---

## 17. Total P/L

Current system so sánh NAV với net external contributions cho field total P/L trong snapshot.

Dùng Position Unrealized P/L để xem open P/L theo từng mã và dùng Performance cho return time series.

Không nhầm lẫn:

```text
P/L amount
với
TWR percentage return
với
XIRR investor return
```

Ba metric trả lời ba câu hỏi khác nhau.

---

## 18. HOLD / ADD / REVIEW

Các label này chỉ mang tính thông tin.

Nếu chưa đặt strategic reference weights, positions thường giữ trạng thái HOLD trừ khi một informational policy khác đánh dấu.

Khi có reference weights:

```text
thấp đáng kể hơn reference → ADD / MUA THÊM
gần reference              → HOLD / GIỮ
cao đáng kể hơn reference  → REVIEW / XEM XÉT
```

Không label nào tự tạo transaction.

---

## 19. Deploy existing cash

QPort có thể hiển thị BUY-only cash-deployment suggestions.

Mục đích:

```text
cash hiện có
→ ưu tiên held positions đang underweight
→ gợi ý số tiền
```

Suggestion không phải execution.

Sau khi broker thực sự khớp lệnh, user tự ghi BUY event.

---

# PHẦN E — HIỆU SUẤT

## 20. TWR

Time-Weighted Return đo investment performance của portfolio trong khi neutralize external flows như deposit, withdrawal và opening import.

Dùng TWR khi hỏi:

> Danh mục tự thân hoạt động như thế nào, không phụ thuộc lúc tôi nạp thêm tiền?

---

## 21. XIRR

XIRR dùng dated investor cash flows và latest official NAV.

Dùng XIRR khi hỏi:

> Với thời điểm tiền thật của tôi đi vào/ra khỏi danh mục, tôi thực tế đạt mức return nào?

TWR và XIRR có thể khác nhau hoàn toàn hợp lý.

---

## 22. Official NAV history

Performance chart chỉ dùng official daily snapshots.

Nếu chưa có đủ official snapshots, một số period metrics sẽ chưa có. Điều đó tốt hơn việc fabricate history.

---

# PHẦN F — RỦI RO

## 23. Risk là thông tin, không phải execution

Trang Rủi ro có thể hiển thị:

- 63D volatility;
- 252D volatility;
- largest position;
- HHI concentration;
- risk contribution theo ticker;
- ERC equal-risk reference;
- data coverage.

Operational QPort không phản ứng bằng cách tự SELL hoặc giảm equity.

---

## 24. Risk contribution

Capital weight và risk contribution là hai khái niệm khác nhau.

Ví dụ:

```text
DGC capital weight       40%
DGC risk contribution    58%
```

Điều đó cho biết DGC đóng góp không cân xứng vào volatility/covariance risk của portfolio.

Đây là lý do để **xem xét thông tin**, không phải lệnh bán tự động.

---

## 25. ERC reference

ERC hỏi: với covariance estimate hiện tại, relative weights nào sẽ xấp xỉ cân bằng risk contribution giữa các mã.

Trong operational QPort ERC chỉ là diagnostic reference.

ERC không:

- hết hạn theo năm;
- thay thế holdings của user;
- tạo rebalance schedule;
- tạo order.

---

# PHẦN G — STRATEGIC REFERENCE WEIGHTS

## 26. Cấu hình reference

Vào Cài đặt.

Reference weights là optional.

Nếu dùng, tổng phải bằng:

```text
100%
```

Ví dụ:

```text
ACB  30%
DGC  20%
FPT  30%
REE  20%
```

References tồn tại dài hạn cho tới khi user tự đổi.

Không tự recalculate mỗi năm.

---

## 27. Reference weights làm gì

Chúng có thể ảnh hưởng:

- HOLD / ADD / REVIEW labels;
- BUY-only suggestions cho cash đang có.

Chúng không mutate ledger.

---

# PHẦN H — ROUTINE VẬN HÀNH HẰNG NGÀY

## 28. EOD routine khuyến nghị

Sau khi thị trường Việt Nam đóng cửa:

1. Mở Danh mục.
2. Chạy/xác nhận `Đồng bộ giá ngày`.
3. Kiểm tra Data status là VALID/HỢP LỆ.
4. Xem NAV và daily/total P/L.
5. Kiểm tra nhanh giá hoặc số lượng bất thường.
6. Xử lý ticker stale/missing nếu có.
7. Mở Rủi ro khi cần context về concentration/risk.
8. Chỉ ghi ledger event mới nếu thực sự có portfolio event.

Routine này bình thường chỉ mất vài phút.

---

## 29. Automatic EOD scheduler

Khi server chạy liên tục, QPort khởi động scheduler idempotent lúc:

```text
15:30 Asia/Ho_Chi_Minh
```

vào ngày làm việc.

Đổi giờ trên Windows:

```bash
set PORTFOLIO_SYNC_TIME=16:00
python serve.py
```

Linux:

```bash
PORTFOLIO_SYNC_TIME=16:00 python serve.py
```

Tắt in-process scheduler:

```bash
python serve.py --no-daily-sync
```

Sau đó có thể schedule:

```bash
python -m portfolio.cli sync
```

bằng Windows Task Scheduler hoặc cron.

---

# PHẦN I — BACKUP VÀ PHỤC HỒI

## 30. File quan trọng nhất cần backup

```text
python/data/portfolio.sqlite3
```

Ledger trong database này là operational source of truth.

Khuyến nghị backup:

- trước bulk migration/import;
- sau portfolio change quan trọng;
- định kỳ, ví dụ mỗi ngày hoặc mỗi tuần.

---

## 31. Đổi vị trí database

Dùng `PORTFOLIO_DB`.

Windows:

```bash
set PORTFOLIO_DB=D:\qport-data\portfolio.sqlite3
python serve.py
```

Linux:

```bash
PORTFOLIO_DB=/srv/qport/portfolio.sqlite3 python serve.py
```

---

## 32. Dữ liệu nguồn sự thật và dữ liệu dẫn xuất

Về mặt khái niệm:

```text
Ledger events              SOURCE OF TRUTH
Reference weights          User configuration
Market prices              External/re-fetchable data
Portfolio snapshots        Derived
Risk metrics               Derived
Performance metrics        Derived
Research results           Isolated evidence
```

Bảo vệ ledger cẩn thận nhất.

---

# PHẦN J — TROUBLESHOOTING

## 33. Giá hiển thị 72 thay vì 72,000

Canonical unit phải là full VND/share.

QPort có normalization/migration cho exchange-style price units của VNDIRECT/Vnstock.

Cách xử lý:

1. cập nhật code mới nhất trên branch;
2. restart QPort để database migration chạy;
3. Sync daily prices lại;
4. kiểm tra Price, Market value và Unrealized P/L.

Không tin các old P/L snapshots được tạo từ wrong price unit.

---

## 34. Data status là STALE

Nguyên nhân có thể:

- provider lỗi;
- một ticker không có giá ở freshest date;
- symbol/provider issue;
- network problem.

Kiểm tra:

- provider connectivity;
- latest trading date từng holding;
- hôm đó thị trường có mở không;
- retry Sync daily prices.

Provider failure không làm thay đổi holdings.

---

## 35. Risk hiển thị UNAVAILABLE

Risk analytics cần đủ overlapping price history.

Nguyên nhân thường gặp:

- ticker mới import chưa có đủ stored history;
- provider gaps;
- quá ít usable covariance observations.

Trạng thái này không thay đổi shares.

---

## 36. BUY bị từ chối vì cash âm

Nếu funding thực sự thuộc tracked portfolio, ghi cash trước:

```text
Nạp tiền
→ broker BUY thật
→ BUY event
```

Không bypass accounting invariant này.

---

## 37. SELL bị từ chối

QPort ngăn bán nhiều hơn số shares ledger cho rằng đang sở hữu.

Kiểm tra:

- opening imports;
- stock dividends;
- splits;
- prior SELL events.

Sửa underlying ledger history thay vì ép lệnh SELL mới.

---

## 38. Snapshot không thành official

Kiểm tra:

- data quality là VALID;
- không còn provider error trong lần sync;
- mọi held symbol có fresh price cùng latest trading date.

Estimated/stale snapshots vẫn hữu ích để chẩn đoán nhưng bị loại khỏi official performance evidence.

---

# PHẦN K — RESEARCH BOUNDARY

## 39. Research Lab

`/research` chứa các tooling nghiên cứu cũ/systematic như:

- backtests;
- Dynamic Alpha experiments;
- optimizer experiments;
- validation/holdout reports.

Boundary mong muốn:

```text
Research
   ↓
evidence / proposal
   ↓
human decision
   ↓
real broker action
   ↓
explicit ledger event
   ↓
operational portfolio
```

Cố ý không có direct automatic Research → BUY/SELL path.

---

# PHẦN L — CHECKLIST NGÀY ĐẦU TIÊN

Trước khi coi setup QPort mới là sẵn sàng, xác nhận:

- [ ] Đã nhập toàn bộ opening holdings.
- [ ] Share counts khớp broker.
- [ ] Average costs khớp intended broker cost basis.
- [ ] Opening cash khớp portfolio scope đã chọn.
- [ ] Daily price sync chạy được.
- [ ] Giá hiển thị theo full VND/share.
- [ ] Cost value khớp `shares × average cost`.
- [ ] Market value khớp `shares × market price`.
- [ ] Unrealized P/L khớp broker trong sai số hợp lý do fee/cost-basis policy.
- [ ] Data status VALID để tạo official snapshot.
- [ ] Đã có database backup.
- [ ] Optional strategic reference weights cộng đủ 100% nếu cấu hình.
- [ ] Hiểu rằng HOLD/ADD/REVIEW và Research outputs không tự thực hiện giao dịch.

Khi checklist này pass, QPort đã sẵn sàng cho routine Buy & Hold monitoring hằng ngày.
