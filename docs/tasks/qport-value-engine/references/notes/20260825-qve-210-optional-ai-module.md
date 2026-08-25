---
id: QVE-210
title: "Optional AI module"
type: rule
status: draft
created: 2026-08-25
updated: 2026-08-25
sources:
  - ../sources/source-qport-value-engine-specification.md
---

# QVE-210 — Optional AI module

## Claim

AI có thể:

- trích xuất dữ liệu từ PDF chưa cấu trúc;
- tìm one-off items trong thuyết minh;
- tóm tắt báo cáo thường niên;
- so sánh thuyết minh giữa hai kỳ;
- tìm nội dung về ESOP, related parties và CAPEX;
- giải thích report bằng ngôn ngữ tự nhiên;
- chat dựa trên dữ liệu QPort đã lưu.

AI không được:

- sửa raw facts;
- tự tạo số liệu;
- tự chọn normalization adjustment;
- tự thay đổi discount rate;
- tự xác nhận moat hoặc management quality;
- tính fair value khác backend;
- tạo hoặc đề xuất trade như một hành động hệ thống.

Mọi AI output phải phân loại:

```text
REPORTED_FACT
CALCULATED_METRIC
USER_ASSUMPTION
AI_INFERENCE
MISSING_INFORMATION
```

Khi AI bị tắt hoặc hết quota, toàn bộ Value Engine vẫn hoạt động bình thường.

---

## Relationships

- derived-from: [SRC-QVE-001](../sources/source-qport-value-engine-specification.md)
- extends: [QVE-170](./20260825-qve-170-valuation-report-contract.md)
- supports: [QVE-021](./20260825-qve-021-deterministic-first.md)
