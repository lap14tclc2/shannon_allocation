---
id: QVE-113
title: "Dividend Discount Model"
type: contract
status: draft
created: 2026-08-25
updated: 2026-08-25
sources:
  - ../sources/source-qport-value-engine-specification.md
---

# QVE-113 — Dividend Discount Model

## Claim

```text
Value = Dividend(next_year) / (required_return − dividend_growth)
```

Chỉ áp dụng khi:

- cổ tức phản ánh khả năng phân phối tiền;
- payout policy ổn định;
- tăng trưởng cổ tức có thể ước tính;
- `dividend_growth < required_return`.

## Relationships

- derived-from: [SRC-QVE-001](../sources/source-qport-value-engine-specification.md)
- requires: [QVE-070](./20260825-qve-070-sector-routing.md)
