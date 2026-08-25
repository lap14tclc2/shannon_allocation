---
id: QFD-210
title: "Identity key của một financial fact"
type: contract
status: verified
created: 2026-08-25
updated: 2026-08-25
sources:
  - ../sources/source-qport-financial-data-design.md
---

# QFD-210 — Identity key của một financial fact

## Claim

Khóa logic tối thiểu:

```text
security_id
+ statement_type
+ period_end
+ period_type
+ fiscal_year
+ fiscal_quarter (nullable)
+ consolidation_scope
+ line_item_code
+ currency
```

Trong đó:

- `statement_type`: `BALANCE_SHEET | INCOME_STATEMENT | CASH_FLOW`.
- `period_type`: `INSTANT | QUARTER | YTD | FY`.
- `consolidation_scope`: `CONSOLIDATED | SEPARATE | UNKNOWN`.
- `line_item_code`: mã nội bộ ổn định, không dùng label của vendor làm khóa.

`provider_id`, `revision_no` và `observed_at` không nằm trong identity kinh tế; chúng tạo các candidate/version khác nhau cho cùng fact.

## Relationships

- supports: [QFD-140](./20260825-qfd-140-khong-tron-domain-su-kien-voi-bctc.md)
- supports: [QFD-220](./20260825-qfd-220-providerfact-contract.md)
- supports: [QFD-240](./20260825-qfd-240-chuan-hoa-ky-bao-cao.md)
- supports: [QFD-250](./20260825-qfd-250-don-vi-tien-te-va-dau.md)
- supports: [QFD-300](./20260825-qfd-300-reconciliation-engine-xac-dinh.md)
