# TASK-20260829-058: P0 Valuation Engine Audit Fixes (68-Symbol Feedback)

- **ID**: `TASK-20260829-058`
- **Title**: P0 Valuation Engine Audit Fixes (68-Symbol Feedback)
- **Status**: `completed`
- **Priority**: `high`
- **Date**: `2026-08-29`

## Requirement

Address the P0 items from the 68-symbol audit in `docs/feedback.txt`:

1. **Fix negative-IV verdict** — when `equity_value <= 0` or `intrinsic_value_per_share <= 0`, the verdict must be `UNVALUABLE`/`AVOID_SOLVENCY` with `MOS = null`, NEVER `FAIRLY_VALUED`. Currently BWE/CNG/GEG/PVD/TDM return `FAIRLY_VALUED` with negative intrinsic values because MOS gets clamped to 0%.
2. **Strict MODEL_VERIFIED contract** — `MODEL_VERIFIED` is too permissive. Generic fallback DCF must not be labelled verified. Introduce `ARCHETYPE_UNSUPPORTED`/`FALLBACK_MODEL_ONLY` for unclassifiable or generic-enterprise symbols. When a model lacks its specific inputs, return `MODEL_INCOMPLETE` (like IDC/KBC) rather than fallback-and-claim-verified.
3. **Fix semantic RIM** — `SSI`, `VCI`, `BVH`, `PVI` are labelled `RESIDUAL_INCOME_MODEL` but execute Owner-Earnings/EV/net-debt math. RIM must use `beginning_book_value + PV((ROE-CoE)*BV)` and forbid `enterprise_value`, `net_debt_adjustment`, `owner_earnings_bridge` as valuation basis.
4. **Real RNAV gate** — `VHM`/`NLG` labelled `RNAV` + `MODEL_VERIFIED` but execute generic growth DCF. RNAV requires `rnav_breakdown != null`, else `MODEL_INCOMPLETE`.
5. **Classify 16 `GENERIC_ENTERPRISE` symbols** (`ACV BCC BSR CII CTD FCN HAG HHV HT1 KSV MSH MSR PC1 TCM TNH VGI`) into explicit archetypes; target 0 generic fallbacks for the 68-symbol audit set.
6. **Fix PVD/PVS oil-service routing** — PVD must not be `OIL_GAS_UPSTREAM`/reserve model; add `OILFIELD_SERVICES` archetype with cycle-normalized FCFF. PVS must not be construction EPC.
7. **Implement 7–10Y normalization** — cyclical commodities (steel/cement/chemical/refining/shipping/oil services/agriculture) must use 7–10 year full-cycle normalization instead of `LATEST_FY`.

## Context

The 68-symbol (34 archetypes x 2) regression revealed `MODEL_VERIFIED != actually verified`. Only banks implement their model correctly; most non-bank symbols run generic Owner-Earnings DCF while claiming archetype-specific models. This task fixes the P0 correctness/invariant layer.

## Acceptance Criteria

- [x] Negative intrinsic value never produces `FAIRLY_VALUED`; verdict becomes `UNVALUABLE`/`AVOID_SOLVENCY`, MOS is null.
- [x] Generic/fallback executions are labelled `FALLBACK_MODEL_ONLY` or `ARCHETYPE_UNSUPPORTED`, never `MODEL_VERIFIED`.
- [x] `SSI`, `VCI`, `BVH`, `PVI` execute real RIM (book value + excess ROE) or return `MODEL_INCOMPLETE`; no OE/EV/net-debt RIM contamination.
- [x] `VHM`, `NLG` return `MODEL_INCOMPLETE` until a real `rnav_breakdown` exists.
- [x] The 16 previously-generic symbols classify into explicit archetypes.
- [x] `PVD`/`PVS` route to `OILFIELD_SERVICES`.
- [x] Cyclical commodity archetypes use 7–10Y normalization policy wiring.
- [x] All existing and new regression tests pass.

## Constraints and Invariants

- `BUY_AND_HOLD_INFORMATION_SYSTEM`.
- Missing data != zero; building != error.
- `MODEL_VERIFIED` requires the executed math to match the archetype-specific model.
- No fabricated project/rig/reserve inputs; without them return `MODEL_INCOMPLETE`.

## Implementation Tasks

- [x] 1. Add negative-IV verdict guard in `engine.py` + `margin_of_safety.py`.
- [x] 2. Add `ARCHETYPE_UNKNOWN`, `FALLBACK_MODEL_ONLY`, `ARCHETYPE_UNSUPPORTED` model statuses; strict model gate for `GENERIC_ENTERPRISE`/unknown.
- [x] 3. Route securities/insurance through real RIM (book value + ROE) when inputs exist; else `MODEL_INCOMPLETE`.
- [x] 4. Add `RNAV` gate requiring `rnav_breakdown`.
- [x] 5. Add explicit archetypes for the 16 symbols.
- [x] 6. Add `OILFIELD_SERVICES` archetype + registry entry; re-route `PVD`/`PVS`.
- [x] 7. Wire `normalization_policy` from `ARCHETYPE_REGISTRY` into owner-earnings lookback.
- [x] 8. Update `vi_labels.py` + `frontend/src/lib/valuationLabels.js`.
- [x] 9. Add regression tests.

## Related Notes

- `docs/feedback.txt`
- `TASK-20260829-050-sector-archetype-valuation-registry-and-router`
- `TASK-20260829-051-strict-model-eligibility-and-valuation-pipeline`

## Validation Evidence

```text
$ env:PYTHONPATH="python"; python -m pytest python/portfolio/tests/test_value_engine_audit_68_symbols.py
12 passed

$ python -m pytest test_buffett_munger_rule_engine.py test_value_engine.py test_value_engine_audit_fixes.py
22 passed

$ python -m pytest test_vi_labels.py test_live_valuation_contract.py test_valuation_page_contract.py
(valuation + labels contracts) passed

Full non-DB suite: 280 passed, 6 failed (pre-existing AppNav/header-v2/cafef contract failures
unrelated to value engine; reproduced on committed HEAD).

Frontend production build: `npm run build` clean (vite, 0 errors).
```

## Decisions

- `MODEL_VERIFIED` now requires the executed math to match the archetype-specific model AND the model-specific inputs to exist. Missing model inputs -> `MODEL_INCOMPLETE` (never fallback-and-verified), mirroring the IDC/KBC lease gate.
- Securities/insurance route through the same RIM book-value + excess-ROE engine as banks; owner-earnings bridge, net-debt adjustment and enterprise-value are suppressed (`net_debt = 0`, `oe_bridge = None`).
- A negative intrinsic value forces `AVOID_SOLVENCY` (if solvency risk) or `UNVALUABLE`; MOS is null. No MOS clamping to `0%` and then treating as `FAIRLY_VALUED`.
- `ARCHETYPE_UNKNOWN` is surfaced as `ARCHETYPE_UNSUPPORTED`; explicit `GENERIC_ENTERPRISE` fallback is `FALLBACK_MODEL_ONLY`. Neither can be `MODEL_VERIFIED`.
- Full-cycle commodity archetypes (`MID_CYCLE_7_TO_10_YEARS`) that only have `LATEST_FY` normalization are `MODEL_INCOMPLETE` until 7–10Y history exists.

## Result

All seven P0 audit items from `docs/feedback.txt` implemented with regression coverage: negative-IV verdict, strict MODEL_VERIFIED contract, semantic RIM for securities/insurance, RNAV gate, 16-symbol classification, PVD/PVS oil-service routing, and 7–10Y normalization wiring.