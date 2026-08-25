---
id: QFD-610
title: "Roadmap triển khai"
type: plan
status: draft
created: 2026-08-25
updated: 2026-08-25
sources:
  - ../sources/source-qport-financial-data-design.md
---

# QFD-610 — Roadmap triển khai

## Claim

### Phase 0 — Spike và contract

- Chốt taxonomy v1 và identity key.
- Probe live Vnstock guest cho 5 nhóm doanh nghiệp.
- Lưu 10–20 HTML fixtures CafeF và xác minh quyền crawl.
- Chốt quota, cache và retention.

### Phase 1 — MVP vertical slice

- Adapter Vnstock: profile + ba statements.
- Adapter CafeF: cùng tập dữ liệu cho một universe nhỏ.
- Raw store, normalize, reconcile, canonical query.
- Quality dashboard và evidence drill-down.

### Phase 2 — Production hardening

- Official filing evidence collector.
- Restatement và bitemporal history.
- Review queue, schema-drift alert, replay pipeline.
- Mở rộng universe và lịch chạy.

### Phase 3 — Nguồn bổ sung

- Đánh giá Simplize/Vietstock hoặc nguồn licensed.
- Chỉ thêm nguồn nếu tăng coverage/quality đo được, không thêm chỉ để “nhiều nguồn”.

## Relationships

- supports: [QFD-260](./20260825-qfd-260-taxonomy-theo-loai-hinh-doanh-nghiep.md)
- supports: [QFD-400](./20260825-qfd-400-kien-truc-dich-vu.md)
- supports: [QFD-600](./20260825-qfd-600-khoang-trong-hien-tai-cua-shannon-allocation.md)
- supports: [QFD-620](./20260825-qfd-620-chien-luoc-test.md)
