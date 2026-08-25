---
id: QVE-062
title: "Kiểm tra bắt buộc"
type: rule
status: draft
created: 2026-08-25
updated: 2026-08-25
sources:
  - ../sources/source-qport-value-engine-specification.md
---

# QVE-062 — Kiểm tra bắt buộc

## Claim

1. Có ít nhất 5 năm dữ liệu annual để định giá; ưu tiên 10 năm.
2. Balance sheet reconciliation nằm trong tolerance cho phép.
3. Đơn vị tiền tệ nhất quán.
4. Không trộn báo cáo riêng và hợp nhất.
5. Không double-count dữ liệu year-to-date.
6. Share count phản ánh stock dividend, split và issuance.
7. Phát hiện kỳ bị restated.
8. Không tự thay missing value bằng 0.
9. Không tính trailing twelve months khi thiếu kỳ thành phần.
10. Gắn audit/review status cho từng kỳ.

## Relationships

- derived-from: [SRC-QVE-001](../sources/source-qport-value-engine-specification.md)
