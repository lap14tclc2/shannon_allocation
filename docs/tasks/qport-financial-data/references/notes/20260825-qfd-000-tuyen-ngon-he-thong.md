---
id: QFD-000
title: "Tuyên ngôn hệ thống"
type: principle
status: verified
created: 2026-08-25
updated: 2026-08-25
sources:
  - ../sources/source-qport-financial-data-design.md
---

# QFD-000 — Tuyên ngôn hệ thống

## Claim

QPort cần một lớp dữ liệu nội bộ có provenance, không phụ thuộc duy nhất vào một website. Hệ thống phải trả lời được bốn câu hỏi cho mọi con số:

1. Con số này mô tả chỉ tiêu gì?
2. Thuộc kỳ, phạm vi hợp nhất, đơn vị và phiên bản báo cáo nào?
3. Được lấy từ nguồn nào, lúc nào và bằng phương thức nào?
4. Đã được đối chiếu với nguồn nào, có mâu thuẫn hay không?

Thành công không phải là “crawl được nhiều”, mà là tạo được dữ liệu **có thể truy vết, tái lập và không gây sai lệch backtest**.

## Relationships

- supports: [QFD-010](./20260825-qfd-010-ranh-gioi-san-pham.md)
- supports: [QFD-200](./20260825-qfd-200-ba-lop-du-lieu.md)
- supports: [QFD-300](./20260825-qfd-300-reconciliation-engine-xac-dinh.md)
- supports: [QFD-500](./20260825-qfd-500-qport-data-api.md)
