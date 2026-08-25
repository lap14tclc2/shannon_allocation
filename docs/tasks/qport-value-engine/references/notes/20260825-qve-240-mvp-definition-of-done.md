---
id: QVE-240
title: "MVP Definition of Done"
type: checklist
status: draft
created: 2026-08-25
updated: 2026-08-25
sources:
  - ../sources/source-qport-value-engine-specification.md
---

# QVE-240 — MVP Definition of Done

## Claim

MVP hoàn thành khi:

- chạy được mà không có AI;
- hỗ trợ ít nhất một doanh nghiệp phi tài chính;
- dữ liệu thiếu không bị suy đoán;
- toàn bộ input có nguồn và kỳ báo cáo;
- Owner Earnings có bridge rõ ràng;
- Bear/Base/Bull có assumptions riêng;
- có DCF, EPV và reverse DCF;
- có sensitivity và confidence;
- kết quả reproducible;
- mọi valuation run có version;
- unit, golden và invariant tests pass;
- valuation không thay đổi portfolio ledger;
- UI giải thích được công thức và dữ liệu đầu vào.

---

## Relationships

- derived-from: [SRC-QVE-001](../sources/source-qport-value-engine-specification.md)
- requires: [QVE-221](./20260825-qve-221-unit-tests.md)
- requires: [QVE-222](./20260825-qve-222-golden-tests.md)
- requires: [QVE-223](./20260825-qve-223-invariant-tests.md)
