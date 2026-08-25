---
id: QVE-130
title: "Margin of Safety"
type: rule
status: draft
created: 2026-08-25
updated: 2026-08-25
sources:
  - ../sources/source-qport-value-engine-specification.md
---

# QVE-130 — Margin of Safety

## Claim

```text
Margin of Safety =
1 − Market Price / Intrinsic Value
```

Hệ thống chỉ trả valuation state:

```text
MATERIAL_DISCOUNT
MODERATE_DISCOUNT
NEAR_FAIR_VALUE
ABOVE_FAIR_VALUE
VALUATION_UNRELIABLE
PRICE_UNAVAILABLE
```

Các threshold phải do versioned policy định nghĩa. Không map trực tiếp state sang BUY/SELL.

---

## Relationships

- derived-from: [SRC-QVE-001](../sources/source-qport-value-engine-specification.md)
- requires: [QVE-122](./20260825-qve-122-output.md)
- requires: [QVE-056](./20260825-qve-056-market-data.md)
