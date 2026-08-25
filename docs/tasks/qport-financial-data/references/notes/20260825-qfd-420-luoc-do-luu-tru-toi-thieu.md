---
id: QFD-420
title: "Lược đồ lưu trữ tối thiểu"
type: contract
status: draft
created: 2026-08-25
updated: 2026-08-25
sources:
  - ../sources/source-qport-financial-data-design.md
---

# QFD-420 — Lược đồ lưu trữ tối thiểu

## Claim

| Table | Mục đích | Thuộc tính quan trọng |
|---|---|---|
| `securities` | master định danh | `security_id`, symbol, exchange, ISIN, entity_type |
| `source_documents` | nguồn và raw pointer | provider, URL, hash, fetched/published time |
| `provider_facts` | fact normalized theo nguồn | identity fields, value, source, parser version |
| `canonical_facts` | fact được phục vụ | chosen value, status, valid time, decision ID |
| `reconciliation_decisions` | giải thích lựa chọn | candidates, rule version, winner, reason |
| `line_item_mappings` | mapping label → taxonomy | provider, label fingerprint, code, scope, version |
| `ingestion_runs` | audit từng job | params, counts, timings, errors, code version |
| `review_queue` | conflict/quarantine | severity, state, owner, resolution |

Tất cả timestamps lưu UTC; business dates giữ dạng `DATE`. Dùng decimal/numeric, không dùng binary float cho tiền.

## Relationships

- supports: [QFD-200](./20260825-qfd-200-ba-lop-du-lieu.md)
- supports: [QFD-210](./20260825-qfd-210-identity-key-cua-mot-financial-fact.md)
- supports: [QFD-230](./20260825-qfd-230-provenance-va-evidence-chain.md)
- supports: [QFD-320](./20260825-qfd-320-chon-nguon-thang-va-xu-ly-revision.md)
