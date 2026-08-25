---
id: QVE-223
title: "Invariant tests"
type: contract
status: draft
created: 2026-08-25
updated: 2026-08-25
sources:
  - ../sources/source-qport-value-engine-specification.md
---

# QVE-223 — Invariant tests

## Claim

Ví dụ:

```text
Higher discount rate must not increase DCF value.
Higher diluted share count must not increase value per share.
Higher debt must not increase equity value, all else equal.
Higher Owner Earnings must not reduce DCF value, all else equal.
Terminal growth must remain below discount rate.
Missing value must never silently become zero.
Valuation run must never mutate portfolio shares or cash.
```

## Relationships

- derived-from: [SRC-QVE-001](../sources/source-qport-value-engine-specification.md)
- extends: [QVE-221](./20260825-qve-221-unit-tests.md)
