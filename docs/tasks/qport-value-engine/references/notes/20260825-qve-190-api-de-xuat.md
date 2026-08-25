---
id: QVE-190
title: "API đề xuất"
type: contract
status: draft
created: 2026-08-25
updated: 2026-08-25
sources:
  - ../sources/source-qport-value-engine-specification.md
---

# QVE-190 — API đề xuất

## Claim

```text
GET  /api/fundamentals/{ticker}
GET  /api/fundamentals/{ticker}/history
GET  /api/fundamentals/{ticker}/quality
GET  /api/fundamentals/{ticker}/dilution

GET  /api/valuation/policies
POST /api/valuation/assumption-sets
POST /api/valuation/{ticker}/run
GET  /api/valuation/{ticker}/latest
GET  /api/valuation/{ticker}/history
GET  /api/valuation/reports/{report_id}
GET  /api/valuation/reports/{report_id}/sensitivity
```

`POST /run` chỉ tạo valuation report, không tạo portfolio transaction.

---

## Relationships

- derived-from: [SRC-QVE-001](../sources/source-qport-value-engine-specification.md)
- applies-to: [QVE-170](./20260825-qve-170-valuation-report-contract.md)
