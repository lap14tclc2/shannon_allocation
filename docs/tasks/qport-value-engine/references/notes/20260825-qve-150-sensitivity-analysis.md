---
id: QVE-150
title: "Sensitivity Analysis"
type: contract
status: draft
created: 2026-08-25
updated: 2026-08-25
sources:
  - ../sources/source-qport-value-engine-specification.md
---

# QVE-150 — Sensitivity Analysis

## Claim

Tối thiểu phải có ma trận:

```text
Discount rate × Terminal growth
Discount rate × Near-term growth
Operating margin × Revenue growth
Maintenance CAPEX × Growth
```

Các cảnh báo:

```text
TERMINAL_VALUE_DOMINANT
HIGH_DISCOUNT_RATE_SENSITIVITY
HIGH_GROWTH_SENSITIVITY
MAINTENANCE_CAPEX_UNCERTAIN
NORMALIZED_EARNINGS_UNSTABLE
```

---

## Relationships

- derived-from: [SRC-QVE-001](../sources/source-qport-value-engine-specification.md)
- applies-to: [QVE-111](./20260825-qve-111-owner-earnings-dcf.md)
