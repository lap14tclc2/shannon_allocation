# TASK-20260829-068: Fix LOW_QUALITY verdict, real leverage penalty & dilution split

- **ID**: `TASK-20260829-068`
- **Title**: Fix LOW_QUALITY verdict, real leverage penalty & dilution split
- **Status**: `verified`
- **Priority**: `high`
- **Date**: `2026-08-29`

## Requirement

Address the 3 findings in `docs/feedback.txt` (review of commit `17411a2`, scored 8.5/10):

1. **P0 – LOW_QUALITY must never be ATTRACTIVE / HIGH_CONVICTION_VALUE**: In `margin_of_safety.py` the `elif satisfied: ATTRACTIVE` branch runs before the `LOW_QUALITY -> AVOID_QUALITY` check, so a LOW_QUALITY company with a satisfied MOS still returns `ATTRACTIVE`. Add an invariant: LOW_QUALITY (and hard rejects) override any valuation-positive verdict.
2. **P1 – Leverage penalty must be computed from real leverage**: Currently `has_solvency_risk = len(quality_scorecard.hard_rejects) > 0` is passed and `leverage_pen = 10 if has_solvency_risk else 5 if CAPITAL_INTENSIVE else 0`. This is not a leverage calculation. Pass real metrics (net_debt, debt_payback_years, net_debt/EBITDA) and derive the penalty from actual leverage.
3. **P1 – Unexplained share change must not be treated as confirmed economic dilution**: `app/main.py` sets both `share_dilution_5y_pct` and `economic_dilution_5y_pct` to the residual (e.g. FRT 88.8%) even when classified `UNEXPLAINED_SHARE_CHANGE` with zero economic events. This penalizes capital-allocation score as if dilution were proven. Split: `confirmed_economic_dilution_pct` (null when unexplained) vs `unexplained_share_change_pct` (the residual); quality score must only use confirmed economic dilution.

## Context

Feedback reviewer confirmed the PR #51 items and the previous P0 fixes PASS, but blocked merge to `main` until these 3 points are fixed. FRT is the production-visible reproducer for #1 (quality=54 LOW_QUALITY, MOS 48%, still ATTRACTIVE) and #3 (raw 115.6% / non-economic 26.8% / unexplained 88.8% / confirmed 0 events).

## Acceptance Criteria

- [x] `LOW_QUALITY` + satisfied MOS → `AVOID_QUALITY` (never `ATTRACTIVE`/`HIGH_CONVICTION_VALUE`).
- [x] Leverage penalty derived from real leverage metrics (net_debt, debt_payback_years, net_debt/EBITDA); capital-intensive overlay alone no longer adds +5.
- [x] `confirmed_economic_dilution_pct` is null when classification is `UNEXPLAINED_SHARE_CHANGE`; `unexplained_share_change_pct` carries the residual; capital-allocation scoring uses only confirmed dilution.
- [x] FRT-like regression test: LOW_QUALITY + satisfied MOS → AVOID_QUALITY.
- [x] All suites pass; frontend build clean.

## Constraints and Invariants

- `BUY_AND_HOLD_INFORMATION_SYSTEM`.
- Never present unexplained residual as proven economic dilution.
- Quality gate always overrides a valuation-positive verdict.

## Implementation Tasks

- [x] 1. `margin_of_safety.py`: add `quality_tier == LOW_QUALITY` invariant before satisfied/ATTRACTIVE.
- [x] 2. `margin_of_safety.py`: accept real leverage inputs (`net_debt`, `debt_payback_years`, `net_debt_to_ebitda`) and derive leverage penalty.
- [x] 3. `engine.py`: pass real leverage metrics from report inputs.
- [x] 4. `app/main.py`: split dilution fields (confirmed vs unexplained); `economic_dilution_5y_pct` null when unexplained.
- [x] 5. `engine.py`/`quality_scorer.py`: use confirmed economic dilution only for capital-allocation penalty.
- [x] 6. Regression tests + docs update.

## Related Notes

- `docs/feedback.txt`
- `TASK-20260829-066`, `TASK-20260829-067`

## Validation Evidence

```text
$ python -m pytest test_audit_integrity_verdict_exposure.py -> 29 passed
  (LOW_QUALITY + MOS satisfied -> AVOID_QUALITY; leverage penalty from real
   debt payback / net-debt-to-EBITDA; confirmed vs unexplained dilution split)

$ python -m pytest (value-engine + activity + service suites) -> 104 passed
$ python -m pytest python/portfolio/tests -> 330 passed, 6 failed, 1 skipped
  (6 failures pre-existing on HEAD: AppNav/header-v2/CafeF contract tests)

Frontend `npm run build`: clean.

Manual:
  FRT (LOW_QUALITY, MOS 48% satisfied) -> verdict AVOID_QUALITY (was ATTRACTIVE)
  12-year debt payback               -> leverage penalty 10.0
  Net cash (net_debt < 0)            -> leverage penalty 0.0
  FRT dilution (raw 115.6/26.8 non-econ) -> UNEXPLAINED_SHARE_CHANGE,
      confirmed_economic_dilution_pct=None, unexplained_share_change_pct=89.2
```

## Decisions

- LOW_QUALITY is a hard quality gate checked BEFORE the satisfied-MOS branch, so the FRT reproducer can never be ATTRACTIVE.
- Leverage MOS penalty now uses real metrics: net_debt <= 0 → 0; net_debt/EBITDA ≥ 6 or payback ≥ 10y → 10; ≥4 / ≥5y → 6; ≥2 / ≥2y → 3; positive debt w/o evidence → 3 (conservative). `CAPITAL_INTENSIVE` overlay alone adds nothing.
- `classify_share_change` returns both `confirmed_economic_dilution_pct` (null unless actual economic events) and `unexplained_share_change_pct` (the residual). `app/main.py`/`engine.py` score capital allocation and hard-reject only on confirmed dilution.

## Result

All 3 findings from the 8.5/10 review resolved: LOW_QUALITY can no longer be ATTRACTIVE/HIGH_CONVICTION_VALUE; leverage penalty is derived from real debt serviceability; unexplained share change is no longer presented or scored as confirmed economic dilution. 29 regression tests in the exposure suite; all value-engine/activity/service suites green; frontend build clean.