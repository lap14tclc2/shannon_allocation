---
id: QVE-089
title: "Dilution warnings"
type: contract
status: draft
created: 2026-08-25
updated: 2026-08-25
sources:
  - ../sources/source-qport-value-engine-specification.md
---

# QVE-089 — Dilution warnings

## Claim

Ví dụ rule:

```yaml
rule_id: DILUTION_001
condition: share_count_cagr_3y > net_income_cagr_3y
severity: warning
message: Share count is growing faster than net income.
```

```yaml
rule_id: CASH_QUALITY_001
condition: cfo_to_net_income_3y_average < configured_threshold
severity: warning
message: Operating cash flow has persistently lagged reported profit.
```

Ngưỡng phải nằm trong versioned policy, không hard-code rải rác trong application code.

---

## Relationships

- derived-from: [SRC-QVE-001](../sources/source-qport-value-engine-specification.md)
