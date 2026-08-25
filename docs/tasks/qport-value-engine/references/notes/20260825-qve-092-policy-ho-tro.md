---
id: QVE-092
title: "Policy hỗ trợ"
type: decision
status: draft
created: 2026-08-25
updated: 2026-08-25
sources:
  - ../sources/source-qport-value-engine-specification.md
---

# QVE-092 — Policy hỗ trợ

## Claim

```yaml
normalization:
  method: weighted_average
  years: 5
  weights: [0.10, 0.15, 0.20, 0.25, 0.30]
  exclude_one_off_items: true
  cycle_adjustment: sector_specific
```

Các method tối thiểu:

- median 5Y;
- simple average 5Y;
- weighted average 5Y;
- mid-cycle margin;
- user-specified normalized value.

Mọi manual override phải có reason và audit trail.

---

## Relationships

- derived-from: [SRC-QVE-001](../sources/source-qport-value-engine-specification.md)
- extends: [QVE-091](./20260825-qve-091-muc-dich.md)
