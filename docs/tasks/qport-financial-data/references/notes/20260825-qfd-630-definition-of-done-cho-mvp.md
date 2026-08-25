---
id: QFD-630
title: "Definition of Done cho MVP"
type: checklist
status: draft
created: 2026-08-25
updated: 2026-08-25
sources:
  - ../sources/source-qport-financial-data-design.md
---

# QFD-630 — Definition of Done cho MVP

## Claim

- [ ] Hai connector hoạt động độc lập: một API, một HTML.
- [ ] Mọi response được lưu raw có hash và connector version.
- [ ] Ba statement types, năm/quý và scope được biểu diễn không mơ hồ.
- [ ] Canonical fact có evidence chain và quality status.
- [ ] Không có code path lấy trung bình các giá trị kế toán.
- [ ] Conflict không đi vào production API mặc định.
- [ ] Restatement không xóa lịch sử.
- [ ] Query `as_of` vượt test chống look-ahead.
- [ ] Fixture tests bao phủ ít nhất bốn entity types.
- [ ] Rate limit, retry, cache, circuit breaker và kill switch được cấu hình.
- [ ] Dashboard phát hiện silent zero-data/schema drift.
- [ ] Tài liệu vận hành mô tả cách disable provider và replay raw data.

---

## Relationships

- supports: [QFD-330](./20260825-qfd-330-trang-thai-chat-luong.md)
- supports: [QFD-430](./20260825-qfd-430-quan-sat-va-slo.md)
- supports: [QFD-610](./20260825-qfd-610-roadmap-trien-khai.md)
- supports: [QFD-620](./20260825-qfd-620-chien-luoc-test.md)
