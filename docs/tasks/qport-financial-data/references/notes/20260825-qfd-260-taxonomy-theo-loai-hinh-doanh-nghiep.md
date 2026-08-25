---
id: QFD-260
title: "Taxonomy theo loại hình doanh nghiệp"
type: decision
status: verified
created: 2026-08-25
updated: 2026-08-25
sources:
  - ../sources/source-qport-financial-data-design.md
---

# QFD-260 — Taxonomy theo loại hình doanh nghiệp

## Claim

Taxonomy có core chung và extension theo entity type:

| Entity type | Ví dụ | Extension cần có |
|---|---|---|
| NORMAL_ENTERPRISE | FPT, DGC | doanh thu, COGS, tồn kho, capex, nợ vay |
| BANK | ACB | thu nhập lãi, NIM inputs, dư nợ, tiền gửi, nợ xấu, dự phòng |
| SECURITIES | SSI, FTS | môi giới, tự doanh, cho vay margin, tài sản FVTPL |
| INSURANCE | BVH | phí bảo hiểm, dự phòng nghiệp vụ, bồi thường |

Không ép bank/insurance vào công thức industrial. Metrics chỉ chạy khi entity type và input contract phù hợp.

---

## Relationships

- supports: [QFD-210](./20260825-qfd-210-identity-key-cua-mot-financial-fact.md)
- supports: [QFD-300](./20260825-qfd-300-reconciliation-engine-xac-dinh.md)
- supports: [QFD-610](./20260825-qfd-610-roadmap-trien-khai.md)
