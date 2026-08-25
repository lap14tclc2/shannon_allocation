---
id: QFD-220
title: "ProviderFact contract"
type: contract
status: verified
created: 2026-08-25
updated: 2026-08-25
sources:
  - ../sources/source-qport-financial-data-design.md
---

# QFD-220 — ProviderFact contract

## Claim

```yaml
ProviderFact:
  security_id: uuid
  symbol_observed: FPT
  statement_type: INCOME_STATEMENT
  line_item_code: IS.REVENUE.NET
  label_observed: Doanh thu thuần
  value_raw: "15,758,123"
  value_normalized: 15758123000000
  currency: VND
  scale_observed: 1000000
  period_start: 2026-01-01
  period_end: 2026-03-31
  period_type: QUARTER
  fiscal_year: 2026
  fiscal_quarter: 1
  consolidation_scope: CONSOLIDATED
  revision_no: 0
  provider_id: cafef_html
  source_document_id: uuid
  observed_at: 2026-04-30T03:00:00Z
  parser_version: cafef-financials@1.0.0
```

`value_normalized` lưu ở đơn vị cơ sở của `currency`; `value_raw` và `scale_observed` luôn được giữ để tái lập phép chuyển đổi.

## Relationships

- supports: [QFD-100](./20260825-qfd-100-he-a-api-ingestion.md)
- supports: [QFD-110](./20260825-qfd-110-he-b-html-ingestion.md)
- supports: [QFD-210](./20260825-qfd-210-identity-key-cua-mot-financial-fact.md)
- supports: [QFD-230](./20260825-qfd-230-provenance-va-evidence-chain.md)
