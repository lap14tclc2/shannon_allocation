---
id: QVE-056
title: "Market data"
type: contract
status: draft
created: 2026-08-25
updated: 2026-08-25
sources:
  - ../sources/source-qport-value-engine-specification.md
---

# QVE-056 — Market data

## Claim

```text
market_price
price_timestamp
price_source
price_freshness
market_cap
```

Nếu giá thiếu hoặc stale, hệ thống vẫn có thể tính intrinsic value nhưng không được tính margin of safety bằng giá giả định không được khai báo.

---

## Relationships

- derived-from: [SRC-QVE-001](../sources/source-qport-value-engine-specification.md)
