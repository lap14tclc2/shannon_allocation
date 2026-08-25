---
id: QFD-320
title: "Chọn nguồn thắng và xử lý revision"
type: rule
status: verified
created: 2026-08-25
updated: 2026-08-25
sources:
  - ../sources/source-qport-financial-data-design.md
---

# QFD-320 — Chọn nguồn thắng và xử lý revision

## Claim

Thứ tự chọn mặc định: official filing mới nhất → structured API → CafeF HTML → nguồn bổ sung. Tuy nhiên:

- Bản điều chỉnh mới hơn thắng bản cũ nếu cùng issuer/kỳ/scope.
- Không overwrite history; tạo canonical version mới với `valid_from`.
- Record cũ có `valid_to` và liên kết `superseded_by`.
- Backtest point-in-time chỉ được thấy version có `published_at/observed_at <= evaluation_time`.
- Nếu nguồn ưu tiên cao có lỗi validation nghiêm trọng, không tự động chọn; chuyển `CONFLICT` hoặc `QUARANTINED`.

## Relationships

- supports: [QFD-120](./20260825-qfd-120-nguon-evidence-chinh-thuc.md)
- supports: [QFD-230](./20260825-qfd-230-provenance-va-evidence-chain.md)
- supports: [QFD-300](./20260825-qfd-300-reconciliation-engine-xac-dinh.md)
- supports: [QFD-330](./20260825-qfd-330-trang-thai-chat-luong.md)
