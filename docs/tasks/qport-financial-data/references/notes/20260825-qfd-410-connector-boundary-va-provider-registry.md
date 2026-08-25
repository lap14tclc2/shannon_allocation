---
id: QFD-410
title: "Connector boundary và provider registry"
type: contract
status: verified
created: 2026-08-25
updated: 2026-08-25
sources:
  - ../sources/source-qport-financial-data-design.md
---

# QFD-410 — Connector boundary và provider registry

## Claim

Provider registry lưu:

- `provider_id`, capability, owner, enabled flag.
- auth mode: `NONE | API_KEY | SESSION`.
- rate policy, timeout, retry policy, cache TTL.
- parser/adapter version và schema fingerprint.
- terms/robots review date.
- health state: `HEALTHY | DEGRADED | DISABLED`.

Domain code chỉ gọi interface chung. Không import SDK Vnstock hoặc selector CafeF vào core portfolio logic.

## Relationships

- supports: [QFD-100](./20260825-qfd-100-he-a-api-ingestion.md)
- supports: [QFD-110](./20260825-qfd-110-he-b-html-ingestion.md)
- supports: [QFD-400](./20260825-qfd-400-kien-truc-dich-vu.md)
- supports: [QFD-430](./20260825-qfd-430-quan-sat-va-slo.md)
