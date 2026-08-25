---
id: QFD-330
title: "Trạng thái chất lượng"
type: contract
status: verified
created: 2026-08-25
updated: 2026-08-25
sources:
  - ../sources/source-qport-financial-data-design.md
---

# QFD-330 — Trạng thái chất lượng

## Claim

| Status | Ý nghĩa | Có phục vụ production? |
|---|---|---:|
| `OFFICIAL_VERIFIED` | Khớp filing chính thức hoặc được parse trực tiếp từ filing | Có |
| `CROSS_SOURCE_VERIFIED` | Ít nhất hai nguồn độc lập khớp trong tolerance | Có |
| `SINGLE_SOURCE` | Một nguồn hợp lệ, chưa đối chiếu | Có, kèm cảnh báo |
| `DERIVED` | Suy ra theo công thức có trace | Có, nếu consumer cho phép |
| `CONFLICT` | Nguồn hợp lệ nhưng bất đồng đáng kể | Không mặc định |
| `QUARANTINED` | Lỗi schema/validation/provenance | Không |
| `MISSING` | Không có dữ liệu | Không |

Quality score MAY được dùng để xếp hàng review, nhưng status và lý do phải là dữ liệu chính; không để một điểm số mơ hồ che mất conflict.

## Relationships

- supports: [QFD-230](./20260825-qfd-230-provenance-va-evidence-chain.md)
- supports: [QFD-300](./20260825-qfd-300-reconciliation-engine-xac-dinh.md)
- supports: [QFD-320](./20260825-qfd-320-chon-nguon-thang-va-xu-ly-revision.md)
- supports: [QFD-430](./20260825-qfd-430-quan-sat-va-slo.md)
