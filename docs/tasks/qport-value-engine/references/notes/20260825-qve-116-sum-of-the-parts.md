---
id: QVE-116
title: "Sum of the Parts"
type: contract
status: draft
created: 2026-08-25
updated: 2026-08-25
sources:
  - ../sources/source-qport-value-engine-specification.md
---

# QVE-116 — Sum of the Parts

## Claim

```text
SOTP value =
Σ segment values
+ listed investments
+ unlisted investments
+ excess cash
− debt
− holding costs
− applicable holding discount
```

Mỗi segment phải lưu model và assumptions riêng.

## Relationships

- derived-from: [SRC-QVE-001](../sources/source-qport-value-engine-specification.md)
- requires: [QVE-070](./20260825-qve-070-sector-routing.md)
