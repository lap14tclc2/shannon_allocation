---
id: QFD-010
title: "Ranh giới sản phẩm"
type: decision
status: verified
created: 2026-08-25
updated: 2026-08-25
sources:
  - ../sources/source-qport-financial-data-design.md
---

# QFD-010 — Ranh giới sản phẩm

## Claim

### Trong phạm vi MVP

- Hồ sơ doanh nghiệp cơ bản: mã, tên, sàn, ngành, loại hình tổ chức, website, mã số thuế nếu có.
- Báo cáo kết quả kinh doanh, bảng cân đối kế toán và lưu chuyển tiền tệ.
- Kỳ năm và quý; hợp nhất và riêng lẻ nếu nguồn có cung cấp.
- Dữ liệu nguồn thô, dữ liệu chuẩn hóa, dữ liệu canonical và bằng chứng nguồn.
- Đối chiếu API với HTML; gắn trạng thái chất lượng thay vì âm thầm chọn giá trị.
- API nội bộ phục vụ valuation, screening và backtest.

### Ngoài phạm vi MVP

- Giao dịch thời gian thực, order book và execution.
- Tin tức, sentiment và dữ liệu mạng xã hội.
- OCR toàn bộ PDF scan chất lượng thấp.
- Mua hoặc vượt qua paywall, CAPTCHA, đăng nhập hay cơ chế chống bot.
- Dùng AI để tự quyết định giá trị kế toán đúng khi hai nguồn xung đột.

## Relationships

- supports: [QFD-000](./20260825-qfd-000-tuyen-ngon-he-thong.md)
- supports: [QFD-020](./20260825-qfd-020-ba-vai-tro-nguon-du-lieu.md)
- supports: [QFD-500](./20260825-qfd-500-qport-data-api.md)
