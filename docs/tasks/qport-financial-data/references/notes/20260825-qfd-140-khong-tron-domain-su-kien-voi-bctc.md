---
id: QFD-140
title: "Không trộn domain sự kiện với BCTC"
type: decision
status: verified
created: 2026-08-25
updated: 2026-08-25
sources:
  - ../sources/source-qport-financial-data-design.md
---

# QFD-140 — Không trộn domain sự kiện với BCTC

## Claim

Cổ tức, quyền mua, chia tách và corporate actions là một bounded context riêng. Chúng có thể dùng VPS/CafeF/FireAnt/Vietcap theo pipeline hiện hữu nhưng không được ép vào schema dòng BCTC. Hai domain chỉ liên kết qua `security_id`, `effective_date` và provenance.

---

## Relationships

- supports: [QFD-010](./20260825-qfd-010-ranh-gioi-san-pham.md)
- supports: [QFD-120](./20260825-qfd-120-nguon-evidence-chinh-thuc.md)
- supports: [QFD-210](./20260825-qfd-210-identity-key-cua-mot-financial-fact.md)
