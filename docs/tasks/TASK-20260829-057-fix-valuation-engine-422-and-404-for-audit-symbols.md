# TASK-20260829-057: Fix Valuation Engine 422 (Owner Earnings Non-Positive) & 404 (Missing Documents)

- **ID**: `TASK-20260829-057`
- **Title**: Fix Valuation Engine 422 (Owner Earnings Non-Positive) & 404 (Missing Documents)
- **Status**: `completed`
- **Priority**: `high`
- **Date**: `2026-08-29`

## Requirement
1. Resolve 404 (`FINANCE_DATA_NOT_READY`) errors for `HT1`, `NT2`, `PC1`:
   - Ingest offline TCBS financial files from `docs/crawled/` into `qport_finance.documents` and `canonical_facts`.
2. Resolve 422 (`OWNER_EARNINGS_NON_POSITIVE`) errors for `BAF`, `CII`, `CTD`, `DCM`, `FCN`, `HAX`, `KBC`, `PNJ`, `TNH`, `VOS`:
   - **Multi-Year History Fact Ingestion**: Ensure `app/main.py` passes historical canonical facts to `ValuationEngine` so `OwnerEarningsCalculator.calculate_cycle_normalized` can perform true 5-10 year median normalization.
   - **Buffett Owner Earnings Standard Formulation**: In single-year calculations, separate Core Owner Earnings ($\text{Net Income} + \text{D&A} - \text{Maintenance CapEx}$) from temporary single-year Working Capital fluctuations ($\Delta\text{WC}$), preventing profitable enterprises (e.g. PNJ with 2,828B profit, DCM with 1,962B profit) from being blocked due to seasonal inventory build.
   - **Graceful Unvaluable / Distressed Handling**: When an enterprise is fundamentally unprofitable ($\text{Owner Earnings} \le 0$), do not raise unhandled HTTP 422 exceptions. Return a structured valuation report with `valuation_status: UNVALUABLE` / `DISTRESSED`, `model_status: MODEL_UNVALUABLE`, and explicit Buffett reasoning in the UI.

## Acceptance Criteria
- [x] `HT1`, `NT2`, `PC1` documents and canonical facts imported from `docs/crawled/`; 404 eliminated.
- [x] `BAF`, `CII`, `CTD`, `DCM`, `FCN`, `HAX`, `KBC`, `PNJ`, `TNH`, `VOS` return HTTP 200 with valid valuation reports (or clear `UNVALUABLE` status).
- [x] Multi-year historical facts passed into `ValuationEngine` in `app/main.py`.
- [x] No stock in the 34 archetypes universe throws 422 or 404 on `/api/portfolio/valuation/<SYMBOL>`.
- [x] All unit and contract tests pass.

## Constraints and Invariants
- `BUY_AND_HOLD_INFORMATION_SYSTEM`.
- Real data only; no synthetic or unverified numbers.

## Implementation Tasks
- [x] 1. Run TCBS crawler import on `docs/crawled` for `HT1`, `NT2`, `PC1`.
- [x] 2. Update `app/main.py` to ingest multi-year canonical facts into `facts` list passed to `ValuationEngine`.
- [x] 3. Refine `OwnerEarningsCalculator` in `python/portfolio/value_engine/owner_earnings.py` to support core OE when single-year working capital is distorted, and true mid-cycle normalization.
- [x] 4. Update `ValuationEngine` in `python/portfolio/value_engine/engine.py` to return graceful unvaluable report instead of throwing unhandled ValueError on negative OE.
- [x] 5. Verify all 68 symbols in the 34 archetypes universe return HTTP 200 without errors.

## Validation Evidence
- Evaluated all 68 symbols in the 34 archetypes universe: `Total: 68, Success: 68, Failed: 0`.
- All 22 value engine unit tests passed cleanly (`pytest python/portfolio/tests/test_buffett_munger_rule_engine.py python/portfolio/tests/test_value_engine.py python/portfolio/tests/test_value_engine_audit_fixes.py`).
- Frontend production bundle build (`npm run build`) completed cleanly with 0 errors.

## Decisions
- For profitable compounders with single-year working capital expansion (inventory/construction progress, e.g. PNJ, DCM, CTD), Core Owner Earnings ($\text{Net Income} + \text{D&A} - \text{CapEx}_{\text{maint}}$) provides the steady-state earning power baseline rather than false-negative DCF blockage.
- When an enterprise is fundamentally unprofitable ($\text{Owner Earnings} \le 0$), return a valid valuation report with `ValuationPill.UNVALUABLE` / `MODEL_UNVALUABLE` and explicit narrative explanation rather than raising HTTP 422.

## Result
All 13 error symbols (`HT1`, `NT2`, `PC1`, `BAF`, `CII`, `CTD`, `DCM`, `FCN`, `HAX`, `KBC`, `PNJ`, `TNH`, `VOS`) and all 68 symbols across 34 archetypes evaluate cleanly with HTTP 200.
