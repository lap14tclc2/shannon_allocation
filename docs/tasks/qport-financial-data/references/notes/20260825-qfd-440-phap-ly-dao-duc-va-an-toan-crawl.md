---
id: QFD-440
title: "Pháp lý, đạo đức và an toàn crawl"
type: rule
status: verified
created: 2026-08-25
updated: 2026-08-25
sources:
  - ../sources/source-qport-financial-data-design.md
---

# QFD-440 — Pháp lý, đạo đức và an toàn crawl

## Claim

- Chỉ lấy nội dung được phép truy cập công khai và đúng mục đích đã rà soát.
- Không né auth, CAPTCHA, paywall, IP block hoặc hạn chế kỹ thuật.
- User-Agent minh bạch khi phù hợp; giới hạn tốc độ và concurrency bảo thủ.
- Tắt connector ngay khi điều khoản, robots hoặc hành vi site thay đổi bất lợi.
- Không log credential/cookie; secrets chỉ tồn tại trong secret manager nếu phase sau dùng nguồn có auth.
- Lưu metadata/provenance theo nhu cầu audit; retention raw content phải tuân thủ quyền sử dụng.

---

## Relationships

- supports: [QFD-110](./20260825-qfd-110-he-b-html-ingestion.md)
- supports: [QFD-130](./20260825-qfd-130-danh-gia-cac-nguon-ngoai-mvp.md)
- supports: [QFD-410](./20260825-qfd-410-connector-boundary-va-provider-registry.md)
