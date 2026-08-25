---
id: QVE-051
title: "Metadata bắt buộc"
type: contract
status: draft
created: 2026-08-25
updated: 2026-08-25
sources:
  - ../sources/source-qport-value-engine-specification.md
---

# QVE-051 — Metadata bắt buộc

## Claim

```yaml
ticker: FPT
exchange: HOSE
sector_code: technology_services
fiscal_period: 2026-Q2
period_start: 2026-01-01
period_end: 2026-06-30
report_type: interim
consolidated: true
audit_status: reviewed
restated: false
currency: VND
unit_multiplier: 1000000000
source: official_disclosure
published_at: 2026-07-30T00:00:00+07:00
retrieved_at: 2026-08-25T00:00:00+07:00
```

Không được trộn:

- báo cáo riêng và hợp nhất;
- quarterly và year-to-date;
- dữ liệu đã điều chỉnh và chưa điều chỉnh;
- VND, nghìn VND, triệu VND và tỷ VND;
- basic shares và diluted shares.

## Relationships

- derived-from: [SRC-QVE-001](../sources/source-qport-value-engine-specification.md)
