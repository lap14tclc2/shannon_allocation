---
id: QVE-102
title: "Maintenance CAPEX policies"
type: contract
status: draft
created: 2026-08-25
updated: 2026-08-25
sources:
  - ../sources/source-qport-value-engine-specification.md
---

# QVE-102 — Maintenance CAPEX policies

## Claim

#### Conservative

```text
maintenance_capex = total_capex
```

Thường dùng cho Bear scenario.

#### Depreciation proxy

```text
maintenance_capex = normalized_depreciation_and_amortization
```

Chỉ dùng khi business model và asset base tương đối ổn định.

#### User-defined

Người dùng nhập maintenance CAPEX từ nghiên cứu thuyết minh.

```yaml
maintenance_capex:
  method: user_defined
  amount: 1500000000000
  source_note: Annual report 2025, CAPEX section
  reason: Excludes disclosed expansion project
```

#### Scenario range

```text
Bear: total CAPEX
Base: normalized D&A or reviewed estimate
Bull: reviewed maintenance CAPEX estimate
```

## Relationships

- derived-from: [SRC-QVE-001](../sources/source-qport-value-engine-specification.md)
- applies-to: [QVE-101](./20260825-qve-101-cong-thuc.md)
