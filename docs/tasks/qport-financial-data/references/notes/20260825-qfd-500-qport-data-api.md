---
id: QFD-500
title: "QPort Data API"
type: contract
status: draft
created: 2026-08-25
updated: 2026-08-25
sources:
  - ../sources/source-qport-financial-data-design.md
---

# QFD-500 — QPort Data API

## Claim

Consumer chỉ đọc canonical model qua API/service nội bộ:

```http
GET /v1/companies/{symbol}
GET /v1/financials/{symbol}?statement=income&period=quarter&as_of=...
GET /v1/financial-facts/{symbol}?codes=IS.REVENUE.NET,IS.PROFIT.NET&as_of=...
GET /v1/data-quality/{symbol}?period_end=...
GET /v1/evidence/{canonical_fact_id}
```

Response MUST có `data_as_of`, `quality_status`, `source_summary`, `canonical_version` và `taxonomy_version`. Mặc định không trả fact `CONFLICT/QUARANTINED`; client có thể yêu cầu rõ qua debug/research scope.

## Relationships

- supports: [QFD-000](./20260825-qfd-000-tuyen-ngon-he-thong.md)
- supports: [QFD-330](./20260825-qfd-330-trang-thai-chat-luong.md)
- supports: [QFD-510](./20260825-qfd-510-metrics-duoc-tinh-noi-bo.md)
- supports: [QFD-520](./20260825-qfd-520-point-in-time-va-chong-look-ahead-bias.md)
