Được. Với constraint mới **free + public + không auth + không dùng CafeF/Vietstock + tránh nguồn có anti-crawl mạnh**, tôi sẽ bỏ luôn TCBS OpenAPI/MCP khỏi backend vì hiện API chính thức của TCBS yêu cầu API key/JWT hoặc OAuth. ([TCBS Developer Portal][1])

Điểm quan trọng là: **không có một website aggregate miễn phí/no-auth nào tôi tin đủ để thay CafeF/Vietstock cho toàn bộ BCTC**. Kiến trúc bền hơn là chuyển QPort sang **official-document-first ingestion**: lấy PDF/công bố chính thức → parse → normalize → DB.

| Nhu cầu                       | Nguồn thay thế                                   |  Auth | Đề xuất               |
| ----------------------------- | ------------------------------------------------ | ----: | --------------------- |
| BCTC năm/quý                  | **HNX disclosure**                               | Không | Primary               |
| BCTC HOSE                     | **Issuer IR + disclosure chính thức của Sở/SSC** | Không | Primary               |
| BCTC công ty đại chúng        | **SSC disclosure system + company website**      | Không | Primary               |
| Annual Report                 | **Website IR doanh nghiệp**                      | Không | Primary               |
| Corporate actions             | **VSDC**                                         | Không | **Canonical**         |
| Shares outstanding / tăng vốn | **VSDC + Annual Report/BCTC**                    | Không | Canonical/cross-check |
| AGM / nghị quyết              | **Company IR + exchange disclosure**             | Không | Primary               |
| KCN                           | **Company IR + UBND/BQL KCN**                    | Không | Primary               |
| Airport                       | **ACV + Cục Hàng không + Bộ Xây dựng**           | Không | Primary               |
| Shipping fleet                | **HAH IR + HAH fleet website**                   | Không | Primary               |
| Business/archetype            | **Annual Report / issuer website**               | Không | Primary               |
| Historical financials 7–10Y   | **Archive BCTC/Annual Report official**          | Không | Parse documents       |

HNX là nguồn đặc biệt phù hợp vì các disclosure page thực tế chứa **PDF BCTC đính kèm trực tiếp**, bao gồm cả bản hợp nhất, kiểm toán, giải trình và đôi khi cả bản tiếng Anh. ([HNX][2])

Ngoài ra quy định công bố thông tin yêu cầu công ty đại chúng công bố BCTC năm kiểm toán trên website doanh nghiệp và hệ thống công bố thông tin của UBCKNN. Vì vậy **Company IR + SSC/exchange disclosure** là nền tảng chính thống hơn việc phụ thuộc aggregator. ([SSO Vietnam][3])

### Corporate actions: dùng VSDC làm nguồn số 1

VSDC public rất phù hợp cho QPort. Các thông báo chứa rõ:

```text
ticker
event type
record date
payment date
cash dividend
stock dividend
bonus shares
rights issue
ratio
```

Ví dụ VSDC public trực tiếp việc BAF nhận cổ tức bằng cổ phiếu và phát hành tăng vốn. ([VSDC][4])

VSDC còn có history thay đổi số lượng chứng khoán, rất hữu ích để reconcile:

```text
historical shares
        ↓
VSDC corporate actions
        ↓
NON_ECONOMIC
│ stock dividend
│ bonus shares
│ split
│
└─ ECONOMIC_EVENT_CANDIDATE
  rights
  ESOP
  placement
  convertible
```

([VSDC][5])

Như vậy có thể xử lý trực tiếp rất nhiều `UNEXPLAINED_SHARE_CHANGE` trong screener hiện tại.

### HAH: không cần nguồn auth

Giữ:

```text
haiants.vn
fleet.haiants.vn
```

Website Hải An public archive Annual Report 2022–2025. ([Hai Ants][6])

Fleet site cũng public. ([Haiants Fleet][7])

QPort có thể lấy:

```text
vessel_name
TEU
year_built
ownership
acquisition
book value
depreciation
remaining useful life
```

Tôi sẽ **không dùng Equasis nữa** vì user phải đăng ký.

Và vì cũng không dùng VesselsValue/Clarksons, `FLEET_NAV` nên có hai level:

```text
FLEET_NAV_BOOK_PROXY
confidence = MEDIUM/LOW

FLEET_NAV_MARKET
= unsupported
```

Không tạo market fleet valuation giả.

### ACV: nguồn official rất tốt

Cho ACV, dùng:

```text
acv.vn
caa.gov.vn
moc.gov.vn / Bộ Xây dựng
government legal documents
```

Cục Hàng không public cả cơ chế quản lý giá và các loại dịch vụ như landing, passenger service, parking, counters, baggage belts, ground handling, fuel infrastructure và concession fees. ([Civil Aviation Authority of Vietnam][8])

Thông tư 23/2026/TT-BXD cũng public và có hiệu lực từ 01/07/2026. ([Civil Aviation Authority of Vietnam][9])

Đây là data tốt hơn rất nhiều so với lấy số từ một trang tổng hợp.

### IDC / KCN

Tôi sẽ dùng:

