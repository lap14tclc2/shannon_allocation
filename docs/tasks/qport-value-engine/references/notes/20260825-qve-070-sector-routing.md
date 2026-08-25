---
id: QVE-070
title: "Sector routing"
type: decision
status: draft
created: 2026-08-25
updated: 2026-08-25
sources:
  - ../sources/source-qport-value-engine-specification.md
---

# QVE-070 — Sector routing

## Claim

| Nhóm doanh nghiệp | Primary model | Cross-check model |
|---|---|---|
| Công nghệ và dịch vụ | Owner Earnings DCF | EPV, historical multiples |
| Sản xuất và hóa chất | Mid-cycle Owner Earnings DCF | EPV, EV/EBIT |
| Ngân hàng | Residual Income | Justified P/B |
| Bảo hiểm | Residual Income hoặc SOTP | P/B |
| Điện, nước, hạ tầng | FCFE hoặc DDM | SOTP |
| Holding | Sum of the Parts | Look-through earnings |
| Bất động sản | RNAV | Normalized earnings |
| Bán lẻ | Owner Earnings DCF | EPV, EV/EBIT |

Không được tự động fallback từ một model không phù hợp sang generic DCF mà không báo lỗi.

---

## Relationships

- derived-from: [SRC-QVE-001](../sources/source-qport-value-engine-specification.md)
- requires: [QVE-063](./20260825-qve-063-dieu-kien-chan-valuation.md)
