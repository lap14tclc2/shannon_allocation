---
id: QFD-230
title: "Provenance và evidence chain"
type: contract
status: verified
created: 2026-08-25
updated: 2026-08-25
sources:
  - ../sources/source-qport-financial-data-design.md
---

# QFD-230 — Provenance và evidence chain

## Claim

Mỗi canonical fact MUST dẫn được đến:

```text
canonical_fact
  -> reconciliation_decision
  -> provider_fact candidate(s)
  -> source_document
  -> raw_object / source URL
```

`source_document` tối thiểu có: URL, provider, document type, published date nếu biết, fetched time, MIME type, content hash, HTTP metadata, extraction status và retention policy.

Nếu không có raw object hoặc URL có thể audit, fact không được mang trạng thái `VERIFIED`.

## Relationships

- supports: [QFD-120](./20260825-qfd-120-nguon-evidence-chinh-thuc.md)
- supports: [QFD-200](./20260825-qfd-200-ba-lop-du-lieu.md)
- supports: [QFD-220](./20260825-qfd-220-providerfact-contract.md)
- supports: [QFD-320](./20260825-qfd-320-chon-nguon-thang-va-xu-ly-revision.md)
- supports: [QFD-430](./20260825-qfd-430-quan-sat-va-slo.md)
