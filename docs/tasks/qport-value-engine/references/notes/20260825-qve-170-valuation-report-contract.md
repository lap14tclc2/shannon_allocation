---
id: QVE-170
title: "Valuation Report Contract"
type: contract
status: draft
created: 2026-08-25
updated: 2026-08-25
sources:
  - ../sources/source-qport-value-engine-specification.md
---

# QVE-170 — Valuation Report Contract

## Claim

```yaml
report_id: val_FPT_20260825_v1
ticker: FPT
valuation_date: 2026-08-25
currency: VND
policy_version: buffet_value_policy_v1
financial_snapshot_version: fs_FPT_2026Q2_v2
sector_model: owner_earnings_dcf

data_quality:
  status: PASS
  annual_years: 10
  latest_report_audit_status: reviewed
  latest_period: 2026-Q2

business_quality:
  status: PASS_WITH_WARNINGS
  circle_of_competence: UNDERSTOOD
  earnings_consistency: HIGH
  balance_sheet_resilience: STRONG
  capital_allocation: REVIEW_REQUIRED

normalized_metrics:
  normalized_net_income: null
  normalized_owner_earnings: null
  owner_earnings_per_share: null
  normalized_roe: null
  normalized_roic: null

valuation:
  bear: null
  base: null
  bull: null
  market_price: null
  base_margin_of_safety: null
  confidence: MEDIUM

reverse_dcf:
  implied_owner_earnings_growth_10y: null

warnings:
  - MAINTENANCE_CAPEX_ESTIMATED

decision_boundary:
  informational_only: true
  trade_created: false
```

`null` phải được giữ nguyên khi chưa có dữ liệu; không thay bằng 0.

---

## Relationships

- derived-from: [SRC-QVE-001](../sources/source-qport-value-engine-specification.md)
- requires: [QVE-061](./20260825-qve-061-trang-thai.md)
- requires: [QVE-122](./20260825-qve-122-output.md)
- requires: [QVE-130](./20260825-qve-130-margin-of-safety.md)
- requires: [QVE-140](./20260825-qve-140-reverse-dcf.md)
- requires: [QVE-150](./20260825-qve-150-sensitivity-analysis.md)
- requires: [QVE-161](./20260825-qve-161-trang-thai.md)
