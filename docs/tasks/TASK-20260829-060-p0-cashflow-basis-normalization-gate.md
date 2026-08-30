# TASK-20260829-060: P0 Cashflow-Basis Invariant, Normalization Gate & Model-Coverage Gaps

- **ID**: `TASK-20260829-060`
- **Title**: P0 Cashflow-Basis Invariant, Normalization Gate & Model-Coverage Gaps
- **Status**: `completed`
- **Priority**: `high`
- **Date**: `2026-08-29`

## Requirement

Address the P0 items from the latest audit in `docs/feedback.txt` (export 2026-08-29 06:17 UTC):

1. **Cashflow-basis invariant (biggest P0)** — NI-based Owner Earnings is an *equity* cash flow (after interest). It must discount at Cost of Equity to Equity Value directly, with NO net-debt adjustment. FCFF must discount at WACC to Enterprise Value, then subtract net debt. Prevent debt double-counting. Mandatory scenario schema: `cashflow_basis`, `discount_rate_basis`, `result_type`, `debt_adjustment_policy`.
2. **Normalization gate consistency** — `HIGH_CYCLICALITY + COMMODITY_EXPOSED` requires >= 7Y full-cycle normalization (prefer 10Y). DGC cannot be `MODEL_VERIFIED` with `LATEST_FY`. HT1 cannot be `MODEL_VERIFIED` with only 3Y mid-cycle -> `MODEL_PARTIAL`. Applied to DGC/DCM/HPG/HSG/BCC/HT1/BSR/PLX/HAH/VHC/FMC/PVD/PVS.
3. **Model coverage** — `MINING_RESOURCE` -> Reserve/Resource NAV; `SHIPPING` -> Fleet NAV + mid-cycle; `AIRLINE` -> lease-adjusted EBITDAR. Without those specialized inputs -> `MODEL_INCOMPLETE` (never generic OE DCF verified).
4. **Classifier regression** — VOS -> SHIPPING (was LOGISTICS_SERVICES). Split power/water over-generalization into THERMAL/HYDRO/RENEWABLE/WATER_UTILITY/CONCESSION.
5. **Narrative invariant** — `LATEST_FY` must never be presented as "mid-cycle".

## Context

Previous round (task 058) fixed negative-IV, generic classification, RIM, RNAV gate. This round the auditor raised engine readiness from 7/10 to 8.1-8.3/10 and names cashflow-basis consistency, full-cycle normalization, and mining/shipping/airline model coverage as the path to ~9/10.

## Acceptance Criteria

- [x] Every `ValuationScenario` carries `cashflow_basis`, `discount_rate_basis`, `result_type`, `debt_adjustment_policy`.
- [x] NI-based OE DCF produces `EQUITY_VALUE` with `NO_NET_DEBT_ADJUSTMENT`; enterprise_value == equity_value (no double count).
- [x] Concession/FCFF models declare `ENTERPRISE_VALUE` + `SUBTRACT_NET_DEBT`; RIM declares `RESIDUAL_INCOME` equity basis with net_debt = 0.
- [x] DGC (cyclical+commodity, LATEST_FY) is not `MODEL_VERIFIED`.
- [x] HT1 (3Y mid-cycle) is `MODEL_PARTIAL`.
- [x] KSV/MSR -> MINING_RESOURCE `RESERVE_NAV`; HAH/VOS -> SHIPPING `FLEET_NAV`; VJC/HVN -> AIRLINE `AIRLINE_EBITDAR`; without inputs -> `MODEL_INCOMPLETE`.
- [x] VOS classifies as SHIPPING.
- [x] `LATEST_FY` narrative shows "Lợi nhuận Thực hiện tại (LATEST_FY)", never "giữa chu kỳ".
- [x] All existing + new regression tests pass; frontend build clean.

## Constraints and Invariants

- `BUY_AND_HOLD_INFORMATION_SYSTEM`.
- Never fabricate reserve/fleet/airline inputs; return `MODEL_INCOMPLETE` when absent.
- `MODEL_VERIFIED` only when the executed math matches the archetype-specific model.

## Implementation Tasks

