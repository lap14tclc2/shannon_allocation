---
id: QVE-111
title: "Owner Earnings DCF"
type: contract
status: draft
created: 2026-08-25
updated: 2026-08-25
sources:
  - ../sources/source-qport-value-engine-specification.md
---

# QVE-111 — Owner Earnings DCF

## Claim

```text
Intrinsic operating value =
Σ OwnerEarnings(t) / (1 + r)^t
+ TerminalValue / (1 + r)^n
```

```text
TerminalValue =
OwnerEarnings(n+1) / (r − g)
```

```text
Equity value =
Operating value
+ Excess cash
+ Non-operating investments
− Debt
− Minority interest
− Other senior claims
```

```text
Intrinsic value per share =
Equity value / diluted shares
```

Guardrails:

- `terminal_growth < discount_rate`;
- terminal growth không được vượt quá giới hạn policy dài hạn;
- sử dụng diluted shares;
- không double-count cash và investment income;
- không trừ debt hai lần;
- cảnh báo nếu terminal value chiếm tỷ trọng quá lớn.

## Relationships

- derived-from: [SRC-QVE-001](../sources/source-qport-value-engine-specification.md)
- requires: [QVE-101](./20260825-qve-101-cong-thuc.md)
- requires: [QVE-121](./20260825-qve-121-cau-hinh-mau.md)
