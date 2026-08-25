---
id: QFD-300
title: "Reconciliation engine xác định"
type: decision
status: verified
created: 2026-08-25
updated: 2026-08-25
sources:
  - ../sources/source-qport-financial-data-design.md
---

# QFD-300 — Reconciliation engine xác định

## Claim

Reconcile theo từng identity key. Engine MUST deterministic: cùng input và rule version phải cho cùng output.

```text
1. Thu thập candidate facts cùng identity key.
2. Loại candidate lỗi schema, kỳ, unit hoặc scope.
3. Gom candidate bằng exact value hoặc tolerance được định nghĩa.
4. Xếp hạng theo evidence tier, revision và freshness.
5. Chọn candidate hoặc gắn CONFLICT.
6. Lưu decision, rule_version và toàn bộ candidate IDs.
```

### Luật cấm

**Không bao giờ lấy trung bình hai con số kế toán để “hợp nhất”.** Trung bình phá provenance và tạo ra số không thuộc bất kỳ báo cáo nào.

## Relationships

- supports: [QFD-020](./20260825-qfd-020-ba-vai-tro-nguon-du-lieu.md)
- supports: [QFD-210](./20260825-qfd-210-identity-key-cua-mot-financial-fact.md)
- supports: [QFD-310](./20260825-qfd-310-so-khop-va-tolerance.md)
- supports: [QFD-320](./20260825-qfd-320-chon-nguon-thang-va-xu-ly-revision.md)
- supports: [QFD-340](./20260825-qfd-340-hang-doi-review.md)
