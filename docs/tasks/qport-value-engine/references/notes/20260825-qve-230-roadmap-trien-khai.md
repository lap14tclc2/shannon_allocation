---
id: QVE-230
title: "Roadmap triển khai"
type: plan
status: draft
created: 2026-08-25
updated: 2026-08-25
sources:
  - ../sources/source-qport-value-engine-specification.md
---

# QVE-230 — Roadmap triển khai

## Claim

### Phase 1 — Fundamental foundation

1. Canonical financial data schema.
2. Source metadata and lineage.
3. Validation engine.
4. Annual and TTM snapshots.
5. Share-count and corporate-action normalization.

### Phase 2 — Non-financial MVP

6. Per-share metrics.
7. Quality diagnostics.
8. Normalized earnings.
9. Owner Earnings engine.
10. Owner Earnings DCF.
11. EPV cross-check.
12. Bear/Base/Bull scenarios.
13. Margin of safety.
14. Reverse DCF.
15. Sensitivity matrix.

Mục tiêu đầu tiên: hỗ trợ các cấu trúc doanh nghiệp như FPT, DGC và các mảng phi tài chính của REE.

### Phase 3 — Banking model

16. Bank-specific data schema.
17. Bank quality metrics.
18. Normalized ROE.
19. Residual Income Model.
20. Justified P/B.

Mục tiêu: hỗ trợ ACB mà không sử dụng sai CFO hoặc generic enterprise DCF.

### Phase 4 — Capital allocation and monitoring

21. Capital-allocation timeline.
22. Dilution and ESOP diagnostics.
23. Fundamental change detection.
24. Investment thesis tracker.
25. Valuation history.

### Phase 5 — Portfolio integration

26. Portfolio look-through earnings.
27. Portfolio Owner Earnings.
28. Portfolio FCF yield.
29. Dividend-income projection.
30. Valuation distribution across holdings.

Mọi output vẫn informational only.

### Phase 6 — Optional AI

31. PDF extraction.
32. Note comparison.
33. Grounded explanation.
34. Gemini chat integration.

---

## Relationships

- derived-from: [SRC-QVE-001](../sources/source-qport-value-engine-specification.md)
- requires: [QVE-240](./20260825-qve-240-mvp-definition-of-done.md)
