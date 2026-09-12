# TASK-20260912-145: Full UI Semantic Audit — Remove All Internal Machine Keys From User-Facing UI

## Status: completed
- Date: 2026-09-12
- Priority: High
- Ticker / Domain: Presentation Layer, Vietnamese Semantics, Frontend & Backend API

---

## Requirement

Audit the entire QPort repository (frontend + backend presentation/serialization layer) to guarantee that **ZERO internal enums, machine keys, status codes, identifiers, or ALL_CAPS / snake_case technical strings** are rendered directly to the user.

Core Principles & Invariants:
1. **INTERNAL REPRESENTATION != USER PRESENTATION**: Internal calculation codes (`RECEIVABLES_GROW_FASTER_THAN_REVENUE`, `PROFIT_CASH_DIVERGENCE`, `NO_DETERIORATION`, `POSSIBLY_STRUCTURAL`, `WAIT_FOR_MOS`, `REVIEW_BUSINESS`, `BUSINESS_REVIEW_INCOMPLETE`, `UNPROTECTED`, `POTENTIAL_COMPOUNDER`, etc.) must pass through a centralized semantic presentation dictionary before rendering.
2. **NO RAW ENUM FALLBACK**: Never use unsafe fallbacks like `label || value` or ``${value}``. Fallbacks for unmapped/unknown machine keys must be safe Vietnamese phrases such as `"Chưa xác định"`.
3. **NO DATA LOSS**: Removing raw machine keys must NOT suppress warnings, flags, or financial findings.
4. **DO NOT ALTER DOMAIN CALCULATIONS**: Domain engines continue to use exact enum values for mathematical decisions. Only the user-facing presentation layer translates them into natural Vietnamese.

---

## Acceptance Criteria

- [x] AC1: `RECEIVABLES_GROW_FASTER_THAN_REVENUE` and `PROFIT_CASH_DIVERGENCE` never appear raw on UI; translated to natural Vietnamese ("Khoản phải thu tăng nhanh hơn doanh thu", "Lợi nhuận tăng nhưng dòng tiền không theo kịp").
- [x] AC2: All forensic findings, deterioration classifications, decision codes, MOS status codes, accounting flags, quality metrics, and Value Trap states are mapped to natural Vietnamese.
- [x] AC3: Centralized semantic dictionary established/verified on frontend and backend presentation layers.
- [x] AC4: Safe fallback configured (e.g. `"Chưa xác định"` instead of raw enum key) so unmapped enums never leak to UI.
- [x] AC5: Full static semantic search across repository conducted with documented whitelist for legitimate technical constants (HTML, CSS, HTTP, API, Tickers).
- [x] AC6: Audit report [`docs/reports/full-ui-semantic-audit.md`](file:///c:/workspace/shannon_allocation/docs/reports/full-ui-semantic-audit.md) generated with mapping dictionary & component inventory.
- [x] AC7: Golden symbols (`ACB`, `DGC`, `FPT`, `VIX`) verified to render 0 raw machine keys.
- [x] AC8: Automated tests created (`python/portfolio/tests/test_semantic_labels.py`) verifying label mapping and raw key detection.
- [x] AC9: Backend pytest (`pytest python/portfolio/tests`) passes.
- [x] AC10: Frontend build (`npm run build`) passes.

---

## Implementation Tasks

- [x] Task 1: Audit Python presentation layer (`vietnamese_presenter.py`, `munger_models.py`, `context_builder.py`, `aiExport.js`, etc.) for raw enum outputs.
- [x] Task 2: Audit React frontend components (`BusinessPage.jsx`, `BuffettMungerCard.jsx`, `ForensicsCard.jsx`, `ValueTrapCard.jsx`, `ChecklistModal.jsx`, etc.) for raw enum references or unsafe fallbacks (`|| val`).
- [x] Task 3: Centralize and expand semantic label dictionary in both Python backend presentation and React frontend utils.
- [x] Task 4: Fix all fallback patterns `label || raw_code` to use safe Vietnamese fallback `label || "Chưa xác định"`.
- [x] Task 5: Create automated test `test_semantic_labels.py` and static audit script to ensure future machine keys fail if unmapped.
- [x] Task 6: Verify golden symbols (`ACB`, `DGC`, `FPT`, `VIX`).
- [x] Task 7: Generate audit report `docs/reports/full-ui-semantic-audit.md`.
- [x] Task 8: Run pytest and frontend build, commit and push to branch.
