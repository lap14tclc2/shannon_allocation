---
id: QFD-620
title: "Chiến lược test"
type: contract
status: draft
created: 2026-08-25
updated: 2026-08-25
sources:
  - ../sources/source-qport-financial-data-design.md
---

# QFD-620 — Chiến lược test

## Claim

### Test pyramid

1. Unit: số/đơn vị/ngày, label mapping, quarter-vs-YTD, null-vs-zero.
2. Golden fixture: payload API và HTML snapshot cố định.
3. Contract: schema/capability probe trên live provider, chạy nhỏ và rate-limited.
4. Reconciliation: exact match, rounding match, scope mismatch, revision và conflict.
5. Accounting invariants: tài sản = nguồn vốn trong tolerance; subtotal consistency khi áp dụng.
6. Point-in-time: không nhìn thấy report trước publish/observed time.
7. End-to-end: ingest → canonical → metric → API.

### Symbol matrix tối thiểu

| Nhóm | Symbol mẫu | Mục tiêu |
|---|---|---|
| Doanh nghiệp thường | FPT hoặc DGC | baseline statements |
| Ngân hàng | ACB | taxonomy bank |
| Chứng khoán | SSI hoặc FTS | taxonomy securities |
| Bảo hiểm | BVH | taxonomy insurance |
| Có lịch sử điều chỉnh/khác biệt | chọn từ dữ liệu thực | revision và conflict |

Live tests không chạy trên mỗi unit-test commit; chạy scheduled/canary vì phụ thuộc mạng và quota.

## Relationships

- supports: [QFD-110](./20260825-qfd-110-he-b-html-ingestion.md)
- supports: [QFD-240](./20260825-qfd-240-chuan-hoa-ky-bao-cao.md)
- supports: [QFD-260](./20260825-qfd-260-taxonomy-theo-loai-hinh-doanh-nghiep.md)
- supports: [QFD-610](./20260825-qfd-610-roadmap-trien-khai.md)
- supports: [QFD-630](./20260825-qfd-630-definition-of-done-cho-mvp.md)
