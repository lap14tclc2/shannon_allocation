---
id: QVE-040
title: "Kiến trúc tổng thể"
type: decision
status: draft
created: 2026-08-25
updated: 2026-08-25
sources:
  - ../sources/source-qport-value-engine-specification.md
---

# QVE-040 — Kiến trúc tổng thể

## Claim

```text
Financial Data Sources
        ↓
Raw Financial Statements
        ↓
Validation & Normalization
        ↓
Canonical Financial Snapshots
        ↓
Sector Classification
        ↓
Business Quality Diagnostics
        ↓
Normalized Earnings / Owner Earnings
        ↓
Sector-Specific Valuation Models
        ↓
Bear / Base / Bull Scenarios
        ↓
Sensitivity & Reverse Valuation
        ↓
Margin of Safety & Confidence
        ↓
Immutable Valuation Report
        ↓
Optional AI Explanation
```

## Relationships

- derived-from: [SRC-QVE-001](../sources/source-qport-value-engine-specification.md)
- requires: [QVE-051](./20260825-qve-051-metadata-bat-buoc.md)
- requires: [QVE-062](./20260825-qve-062-kiem-tra-bat-buoc.md)
- requires: [QVE-070](./20260825-qve-070-sector-routing.md)
