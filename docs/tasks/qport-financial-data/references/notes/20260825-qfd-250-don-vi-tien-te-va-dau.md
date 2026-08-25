---
id: QFD-250
title: "Đơn vị, tiền tệ và dấu"
type: rule
status: verified
created: 2026-08-25
updated: 2026-08-25
sources:
  - ../sources/source-qport-financial-data-design.md
---

# QFD-250 — Đơn vị, tiền tệ và dấu

## Claim

- Lưu giá trị normalized bằng VND đơn vị cơ sở; không làm tròn khi ingestion.
- Lưu cả `currency`, `scale_observed`, `sign_convention` và `value_raw`.
- Dấu ngoặc, dấu trừ, số không, ô trống và ký hiệu `-` phải được phân biệt.
- `null` nghĩa là không biết/không công bố; không tự đổi `null` thành `0`.
- Chuyển đổi ngoại tệ chỉ xảy ra ở lớp metric, không sửa fact gốc.

## Relationships

- supports: [QFD-210](./20260825-qfd-210-identity-key-cua-mot-financial-fact.md)
- supports: [QFD-220](./20260825-qfd-220-providerfact-contract.md)
- supports: [QFD-310](./20260825-qfd-310-so-khop-va-tolerance.md)
