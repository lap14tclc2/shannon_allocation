---
id: QFD-430
title: "Quan sát và SLO"
type: runbook
status: draft
created: 2026-08-25
updated: 2026-08-25
sources:
  - ../sources/source-qport-financial-data-design.md
---

# QFD-430 — Quan sát và SLO

## Claim

Dashboard tối thiểu theo provider và entity type:

- Tỷ lệ job thành công, latency, retry, rate-limit.
- Số kỳ/fact mới; độ trễ từ publish đến ingest.
- Tỷ lệ mapping unknown, parse failure và schema drift.
- Tỷ lệ `CROSS_SOURCE_VERIFIED`, `SINGLE_SOURCE`, `CONFLICT`, `QUARANTINED`.
- Chênh lệch theo line item, kỳ và source pair.
- Raw payload không có downstream normalized fact.

SLO gợi ý cho MVP: 99% báo cáo mới của universe theo dõi được phát hiện trong 24 giờ sau khi nguồn khả dụng; 100% canonical facts có evidence chain; 0 silent schema failure.

## Relationships

- supports: [QFD-230](./20260825-qfd-230-provenance-va-evidence-chain.md)
- supports: [QFD-330](./20260825-qfd-330-trang-thai-chat-luong.md)
- supports: [QFD-340](./20260825-qfd-340-hang-doi-review.md)
- supports: [QFD-410](./20260825-qfd-410-connector-boundary-va-provider-registry.md)
