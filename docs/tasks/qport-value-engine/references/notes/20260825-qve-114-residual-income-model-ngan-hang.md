---
id: QVE-114
title: "Residual Income Model — ngân hàng"
type: contract
status: draft
created: 2026-08-25
updated: 2026-08-25
sources:
  - ../sources/source-qport-value-engine-specification.md
---

# QVE-114 — Residual Income Model — ngân hàng

## Claim

```text
Residual Income(t) =
Net Income(t) − required_return × opening_equity(t)
```

```text
Equity value =
Current book value
+ present value of future residual income
```

Các input ngân hàng:

- book value;
- normalized ROE;
- cost of equity;
- equity growth;
- payout ratio;
- NPL;
- loan-loss coverage;
- credit cost;
- CAR;
- NIM và CASA nếu có.

Không dùng CFO hoặc EV/EBITDA truyền thống để định giá ngân hàng.

## Relationships

- derived-from: [SRC-QVE-001](../sources/source-qport-value-engine-specification.md)
- requires: [QVE-070](./20260825-qve-070-sector-routing.md)
- requires: [QVE-083](./20260825-qve-083-profitability.md)
