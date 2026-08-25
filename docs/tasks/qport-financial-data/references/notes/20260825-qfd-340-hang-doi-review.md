---
id: QFD-340
title: "Hàng đợi review"
type: runbook
status: draft
created: 2026-08-25
updated: 2026-08-25
sources:
  - ../sources/source-qport-financial-data-design.md
---

# QFD-340 — Hàng đợi review

## Claim

Một conflict item cần có symbol, identity key, candidate values, source links, diff, validation failures, first/last seen, severity và suggested action. Người review chỉ được:

- Chọn một candidate với lý do.
- Gắn mapping/scope/unit đúng và rerun reconcile.
- Đánh dấu upstream error.
- Chờ filing chính thức.

Manual override phải versioned, có author/reason/expiry; connector run mới không được âm thầm xóa override.

---

## Relationships

- supports: [QFD-300](./20260825-qfd-300-reconciliation-engine-xac-dinh.md)
- supports: [QFD-310](./20260825-qfd-310-so-khop-va-tolerance.md)
- supports: [QFD-330](./20260825-qfd-330-trang-thai-chat-luong.md)
- supports: [QFD-430](./20260825-qfd-430-quan-sat-va-slo.md)