- [x] 1. Add cashflow-basis schema to `ValuationScenario` + model enum statuses (`MODEL_PARTIAL`).
- [x] 2. DCF model: equity basis for NI-based OE (enterprise == equity, no net-debt adjustment); FCFF branch declared.
- [x] 3. Concession, Lease, SOTP, RIM models declare their basis honestly.
- [x] 4. Registry: MINING/SHIPPING/AIRLINE primary models = RESERVE_NAV/FLEET_NAV/AIRLINE_EBITDAR with required fields.
- [x] 5. Classifier: VOS->SHIPPING, VJC/HVN->AIRLINE_EBITDAR, power/water split.
- [x] 6. Engine: overlay-driven full-cycle normalization gate (>=7Y), `MODEL_PARTIAL` for shallow mid-cycle.
- [x] 7. Narrative invariant: dynamic model label for LATEST_FY.
- [x] 8. Labels: `vi_labels.py` + `frontend/src/lib/valuationLabels.js` for new models/statuses.
- [x] 9. Regression tests in `test_value_engine_audit_68_symbols.py`.

## Related Notes

- `docs/feedback.txt` (latest audit)
- `TASK-20260829-058-p0-valuation-engine-audit-fixes`

## Validation Evidence

```text
$ python -m pytest test_value_engine_audit_68_symbols.py -> 20 passed
$ python -m pytest test_buffett_munger_rule_engine.py test_value_engine.py \
    test_value_engine_audit_fixes.py test_vi_labels.py test_valuation_page_contract.py \
    test_live_valuation_contract.py -> 53 passed
Full non-DB suite: 289 passed, 6 failed (pre-existing AppNav/header-v2/cafef contract
failures unrelated to value engine; reproduced on committed HEAD).
Frontend `npm run build`: clean (0 errors).

Manual verification:
  DGC (cyclical+commodity, 1Y)      -> MODEL_INCOMPLETE (was MODEL_VERIFIED)
  HT1 (cement, 3Y mid-cycle)        -> MODEL_PARTIAL
  KSV/MSR mining                    -> MODEL_INCOMPLETE (RESERVE_NAV required)
  HAH/VOS shipping                  -> MODEL_INCOMPLETE (FLEET_NAV required)
  VJC/HVN airline                   -> MODEL_INCOMPLETE (AIRLINE_EBITDAR required)
  PVD/PVS oil services              -> MODEL_INCOMPLETE (MID_CYCLE_FCFF required)
  Generic DCF (FPT)                 -> cashflow_basis=NET_INCOME_OWNER_EARNINGS,
                                       result_type=EQUITY_VALUE,
                                       debt_adjustment_policy=NO_NET_DEBT_ADJUSTMENT,
                                       enterprise_value == equity_value
  LATEST_FY narrative               -> "Lợi nhuận Thực hiện tại (LATEST_FY)"
```

## Decisions

- NI-based Owner Earnings is declared `NET_INCOME_OWNER_EARNINGS` / `COST_OF_EQUITY` / `EQUITY_VALUE` / `NO_NET_DEBT_ADJUSTMENT`; the DCF no longer inflates `enterprise_value` by net debt, eliminating the double-count the auditor flagged.
- Concession and Industrial-RE (KCN) cash flows are declared FCFF/enterprise basis (they genuinely subtract project net debt). RIM is declared equity basis with net_debt = 0.
- Full-cycle normalization gate is now driven by OVERLAYS (`HIGH_CYCLICALITY + COMMODITY_EXPOSED`), not only the registry `normalization_policy`, so DGC/DCM/HPG/etc. can no longer escape via LATEST_FY. Shallow mid-cycle (< 7Y) yields the new `MODEL_PARTIAL` status (HT1).
- MINING/SHIPPING/AIRLINE declare specialized primary models (`RESERVE_NAV`, `FLEET_NAV`, `AIRLINE_EBITDAR`). Until those inputs exist the engine returns `MODEL_INCOMPLETE`, exactly like the IDC/KBC/RNAV gates.

## Result

Implemented all P0 items from the latest audit: cashflow-basis invariant schema, overlay-driven full-cycle normalization gate with `MODEL_PARTIAL`, and model-coverage gates for mining/shipping/airline. 20 new regression tests added; all value-engine/valuation suites pass; frontend build clean.