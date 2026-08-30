# TASK-20260829-064: Remaining Audit R3 Items — ACV concession gate + full Overview

- **ID**: `TASK-20260829-064`
- **Title**: Remaining Audit R3 Items — ACV concession gate + full Overview
- **Status**: `completed`
- **Priority**: `high`
- **Date**: `2026-08-29`

## Requirement

Finish the two audit-round-3 items from `docs/feedback.txt` that TASK-062 did not cover:

1. **ACV concession duration must be sourced (#12)** — the airport model runs a 15-year
   finite concession with TV=0 from a default config. The export does not show
   evidence that 15 years is the remaining economic/concession life
   (`concession_end_date`, `remaining_years`, traffic/fee assumptions). If 15 years
   is only a default, `MODEL_ESTIMATED` is more honest than `MODEL_VERIFIED`.
   Add a gate: CONCESSION_DCF for AIRPORT_INFRASTRUCTURE without sourced concession
   evidence -> `MODEL_ESTIMATED` (not VERIFIED).

2. **Overview UX (#13)** — the overview table should expose the full contract:
   Ticker | Archetype | Model | Status | Price | Bear IV | Base IV | Bull IV |
   MOS | Required MOS | Confidence. For `MODEL_INCOMPLETE`/`MODEL_PARTIAL`,
   Base IV / MOS show N/A (never the fallback number as primary).

## Context

TASK-062 implemented public/fallback separation, present_value, capex LOW, power/water
split, enum narrative. The two items above remain.

## Acceptance Criteria

- [x] AIRPORT_INFRASTRUCTURE + CONCESSION_DCF with no sourced concession evidence -> `MODEL_ESTIMATED`.
- [x] Other concession archetypes (BOT, utility, power) keep existing behavior unless
      evidence indicates otherwise.
- [x] Overview table adds Bear IV / Bull IV / Required MOS / Confidence columns.
- [x] Gated models still show N/A for Base IV / MOS in overview.
- [x] All value-engine tests pass; frontend build clean.

## Constraints and Invariants

- `BUY_AND_HOLD_INFORMATION_SYSTEM`.
- Never invent concession duration evidence; gate instead.
- Keep pure-Vietnamese narrative contract (`test_valuation_page_contract`).

## Implementation Tasks

- [x] 1. Add `MODEL_ESTIMATED` handling for unsourced airport concession.
- [x] 2. Expand `ValuationOverviewTable` columns.
- [x] 3. Regression tests + build.

## Related Notes

- `docs/feedback.txt` (#12, #13)
- `python/portfolio/value_engine/engine.py`
- `frontend/src/pages/ValuationPage.jsx`

## Validation Evidence

```text
$ npm run build -> clean
$ pytest test_buffett_munger_rule_engine.py test_value_engine.py \
    test_value_engine_audit_fixes.py test_value_engine_audit_68_symbols.py \
    test_vi_labels.py test_valuation_page_contract.py -> 56 passed
New tests: ACV no-duration -> MODEL_ESTIMATED + fallback; ACV sourced -> VERIFIED;
          GAS unaffected -> VERIFIED (29 total in audit_68 file, +3 new)
Full non-DB suite: 265 passed; only 6 pre-existing unrelated failures.

Manual verification:
  ACV (no concession_end_date) -> model_status=MODEL_ESTIMATED, fallback=True
  ACV (concession_end_date=2045-12-31) -> MODEL_VERIFIED
  GAS (utility concession) -> MODEL_VERIFIED (gate is airport-specific)
```

## Decisions

- The 15-year airport concession is a default config, not sourced evidence. Until
  `concession_end_date`/`remaining_years`/traffic/fee assumptions are provided the
  model is `MODEL_ESTIMATED` (kept visible with the fallback for audit, but never
  `MODEL_VERIFIED`). Supplying `concession_end_date` in fundamentals restores
  `MODEL_VERIFIED`.
- Overview table now exposes the full contract: Bear/Base/Bull IV, MOS, Required
  MOS, and Confidence, matching the audit's proposed schema. Gated models show N/A
  for IV/MOS (never the fallback number as primary).

## Result

Both remaining audit-round-3 items are done: unsourced airport concession duration
now yields `MODEL_ESTIMATED` instead of a misleading `MODEL_VERIFIED`, and the
valuation overview exposes the full Bear/Base/Bull IV + MOS + Required MOS +
Confidence contract with N/A for gated models. Tests and build are clean.

Follow-up (same feedback round, #1/#8): RIM scenarios now expose the equity-specific
`present_value` field (== equity_value) in addition to the backward-compat
`enterprise_value` alias, so downstream consumers can rely on equity-specific naming
for RESIDUAL_INCOME models. Regression test added (30 total in audit_68 file).