---
id: QFD-130
title: "Đánh giá các nguồn ngoài MVP"
type: reference
status: stale
created: 2026-08-25
updated: 2026-08-25
sources:
  - ../sources/source-qport-financial-data-design.md
---

# QFD-130 — Đánh giá các nguồn ngoài MVP

## Claim

| Nguồn | Vai trò dự kiến | Auth | Quyết định hiện tại |
|---|---|---:|---|
| CafeF | HTML fallback/cross-check | Không cho trang công khai | Dùng trong MVP, parser cô lập |
| FireAnt | Sự kiện/cổ tức hoặc dữ liệu nâng cao | API chính thức thường cần token/license | Không dùng làm nguồn fundamental không-auth |
| VPS | Sự kiện/cổ tức public endpoint nếu còn hoạt động | Có thể không cần auth ở một số endpoint | Không giả định có fundamental API công khai ổn định |
| Simplize | HTML cross-check tiềm năng | Trang công khai có thể không cần auth | Để phase 2, cần kiểm tra ToS và độ ổn định |
| Vietstock | HTML/evidence bổ sung | Một phần công khai | Để phase 2, cần kiểm tra cấu trúc và quyền sử dụng |

Không biến endpoint reverse-engineered thành dependency production mà không có owner, health check và kế hoạch thay thế.

## Relationships

- supports: [QFD-100](./20260825-qfd-100-he-a-api-ingestion.md)
- supports: [QFD-110](./20260825-qfd-110-he-b-html-ingestion.md)
- supports: [QFD-440](./20260825-qfd-440-phap-ly-dao-duc-va-an-toan-crawl.md)
