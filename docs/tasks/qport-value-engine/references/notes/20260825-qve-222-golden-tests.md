---
id: QVE-222
title: "Golden tests"
type: contract
status: draft
created: 2026-08-25
updated: 2026-08-25
sources:
  - ../sources/source-qport-value-engine-specification.md
---

# QVE-222 — Golden tests

## Claim

Tạo các fixture cố định cho:

- doanh nghiệp phi tài chính ổn định;
- doanh nghiệp chu kỳ;
- ngân hàng;
- doanh nghiệp có pha loãng lớn;
- dữ liệu restated;
- dữ liệu thiếu;
- doanh nghiệp có net cash;
- doanh nghiệp có debt cao.

Mỗi fixture phải có expected intermediate calculations, không chỉ expected final fair value.

## Relationships

- derived-from: [SRC-QVE-001](../sources/source-qport-value-engine-specification.md)
- extends: [QVE-221](./20260825-qve-221-unit-tests.md)
