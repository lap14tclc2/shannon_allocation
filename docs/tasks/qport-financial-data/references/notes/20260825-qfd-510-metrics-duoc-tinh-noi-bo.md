---
id: QFD-510
title: "Metrics được tính nội bộ"
type: principle
status: verified
created: 2026-08-25
updated: 2026-08-25
sources:
  - ../sources/source-qport-financial-data-design.md
---

# QFD-510 — Metrics được tính nội bộ

## Claim

QPort nên lấy raw financial facts đã chuẩn hóa rồi tự tính ROE, margins, leverage, FCF, growth và valuation inputs. Không chọn ratio của vendor làm nguồn sự thật nếu có thể tái tạo từ fact.

Mỗi metric cần:

- `metric_code` và version công thức.
- Danh sách input canonical fact IDs.
- Chính sách `TTM/FY/YTD`, entity type và missing value.
- `computed_at`, `as_of` và quality tổng hợp từ input.

AI có thể giải thích hoặc hỗ trợ mapping review, nhưng **không nằm trên critical path tính toán**.

## Relationships

- supports: [QFD-260](./20260825-qfd-260-taxonomy-theo-loai-hinh-doanh-nghiep.md)
- supports: [QFD-500](./20260825-qfd-500-qport-data-api.md)
- supports: [QFD-520](./20260825-qfd-520-point-in-time-va-chong-look-ahead-bias.md)
