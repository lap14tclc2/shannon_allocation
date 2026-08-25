---
id: QFD-020
title: "Ba vai trò nguồn dữ liệu"
type: decision
status: verified
created: 2026-08-25
updated: 2026-08-25
sources:
  - ../sources/source-qport-financial-data-design.md
---

# QFD-020 — Ba vai trò nguồn dữ liệu

## Claim

Hệ thống phân vai nguồn thay vì xem mọi nguồn là tương đương:

| Vai trò | Nguồn MVP | Mục đích |
|---|---|---|
| Structured primary | Vnstock fundamental guest/public capability | Lấy dữ liệu có cấu trúc nhanh, giảm chi phí parser |
| Independent cross-check | CafeF HTML công khai | Đối chiếu và fallback theo từng kỳ/chỉ tiêu |
| Evidence | Công bố của HOSE/HNX/SSC hoặc IR doanh nghiệp | Bằng chứng ưu tiên cao nhất khi xử lý xung đột |

Nguồn evidence không nhất thiết phải được parse đầy đủ trong MVP; tối thiểu phải lưu URL, ngày công bố và checksum/tệp nếu được phép.

---

## Relationships

- supports: [QFD-100](./20260825-qfd-100-he-a-api-ingestion.md)
- supports: [QFD-110](./20260825-qfd-110-he-b-html-ingestion.md)
- supports: [QFD-120](./20260825-qfd-120-nguon-evidence-chinh-thuc.md)
- supports: [QFD-300](./20260825-qfd-300-reconciliation-engine-xac-dinh.md)
