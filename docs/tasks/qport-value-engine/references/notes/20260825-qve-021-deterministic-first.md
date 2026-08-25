---
id: QVE-021
title: "Deterministic first"
type: rule
status: draft
created: 2026-08-25
updated: 2026-08-25
sources:
  - ../sources/source-qport-value-engine-specification.md
---

# QVE-021 — Deterministic first

## Claim

Cùng dữ liệu, cùng policy version và cùng assumptions phải luôn tạo cùng một kết quả.

AI không được tham gia vào:

- phép tính tài chính;
- chuẩn hóa lợi nhuận;
- lựa chọn discount rate;
- tạo dữ liệu còn thiếu;
- thay đổi giả định;
- xác nhận giá trị nội tại;
- tạo giao dịch.

## Relationships

- derived-from: [SRC-QVE-001](../sources/source-qport-value-engine-specification.md)
- supports: [QVE-040](./20260825-qve-040-kien-truc-tong-the.md)
- supports: [QVE-170](./20260825-qve-170-valuation-report-contract.md)
- supports: [QVE-260](./20260825-qve-260-quyet-dinh-kien-truc-cuoi-cung.md)
