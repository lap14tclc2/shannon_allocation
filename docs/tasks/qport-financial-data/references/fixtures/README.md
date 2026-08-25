# Raw Crawled Financial Data

Dữ liệu crawl thực tế từ hai nguồn độc lập phục vụ kiểm chứng và đối soát cho QPort Financial Data System.

- **Thời điểm lấy:** `2026-08-25T13:57:29Z`
- **Mã cổ phiếu:** `FPT`

## Tệp dữ liệu

1. **Kênh A (Vnstock API / VCI)**:
   - File: [`vnstock_FPT_financials.json`](./vnstock_FPT_financials.json)
   - Nội dung: Đầy đủ 3 báo cáo tài chính (Income Statement, Balance Sheet, Cash Flow) 4 kỳ gần nhất dạng JSON có cấu trúc.

2. **Kênh B (CafeF Ingestion)**:
   - File JSON: [`cafef_FPT_financials.json`](./cafef_FPT_financials.json)
     - Nội dung: Dữ liệu báo cáo kết quả kinh doanh FPT dạng JSON trích xuất từ bảng CafeF với 25 chỉ tiêu tài chính qua các quý.
   - File HTML thô: [`cafef_FPT_income_statement.html`](./cafef_FPT_income_statement.html)
     - Nội dung: Raw HTML snapshot nguyên bản dùng để đối soát tính toàn vẹn và provenance.
