---
id: QVE-250
title: "Những điều không được triển khai"
type: rule
status: draft
created: 2026-08-25
updated: 2026-08-25
sources:
  - ../sources/source-qport-value-engine-specification.md
---

# QVE-250 — Những điều không được triển khai

## Claim

- Một `Buffett Score` duy nhất thay thế phân tích.
- Dùng P/E thấp làm bằng chứng cổ phiếu rẻ.
- Dùng ROE cao nhưng bỏ qua leverage.
- Dùng total profit mà bỏ qua dilution.
- Coi stock dividend là giá trị kinh tế miễn phí.
- Dùng cost basis của nhà đầu tư làm input định giá.
- Hard-code inflation hoặc discount rate vĩnh viễn.
- Dùng generic DCF cho ngân hàng.
- Tự điền dữ liệu thiếu bằng 0.
- Dùng dữ liệu ví dụ trong tài liệu như current facts.
- Chuyển valuation state thành giao dịch.
- Cho AI sửa dữ liệu hoặc phép tính.

---

## Relationships

- derived-from: [SRC-QVE-001](../sources/source-qport-value-engine-specification.md)
- supports: [QVE-021](./20260825-qve-021-deterministic-first.md)
- supports: [QVE-022](./20260825-qve-022-information-only.md)
- supports: [QVE-025](./20260825-qve-025-sector-specific-models.md)
