---
id: QVE-140
title: "Reverse DCF"
type: contract
status: draft
created: 2026-08-25
updated: 2026-08-25
sources:
  - ../sources/source-qport-value-engine-specification.md
---

# QVE-140 — Reverse DCF

## Claim

Reverse DCF giải phương trình để tìm mức tăng trưởng mà giá thị trường đang yêu cầu.

Ví dụ output:

```yaml
market_price: 95000
required_return: 0.13
terminal_growth: 0.03
implied_owner_earnings_cagr_10y: 0.118
historical_owner_earnings_cagr_5y: 0.092
roiic_5y: 0.145
```

Reverse DCF phải trả lời:

- implied growth là bao nhiêu;
- implied margin là bao nhiêu nếu giữ growth cố định;
- assumptions nào nhạy cảm nhất;
- implied expectations có cao hơn lịch sử và khả năng tái đầu tư hay không.

Không tự kết luận giá cao/thấp nếu dữ liệu nền không đủ tin cậy.

---

## Relationships

- derived-from: [SRC-QVE-001](../sources/source-qport-value-engine-specification.md)
- requires: [QVE-101](./20260825-qve-101-cong-thuc.md)
- requires: [QVE-056](./20260825-qve-056-market-data.md)
