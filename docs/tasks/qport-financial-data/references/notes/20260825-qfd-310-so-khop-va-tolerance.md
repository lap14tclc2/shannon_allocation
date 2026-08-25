---
id: QFD-310
title: "So khớp và tolerance"
type: rule
status: draft
created: 2026-08-25
updated: 2026-08-25
sources:
  - ../sources/source-qport-financial-data-design.md
---

# QFD-310 — So khớp và tolerance

## Claim

So khớp sau khi đã chuẩn hóa currency/scale/period/scope.

```text
absolute_diff = abs(a - b)
relative_diff = absolute_diff / max(abs(a), abs(b), 1)
match = absolute_diff <= ABS_TOLERANCE
        OR relative_diff <= REL_TOLERANCE
```

Giá trị ban đầu để thử nghiệm, không phải mặc định vĩnh viễn:

- `ABS_TOLERANCE = 1 VND` cho payload có cùng độ chính xác.
- Cho HTML hiển thị theo triệu/tỷ: tolerance suy từ `scale_observed` và precision hiển thị, không dùng một tỷ lệ chung tùy tiện.
- Mọi tolerance phải có `tolerance_rule_id` và test chống false match.

Ngoài so giá trị, cần kiểm tra phương trình kế toán và quan hệ subtotal khi taxonomy cho phép.

## Relationships

- supports: [QFD-240](./20260825-qfd-240-chuan-hoa-ky-bao-cao.md)
- supports: [QFD-250](./20260825-qfd-250-don-vi-tien-te-va-dau.md)
- supports: [QFD-300](./20260825-qfd-300-reconciliation-engine-xac-dinh.md)
- supports: [QFD-340](./20260825-qfd-340-hang-doi-review.md)
