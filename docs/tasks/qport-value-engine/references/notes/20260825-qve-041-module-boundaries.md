---
id: QVE-041
title: "Module boundaries"
type: decision
status: draft
created: 2026-08-25
updated: 2026-08-25
sources:
  - ../sources/source-qport-value-engine-specification.md
---

# QVE-041 — Module boundaries

## Claim

```text
fundamental_data/
  ingestion
  canonicalization
  validation

fundamental_analysis/
  per_share_metrics
  profitability
  balance_sheet
  capital_allocation
  dilution
  quality_diagnostics

valuation/
  normalization
  owner_earnings
  dcf
  earnings_power
  dividend_discount
  residual_income
  justified_pb
  sum_of_parts
  rnav
  reverse_valuation
  sensitivity

valuation_policy/
  assumptions
  sector_routing
  thresholds
  versioning

reporting/
  valuation_report
  evidence
  warnings
  history

ai_optional/
  document_extraction
  report_summary
  grounded_chat
```

---

## Relationships

- derived-from: [SRC-QVE-001](../sources/source-qport-value-engine-specification.md)
- extends: [QVE-040](./20260825-qve-040-kien-truc-tong-the.md)
