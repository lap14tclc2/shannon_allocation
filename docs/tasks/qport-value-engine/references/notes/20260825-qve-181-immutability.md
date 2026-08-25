---
id: QVE-181
title: "Immutability"
type: decision
status: draft
created: 2026-08-25
updated: 2026-08-25
sources:
  - ../sources/source-qport-value-engine-specification.md
---

# QVE-181 — Immutability

## Claim

- Raw source facts không được sửa trực tiếp.
- Restatement tạo version mới.
- Manual override tạo adjustment record.
- Valuation run đã hoàn tất là immutable.
- Re-run tạo report mới với version mới.
- Phải lưu code version hoặc calculation-engine version.

---

## Relationships

- derived-from: [SRC-QVE-001](../sources/source-qport-value-engine-specification.md)
- supports: [QVE-170](./20260825-qve-170-valuation-report-contract.md)
