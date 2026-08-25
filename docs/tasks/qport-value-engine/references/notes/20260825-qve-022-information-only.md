---
id: QVE-022
title: "Information only"
type: rule
status: draft
created: 2026-08-25
updated: 2026-08-25
sources:
  - ../sources/source-qport-value-engine-specification.md
---

# QVE-022 — Information only

## Claim

QPort Value Engine cung cấp dữ liệu, chẩn đoán và valuation report. Nó không được:

- tự động BUY/SELL;
- tự động thay thế cổ phiếu;
- tự động phân bổ danh mục;
- tự động tái đầu tư cổ tức;
- thay đổi shares hoặc cash;
- tạo ledger event.

Chỉ explicit ledger event do người dùng xác nhận mới được thay đổi portfolio state.

## Relationships

- derived-from: [SRC-QVE-001](../sources/source-qport-value-engine-specification.md)
- supports: [QVE-203](./20260825-qve-203-khong-su-dung-mau-nhu-lenh-giao-dich.md)
- supports: [QVE-260](./20260825-qve-260-quyet-dinh-kien-truc-cuoi-cung.md)