```text
IDICO IR
Annual Report
AGM documents
project pages
+
UBND tỉnh
Ban Quản lý KCN/KKT
quyết định đầu tư
quyết định mở rộng
```

Không cần CBRE/Savills nếu muốn constraint cực sạch.

Nếu actual lease price không public:

```text
lease_price = null
```

chứ không lấy benchmark bên thứ ba rồi giả làm actual price.

Model:

```text
LEASE_CASHFLOW_DCF
→ MODEL_INCOMPLETE
```

cho tới khi đủ evidence.

Điều này phù hợp với chính screener hiện tại, vì IDC đang thiếu diện tích thương phẩm, giá thuê, occupancy và thời hạn dự án. 

### HPG / DGC / BMP và full-cycle

Đây là nhóm **không cần nguồn aggregate**.

Screener hiện block HPG vì thiếu 7–10 năm normalization; DGC/BMP tương tự. 

Thay vì:

```text
CafeF API
Vietstock HTML
```

hãy làm:

```text
Issuer IR / HNX / HOSE / SSC
           ↓
     PDF downloader
           ↓
  financial document parser
           ↓
 canonical financial facts
           ↓
2016 2017 ... 2025
           ↓
full-cycle normalization
```

Đây là kiến trúc tôi khuyên mạnh nhất.

## Source registry mới cho QPort

Tôi sẽ chốt như sau:

```text
OFFICIAL_FINANCIAL
├── HNX
├── HOSE / issuer disclosure
├── SSC
└── Company IR

CORPORATE_ACTION
└── VSDC

SECTOR_OFFICIAL
├── CAAV / Cục Hàng không
├── Bộ Xây dựng
├── UBND tỉnh
├── Ban Quản lý KCN/KKT
└── ministry / regulator specific

COMPANY_SPECIALIZED
├── HAH Fleet
├── ACV project disclosures
├── IDICO project disclosures
└── company-specific IR datasets
```

Và bỏ hoàn toàn khỏi ingestion pipeline:

```text
❌ CafeF
❌ Vietstock
❌ TCBS API/MCP
❌ FireAnt
❌ Vietcap IQ
❌ Equasis
❌ VesselsValue
❌ Clarksons
❌ mọi nguồn login/token
❌ mọi paid vendor
```

Tôi cũng sẽ **không tìm thêm một “CafeF clone”** để thay thế, vì rất dễ quay lại cùng vấn đề anti-bot/API private. Với QPort, hướng đúng hơn là **official document ingestion + parser + local canonical database**. Khi đã crawl một BCTC PDF chính thức thành công, QPort lưu fact vào DB và valuation/screener sau đó chỉ đọc DB, không phụ thuộc website ở runtime.

[1]: https://developers.tcbs.com.vn/ "https://developers.tcbs.com.vn/"
[2]: https://www.hnx.vn/vi-vn/m-niem-yet/tin-tuc/Bao%20cao%20tai%20chinh%20nam%202025-602547-1.html "https://www.hnx.vn/vi-vn/m-niem-yet/tin-tuc/Bao%20cao%20tai%20chinh%20nam%202025-602547-1.html"
[3]: https://ssc.gov.vn/webcenter/contentattachfile/idcplg?IdcService=GET_FILE&IsAttachment=1&Rendition=Th%C3%B4ng+t%C6%B0+96%2F2020%2FTT-BTC&dDocName=APPSSCGOVVN162136358&dID=101102&filename=Thong+tu+so+96+cua+Bo+truong+Bo+Tai+chinh+huong+dan+CBTT+tren+thi+truong+chung+khoan_ngay+16-11-2020_Final.pdf "https://ssc.gov.vn/webcenter/contentattachfile/idcplg?IdcService=GET_FILE&IsAttachment=1&Rendition=Th%C3%B4ng+t%C6%B0+96%2F2020%2FTT-BTC&dDocName=APPSSCGOVVN162136358&dID=101102&filename=Thong+tu+so+96+cua+Bo+truong+Bo+Tai+chinh+huong+dan+CBTT+tren+thi+truong+chung+khoan_ngay+16-11-2020_Final.pdf"
[4]: https://vsdc.vn/vi/ad/196661 "https://vsdc.vn/vi/ad/196661"
[5]: https://vsdc.vn/vi/s-detail/707 "https://vsdc.vn/vi/s-detail/707"
[6]: https://haiants.vn/bao-cao-thuong-nien-q11.html "https://haiants.vn/bao-cao-thuong-nien-q11.html"
[7]: https://fleet.haiants.vn/ "https://fleet.haiants.vn/"
[8]: https://caa.gov.vn/hoat-dong-nganh/trach-nhiem-tham-dinh-phuong-an-gia-20260527134503981.htm "https://caa.gov.vn/hoat-dong-nganh/trach-nhiem-tham-dinh-phuong-an-gia-20260527134503981.htm"
[9]: https://caa.gov.vn/van-ban/23-2026-tt-bxd-31832.htm "https://caa.gov.vn/van-ban/23-2026-tt-bxd-31832.htm"
