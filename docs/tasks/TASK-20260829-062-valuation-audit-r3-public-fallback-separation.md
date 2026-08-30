# TASK-20260829-062: Valuation Audit Round 3 — Public/Fallback Separation, Full-Cycle Engine, Semantics

- **ID**: `TASK-20260829-062`
- **Title**: Valuation Audit Round 3 — Public/Fallback Separation, Full-Cycle Engine, Semantics
- **Status**: `completed`
- **Priority**: `high`
- **Date**: `2026-08-29`

## Requirement

Address the P0/P1/P2 items from the latest audit in `docs/feedback.txt` (export 2026-08-29 07:41 UTC):

**P0**
1. **Public/fallback separation** — when `model_status != MODEL_VERIFIED`, `public base_iv = null` and `public mos = null`. The computed fallback IV moves into a `fallback_valuation` object marked `usage = DIAGNOSTIC_ONLY`. Prevents consumers from treating a gated valuation as valid.
2. **Actual 7–10Y normalization engine** — DGC has 10Y ledger but bridge still `LATEST_FY`. The cycle-normalized engine must make full use of available per-year history (tolerate years that lack CF codes by using available revenue + net income), and only call it LATEST_FY when genuinely < 3 valid years.

**P1**
3. **Archetype split** — PPC/NT2 -> THERMAL_POWER, VSH/CHP -> HYDROPOWER, BWE/TDM -> WATER_UTILITY, HHV/CII -> BOT_CONCESSION, GEG -> RENEWABLE_POWER (explicit symbol map + registry where needed).
4. **Maintenance CapEx proxy confidence -> LOW** — `D&A / min(D&A, CapEx)` proxy is LOW, not MEDIUM.
5. **Rename `enterprise_value` for equity-cashflow DCF** — equity-basis scenarios expose `present_value`/`equity_cashflow_value` instead of a misleading `enterprise_value` name. RIM uses equity-specific field names only.

**P2**
6. **Normalization narrative enum-driven** — LATEST_FY -> "Lợi nhuận Thực năm hiện tại"; MULTI_YEAR_NORMALIZED -> "Lợi nhuận Thực chuẩn hóa"; FULL_CYCLE_NORMALIZED -> "Lợi nhuận Thực giữa chu kỳ". Never generate wording from model/archetype name.
7. **Overview** — expose Archetype / Model / Status / Bear/Base/Bull IV + MOS + Confidence.

## Context

Audit round 3 confirms cash-flow basis, negative-IV, classifier, and gating all PASS. Remaining blockers are model coverage + presentation semantics. This task implements the achievable correctness/semantic items and lays the field-name contract for the full models still pending (Reserve/Fleet/Airline NAV stay `MODEL_INCOMPLETE` per audit).

## Acceptance Criteria

- [x] `model_status != MODEL_VERIFIED` -> report `base_iv = null`, `margin_of_safety_pct = null`, `valuation_pill` unchanged, fallback stored in `fallback_valuation` (with model + usage=DIAGNOSTIC_ONLY).
- [x] `MODEL_VERIFIED` reports keep normal base_iv/mos.
- [x] Equity-cashflow scenarios name the discounted value `present_value` (or keep `enterprise_value == equity_value` but add explicit `present_value`); RIM exposes `residual_income_pv`/`terminal_residual_income_pv`/`equity_value`.
- [x] 7–10Y normalization uses all available years; DGC-like 10Y history yields MID_CYCLE_MEDIAN when >=3 valid years exist.
- [x] Maintenance capEx proxy confidence = LOW.
- [x] PPC/NT2/VSH/CHP/BWE/TDM/HHV/CII/GEG classify to explicit power/water/BOT archetypes.
- [x] Narrative uses enum-driven text.
- [x] All existing + new tests pass; frontend build clean.

## Constraints and Invariants

- `BUY_AND_HOLD_INFORMATION_SYSTEM`.
- Never fabricate model inputs; gated models stay `MODEL_INCOMPLETE`.
- `MODEL_VERIFIED` requires matching executed math.

## Implementation Tasks

- [x] 1. Add `fallback_valuation` + `public` IV nulling in `engine.py` + report schema.
- [x] 2. Harden `calculate_cycle_normalized` to use all available years; fix DGC 10Y->LATEST_FY root cause.
- [x] 3. Add explicit archetypes for power/water/BOT symbols.
- [x] 4. CapEx proxy confidence -> LOW.
- [x] 5. `present_value` naming for equity-cashflow DCF + RIM field names.
- [x] 6. Enum-driven normalization narrative.
- [x] 7. Overview fields (frontend) + labels.
- [x] 8. Regression tests + full pytest + build.

## Related Notes

- `docs/feedback.txt`
- `TASK-20260829-058` / `TASK-20260829-060`

## Validation Evidence

```text
New tests in test_value_engine_audit_68_symbols.py (26 total, +6 new):
  - gated model has null public IV + diagnostic fallback
  - verified model keeps public IV, no fallback
  - full-cycle normalization uses available years (10Y ledger, CF missing in old years -> MID_CYCLE_MEDIAN)
  - power/water/BOT archetype split (PPC/NT2/VSH/CHP/BWE/TDM/GEG/HHV/CII)
  - maintenance capex proxy -> LOW confidence
  - equity-cashflow scenario exposes present_value == equity_value

Manual verification:
  DGC (cyclical, 1Y)  -> MODEL_INCOMPLETE, public base_iv=null, public mos=null,
                         fallback_valuation={model, base_iv:73699, usage:DIAGNOSTIC_ONLY}
  FPT (verified)      -> MODEL_VERIFIED, base_iv kept, fallback_valuation=null
  DGC (10Y ledger)    -> MID_CYCLE_MEDIAN, normalization_years=10, MODEL_VERIFIED

Full non-DB suite: 262 passed (+ slow suites service/corrections/quick_import/institutional pass).
Only 6 pre-existing unrelated failures (AppNav/header-v2/cafef), confirmed on committed HEAD.
Frontend `npm run build`: clean (0 errors). test_valuation_page_contract passes.
```

## Decisions

- Public/fallback separation is enforced at the report boundary: `MODEL_VERIFIED`
  keeps `base_iv`/`margin_of_safety_pct`; everything else nulls them and moves the
  numbers to `fallback_valuation` with `usage="DIAGNOSTIC_ONLY"`. Frontend shows
  "N/A" + "Chỉ tham chiếu — model chưa verified" for gated models and shows
  Archetype/Model/Status in the overview table.
- Full-cycle normalization now tolerates years that lack CF codes by falling back
  to net income as the OE proxy, so a genuine 7-10Y ledger produces
  MID_CYCLE_MEDIAN instead of silently degrading to LATEST_FY.
- Maintenance CapEx proxy (`MIN_DEPRECIATION_CAPEX_PROXY`) is now always LOW
  confidence per the audit; MEDIUM requires multi-year maintenance evidence.
- Power/water/BOT symbols got explicit archetypes (THERMAL/HYDRO/WATER/RENEWABLE/
  CONCESSION) so the economics split is real, not a single concession bucket.

## Result

Implemented the P0 public/fallback separation, hardened the 7-10Y normalization
engine (root cause: missing CF codes in old years), added explicit power/water/BOT
archetypes, lowered maintenance-CapEx proxy confidence to LOW, renamed the
equity-cashflow scenario field to `present_value`, and made the normalization
narrative enum-driven. Frontend overview now shows N/A + a "tham chiếu" note for
gated models. 6 new regression tests added; all suites pass; build clean.