---
id: QVE-063
title: "Điều kiện chặn valuation"
type: rule
status: draft
created: 2026-08-25
updated: 2026-08-25
sources:
  - ../sources/source-qport-value-engine-specification.md
---

# QVE-063 — Điều kiện chặn valuation

## Claim

Valuation phải bị chặn khi:

- thiếu share count đáng tin cậy;
- đơn vị tiền tệ không xác định;
- dữ liệu lợi nhuận và dòng tiền không khớp kỳ;
- sector chưa được hỗ trợ;
- không đủ dữ liệu cho model được chọn;
- normalized earnings không thể xác định hợp lý.

---

## Relationships

- derived-from: [SRC-QVE-001](../sources/source-qport-value-engine-specification.md)
- requires: [QVE-062](./20260825-qve-062-kiem-tra-bat-buoc.md)
