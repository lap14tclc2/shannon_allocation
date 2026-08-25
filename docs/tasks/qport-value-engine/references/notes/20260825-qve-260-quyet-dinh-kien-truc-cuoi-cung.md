---
id: QVE-260
title: "Quyết định kiến trúc cuối cùng"
type: decision
status: draft
created: 2026-08-25
updated: 2026-08-25
sources:
  - ../sources/source-qport-value-engine-specification.md
---

# QVE-260 — Quyết định kiến trúc cuối cùng

## Claim

QPort Value Engine phải tuân theo chuỗi:

```text
Data Quality
→ Business Quality
→ Normalized Per-Share Economics
→ Owner Earnings
→ Sector-Specific Valuation
→ Scenario Range
→ Reverse Expectations
→ Margin of Safety
→ Human Review
```

Hệ thống định giá là module độc lập với portfolio ledger. Thay đổi giá thị trường, fair value, margin of safety, quality warning hoặc investment thesis không được tự động thay đổi shares, cash hay transactions.

AI là lớp tùy chọn ở phía ngoài, không phải dependency của valuation core.

---

## Relationships

- derived-from: [SRC-QVE-001](../sources/source-qport-value-engine-specification.md)
- requires: [QVE-021](./20260825-qve-021-deterministic-first.md)
- requires: [QVE-022](./20260825-qve-022-information-only.md)
- requires: [QVE-025](./20260825-qve-025-sector-specific-models.md)
- requires: [QVE-063](./20260825-qve-063-dieu-kien-chan-valuation.md)
- requires: [QVE-070](./20260825-qve-070-sector-routing.md)
- requires: [QVE-170](./20260825-qve-170-valuation-report-contract.md)
