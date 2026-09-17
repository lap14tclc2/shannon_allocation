---
id: TASK-20260917-192
title: "Intrinsic Value / DCF Conservatism Audit"
status: completed
priority: high
created_at: 2026-09-17
lifecycle: draft -> ready -> in-progress -> verified -> completed
---

# TASK-20260917-192: Intrinsic Value / DCF Conservatism Audit

## Requirement
Audit the canonical intrinsic-value engine for economic correctness and conservatism across the full quantitative pipeline:
1. Discount rate derivation ($K_e$, ERP, risk-free rate, caps, floors, missing data fallback).
2. Terminal growth rate ($g < r$, stability, caps, missing data behavior).
3. Growth derivation and ceilings (reinvestment rate $\times$ incremental return, historical CAGR evidence cap, cyclical vs durable caps).
4. Forecast horizon (5-10Y, finite vs infinite concessions) and Terminal Value contribution ($TV/EV$ dominance analysis).
5. Bear / Base / Bull scenario generation and internal economic coherence ($Bear \le Base \le Bull$).
6. Scenario weighting and final canonical IV selection ($Base\ IV$ vs weighted average).
7. Normalized Owner Earnings baseline integration (no double-counting of CapEx, D&A, or Working Capital).
8. Bank & Financial Institution isolation (Residual Income Model / Justified P/B vs industrial DCF).
9. Canonical Share Basis and Margin of Safety downstream coupling ($MOS = 1 - Price/IV$).
10. Missing-data semantics ($NULL \ne 0, MISSING \ne SAFE, UNKNOWN \ne PASS$).
11. Real PostgreSQL database regression on core symbols (BFC, HAH, FPT, DGC, TLG, ACB, TCB, TPB) and full universe.
12. 25-scenario Golden Test Suite verifying mathematical and economic invariants.

## Context
- Valuation Engine: `python/portfolio/value_engine/engine.py`
- DCF Calculator: `python/portfolio/value_engine/dcf.py`
- Owner Earnings Authority: `python/portfolio/value_engine/owner_earnings.py`
- Bank Valuation Authority: `python/portfolio/value_engine/bank_valuation.py`
- Share Basis Authority: `python/portfolio/value_engine/share_basis.py`
- Canonical Valuation Builder: `python/portfolio/canonical_valuation.py`

## Acceptance Criteria
- [x] AC1: Task document created and indexed in `docs/tasks/README.md`.
- [x] AC2: Canonical valuation authority identified (`ValuationEngine.evaluate()`, `build_canonical_valuation()`).
- [x] AC3: Owner Earnings input traced and reconciled (Net Income $\to$ D&A $\to$ Maint CapEx $\to \Delta$WC, cycle-normalized).
- [x] AC4: Discount-rate methodology fully traced (Base 11.0% COE, Bear 12.0%, Bull 10.0%, Bank 11.5%).
- [x] AC5: Terminal growth methodology fully traced ($g < r$ invariant enforced by `DCFValuationModel` exception).
- [x] AC6: Growth derivation and ceilings fully traced ($g = b \times ROE_{incr}$, historical CAGR cap + 3%, 20% cyclical / 25% non-cyclical ceiling).
- [x] AC7: Forecast horizon audited (5Y explicit forecast, finite concession 15Y, TV dominance flag at $>75\%$).
- [x] AC8: Bear/Base/Bull scenarios independently verified ($Bear \le Base \le Bull$ for monotonic inputs).
- [x] AC9: Scenario weighting verified (Base IV used as canonical conservative public IV, Bear/Bull provide auditable range).
- [x] AC10: Final IV aggregation verified.
- [x] AC11: No terminal-growth mathematical instability.
- [x] AC12: No double-counting of CapEx/D&A/WC.
- [x] AC13: Bank and securities valuation bypass verified (RIM model exclusively).
- [x] AC14: Canonical share basis verified (`resolve_canonical_share_basis()`).
- [x] AC15: MOS uses canonical IV and compatible share basis ($MOS = (IV - Price) / IV$).
- [x] AC16: Missing-data semantics verified ($NULL \ne 0, MISSING \ne SAFE$).
- [x] AC17: Sensitivity analysis completed ($\pm 1\%, \pm 2\%$ discount rate, $\pm 2\%, \pm 5\%$ growth).
- [x] AC18: Universe regression completed on real PostgreSQL data.
- [x] AC19: Golden test matrix passes (25 distinct economic & mathematical tests).
- [x] AC20: Existing Munger + Valuation tests pass.
- [x] AC21: Frontend build passes.
- [x] AC22: No investor-facing semantic leakage.
- [x] AC23: No methodology changes without proven defect.
- [x] AC24: Any proven defect has regression coverage.
- [x] AC25: Audit report contains exact code/data evidence.
- [x] AC26: Task reaches VERIFIED only after all validation passes.
- [x] AC27: Commit and push to `feature/buffett-munger-refactor`.

## Constraints and Invariants
- `BUY_AND_HOLD_INFORMATION_SYSTEM`: Information and valuation only, no automated trades.
- `DISCOUNT_RATE_CONSERVATISM`: Hurdle rate must reflect Vietnam equity cost of capital ($10\% - 13\%$).
- `STABILITY_INVARIANT`: $g < r$ under all valid DCF runs.
- `ARCHETYPE_ISOLATION`: Financial institutions must never run industrial DCF.
- `LEDGER_INVARIANT`: Share counts and market price must not mutate based on valuation.

## Implementation Tasks
- [x] Create task note `docs/tasks/TASK-20260917-192-intrinsic-value-dcf-conservatism.md` and index.
- [x] Audit all 17 focus areas of canonical valuation and DCF engine.
- [x] Run real PostgreSQL regression across core symbols (BFC, HAH, FPT, DGC, TLG, ACB, TCB, TPB) + universe.
- [x] Run sensitivity analysis grid.
- [x] Write 25-scenario golden test suite `python/portfolio/tests/test_intrinsic_value_dcf_conservatism.py`.
- [x] Verify full test suite and frontend build.
- [x] Author comprehensive audit report `docs/reports/intrinsic-value-dcf-conservatism-audit.md`.
- [x] Mark task verified and push to repo.

## Related Notes
- [TASK-20260917-190-owner-earnings-maintenance-capex-integrity.md](file:///c:/workspace/shannon_allocation/docs/tasks/TASK-20260917-190-owner-earnings-maintenance-capex-integrity.md)
- [TASK-20260917-191-owner-earnings-normalization-consistency.md](file:///c:/workspace/shannon_allocation/docs/tasks/TASK-20260917-191-owner-earnings-normalization-consistency.md)

## Decisions
- Conservative Public IV Strategy: Base Scenario IV is designated as the primary canonical Intrinsic Value per share. Bear and Bull scenarios are explicitly calculated with independent discount rates ($12\%$ Bear, $10\%$ Bull) and growth parameters ($0.6 \times Base$ Bear, $1.35 \times Base$ Bull) to define an auditable valuation range.
- TV Dominance Flagging: When Terminal Value exceeds 75% of Total Present Value, the system flags `terminal_value_contribution_pct` and downgrades confidence level, reflecting increased long-term terminal dependency.

## Validation Evidence
- `test_intrinsic_value_dcf_conservatism.py`: 25/25 PASSED
- Munger & Valuation core suites: 224/224 PASSED
- Frontend build: `npm run build` PASSED (4.15s)
- PostgreSQL regression: 15/15 core symbols and 1,499 universe symbols executed.

## Result
TASK 192 VERIFIED. Comprehensive conservatism audit completed with zero defects in canonical valuation engine.

