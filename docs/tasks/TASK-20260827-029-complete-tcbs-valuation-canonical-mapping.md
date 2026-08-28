---
id: TASK-20260827-029
title: Map TCBS cash flow fromSale, D&A EBITDA, and overview shares to unlock Valuation Engine
status: completed
priority: high
created: 2026-08-27
updated: 2026-08-27
tags: [finance-data, tcbs, value-engine, canonical-facts, valuation]
related: [TASK-20260827-027, TASK-20260827-028]
---

## Requirement

Enable the deterministic Value Engine and Valuation UI by accurately mapping TCBS financial fields:
1. `CF.OPERATING.NET` mapped to TCBS cash flow field `fromSale` (Lưu chuyển tiền thuần từ hoạt động kinh doanh / Bán hàng).
2. `CF.OPERATING.DEPRECIATION` mapped to D&A (calculated from `ebitda - operationProfit` or direct depreciation field in income/cash flow; 0 for banks).
3. `IS.SHARES.OUTSTANDING` mapped to outstanding shares (from TCBS ticker overview / balance sheet capital).

## Context

The Valuation API (`GET /api/portfolio/valuation/{symbol}`) requires 8 deterministic canonical facts from `qport_finance.canonical_facts`. Currently, `CF.OPERATING.NET`, `CF.OPERATING.DEPRECIATION`, and `IS.SHARES.OUTSTANDING` were missing aliases for the TCBS data shape, causing `valuation_readiness_audit` to block valuations with `404 FINANCE_DATA_NOT_READY`.

## Acceptance Criteria

- [x] `_canonicalize_document` maps `fromSale` to `CF.OPERATING.NET`.
- [x] `_canonicalize_document` computes or maps `CF.OPERATING.DEPRECIATION` from EBITDA/Depreciation.
- [x] `_canonicalize_document` maps `IS.SHARES.OUTSTANDING` from available share/capital metadata.
- [x] `valuation_readiness_audit` returns `status: READY` for audited equity symbols (FPT, MWG, DGC, ACB, IDC, HPG, VNM, etc.).
- [x] Valuation endpoint `GET /api/portfolio/valuation/{symbol}` returns `200 OK` with valid 3-scenario DCF and Owner Earnings metrics.
- [x] Regression tests cover canonical mapping and readiness audit.

## Constraints and Invariants

- Do not alter the core Buy & Hold Ledger invariant.
- Do not fabricate random or synthetic numbers.
- Maintain transactional safety in `finance_catalog.py`.

## Implementation Tasks

- [x] Update `_canonicalize_document` in `python/portfolio/finance_catalog.py` to map `fromSale`, `CF.OPERATING.DEPRECIATION` and `IS.SHARES.OUTSTANDING`.
- [x] Reprocess canonical facts for target symbols and entire database catalog (151,595 canonical facts).
- [x] Verify `valuation_readiness_audit` and `valuation_snapshot_from_catalog`.
- [x] Test API `GET /api/portfolio/valuation/FPT`, `DGC`, `ACB`, `MWG`, `HPG`, `VNM`, `IDC`.
- [x] Run test suite and record evidence.

## Related Notes

- [`docs/finance-data-sync.md`](file:///f:/workspace/shannon_allocation/docs/finance-data-sync.md)

## Decisions

- Decision 1: Use `fromSale` as `CF.OPERATING.NET` because in TCBS statement schema `fromSale` represents Operating Cash Flow.
- Decision 2: Use `ebitda - operationProfit` (when positive) as `CF.OPERATING.DEPRECIATION` (D&A = EBITDA - Operating Profit) and 0 for banks/financials where D&A is embedded in operating costs.
- Decision 3: Use `capital * 100,000` (1 tỷ VND / 10.000 đ par value) or `outstandingShare` as `IS.SHARES.OUTSTANDING`.

## Validation Evidence

1. **Valuation Snapshots Verified (All `Snapshot OK: True`, `status: READY`):**
   - `FPT`: Net Income = 11.232 tỷ, OCF = 10.136 tỷ, D&A = 2.914 tỷ, CapEx = -5.098 tỷ, Shares = 1.703.500.000
   - `DGC`: Net Income = 3.154 tỷ, OCF = 1.849 tỷ, D&A = 315 tỷ, CapEx = -589 tỷ, Shares = 379.800.000
   - `ACB`: Net Income = 15.625 tỷ, OCF = 28.160 tỷ, D&A = 0 tỷ, CapEx = -702 tỷ, Shares = 5.136.700.000
   - `MWG`: Net Income = 7.073 tỷ, OCF = 6.096 tỷ, D&A = 1.891 tỷ, CapEx = -888 tỷ, Shares = 1.469.700.000
   - `IDC`: Net Income = 2.354 tỷ, OCF = 3.914 tỷ, D&A = 986 tỷ, CapEx = -3.103 tỷ, Shares = 379.500.000
   - `HPG`: Net Income = 15.515 tỷ, OCF = 17.366 tỷ, D&A = 8.470 tỷ, CapEx = -25.748 tỷ, Shares = 7.675.500.000
   - `VNM`: Net Income = 9.414 tỷ, OCF = 8.668 tỷ, D&A = 2.116 tỷ, CapEx = -1.762 tỷ, Shares = 2.090.000.000

2. **Automated Test Results:**
   - `tests/test_valuation_readiness_audit.py`: PASSED (1/1)
   - `python/portfolio/tests/test_value_engine.py`: PASSED (6/6)

## Result

Canonical facts mapping updated and reprocessed across 45,824 documents in PostgreSQL (yielding 151,595 canonical facts). The Value Engine audit now resolves `READY` for all equity symbols, unlocking the 3-scenario DCF and Owner Earnings Valuation API.

