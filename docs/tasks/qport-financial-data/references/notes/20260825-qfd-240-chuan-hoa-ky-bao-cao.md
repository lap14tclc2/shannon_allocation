---
id: QFD-240
title: "Chuẩn hóa kỳ báo cáo"
type: rule
status: verified
created: 2026-08-25
updated: 2026-08-25
sources:
  - ../sources/source-qport-financial-data-design.md
---

# QFD-240 — Chuẩn hóa kỳ báo cáo

## Claim

- Balance sheet là số tại thời điểm: `period_type=INSTANT`.
- Income statement và cash flow có thể là quý riêng (`QUARTER`), lũy kế (`YTD`) hoặc năm (`FY`).
- Không so sánh `Q2 standalone` với `6M YTD`.
- Chỉ suy ra quý riêng bằng phép trừ YTD khi cùng phạm vi hợp nhất, cùng đơn vị, cùng revision family và không có dấu hiệu restatement.
- Fact suy ra phải có `derivation_method=YTD_DIFFERENCE` và liên kết tới hai input facts.

## Relationships

- supports: [QFD-210](./20260825-qfd-210-identity-key-cua-mot-financial-fact.md)
- supports: [QFD-310](./20260825-qfd-310-so-khop-va-tolerance.md)
- supports: [QFD-520](./20260825-qfd-520-point-in-time-va-chong-look-ahead-bias.md)
