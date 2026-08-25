---
id: QVE-121
title: "Cấu hình mẫu"
type: contract
status: draft
created: 2026-08-25
updated: 2026-08-25
sources:
  - ../sources/source-qport-value-engine-specification.md
---

# QVE-121 — Cấu hình mẫu

## Claim

```yaml
scenarios:
  bear:
    growth_years_1_5: 0.04
    terminal_growth: 0.02
    discount_rate: 0.15
    maintenance_capex_policy: conservative

  base:
    growth_years_1_5: 0.08
    terminal_growth: 0.03
    discount_rate: 0.13
    maintenance_capex_policy: depreciation_proxy

  bull:
    growth_years_1_5: 0.12
    terminal_growth: 0.04
    discount_rate: 0.11
    maintenance_capex_policy: user_defined
```

Đây chỉ là cấu trúc minh họa, không phải default rate cho thị trường Việt Nam. Discount rate, inflation, risk-free rate và growth assumptions phải là dữ liệu cấu hình có ngày hiệu lực và được kiểm chứng hiện hành trước khi sử dụng.

## Relationships

- derived-from: [SRC-QVE-001](../sources/source-qport-value-engine-specification.md)
- applies-to: [QVE-111](./20260825-qve-111-owner-earnings-dcf.md)
