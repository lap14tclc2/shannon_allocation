---
id: QFD-120
title: "Nguồn evidence chính thức"
type: principle
status: verified
created: 2026-08-25
updated: 2026-08-25
sources:
  - ../sources/source-qport-financial-data-design.md
---

# QFD-120 — Nguồn evidence chính thức

## Claim

Thứ tự bằng chứng mặc định:

1. BCTC/công bố chính thức từ doanh nghiệp, HOSE, HNX hoặc SSC.
2. Dữ liệu structured từ connector API đã kiểm định.
3. HTML công khai từ CafeF.
4. Nguồn web bổ sung đã được phê duyệt.

Ưu tiên trên chỉ là mặc định. Một tài liệu chính thức cũ không được ghi đè bản điều chỉnh mới hơn. `published_at`, `revision_no` và `supersedes` phải tham gia quyết định.

## Relationships

- supports: [QFD-020](./20260825-qfd-020-ba-vai-tro-nguon-du-lieu.md)
- supports: [QFD-140](./20260825-qfd-140-khong-tron-domain-su-kien-voi-bctc.md)
- supports: [QFD-230](./20260825-qfd-230-provenance-va-evidence-chain.md)
- supports: [QFD-320](./20260825-qfd-320-chon-nguon-thang-va-xu-ly-revision.md)
