---
id: QFD-520
title: "Point-in-time và chống look-ahead bias"
type: rule
status: verified
created: 2026-08-25
updated: 2026-08-25
sources:
  - ../sources/source-qport-financial-data-design.md
---

# QFD-520 — Point-in-time và chống look-ahead bias

## Claim

Backtest tại thời điểm `T` chỉ được dùng dữ liệu mà hệ thống có thể chứng minh đã được công bố/quan sát trước hoặc bằng `T`. `period_end` không phải availability date.

Mọi query nghiên cứu MUST hỗ trợ `as_of`. Nếu `published_at` không biết, dùng `observed_at` bảo thủ và đánh dấu uncertainty. Restatement chỉ ảnh hưởng kết quả sau thời điểm bản điều chỉnh khả dụng.

---

## Relationships

- supports: [QFD-240](./20260825-qfd-240-chuan-hoa-ky-bao-cao.md)
- supports: [QFD-320](./20260825-qfd-320-chon-nguon-thang-va-xu-ly-revision.md)
- supports: [QFD-500](./20260825-qfd-500-qport-data-api.md)
- supports: [QFD-510](./20260825-qfd-510-metrics-duoc-tinh-noi-bo.md)
