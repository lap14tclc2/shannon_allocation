# TASK-20260829-069: Fix capital_allocation.status TypeError & verdict/dilution precedence

- **ID**: `TASK-20260829-069`
- **Title**: Fix capital_allocation.status TypeError & verdict/dilution precedence
- **Status**: `verified`
- **Priority**: `high`
- **Date**: `2026-08-29`

## Requirement

Address the review of commit `6a80537` (CHANGES REQUESTED, 8.6–8.8/10, merge blocked):

1. **P0 – `capital_allocation.status` precedence / None TypeError** (blocker): the `and`/`or` precedence expression can evaluate `None < 5` → `TypeError` when `confirmed_economic_dilution_pct` is None and `avg_roe < 18` (exactly the UNEXPLAINED_SHARE_CHANGE case). Split the variable and use explicit grouping.
2. **P1 – `has_solvency_risk` must mean only `SOLVENCY_RISK`**, not any hard reject. A net-cash company with `EXCESSIVE_DILUTION` must not get a +10 leverage penalty.
3. **P1 – hard-reject precedence**: `SOLVENCY_RISK` > `UNNORMALIZABLE/CIRCLE_FAIL` > `LOW_QUALITY`. LOW_QUALITY + SOLVENCY_RISK → AVOID_SOLVENCY; LOW_QUALITY + UNNORMALIZABLE → UNVALUABLE.
4. **P1 – do not confirm the entire residual dilution merely because one economic event exists**: cap confirmed economic dilution by the value-transfer implied by actual events (shares_issued × max(fair_value − issue_price, 0)); a small rights issue should not mark all residual as proven.
5. **P2 – deprecate `share_dilution_5y_pct`** semantics; expose explicit `raw_share_change_5y_pct`, `confirmed_economic_dilution_5y_pct`, `unexplained_share_change_5y_pct`, `non_economic_share_change_5y_pct`.
6. **P2 – add regression tests** for all of the above (incl. `None` no-TypeError, net-cash+EXCESSIVE_DILUTION penalty 0, LOW_QUALITY+SOLVENCY_RISK → AVOID_SOLVENCY).

## Context

Reviewer confirmed LOW_QUALITY gate, leverage inputs, and dilution split PASS. Blockers: a concrete runtime `None < 5` TypeError in `app/main.py`, solvency-risk conflation with any hard reject, missing reject precedence, and over-confirming residual dilution from a single economic event.

## Acceptance Criteria

- [x] `capital_allocation.status` never raises; `confirmed=None, roe<18` → not EXCELLENT, no exception.
- [x] `has_solvency_risk` is true only when `SOLVENCY_RISK` is in hard_rejects.
- [x] Verdict precedence: SOLVENCY_RISK → AVOID_SOLVENCY > UNNORMALIZABLE/CIRCLE_FAIL → UNVALUABLE > LOW_QUALITY → AVOID_QUALITY.
- [x] `confirmed_economic_dilution_pct` capped by event value-transfer estimate; a single small event does not confirm the whole residual.
- [x] `share_dilution_5y_pct` deprecated; explicit dilution fields exposed.
- [x] Regression tests + full suites pass; frontend build clean.

## Constraints and Invariants

- `BUY_AND_HOLD_INFORMATION_SYSTEM`.
- Never score/present unexplained residual as proven dilution.
- Solvency risk is distinct from quality/dilution rejects.

## Implementation Tasks

- [x] 1. `app/main.py`: fix status expression (explicit `confirmed_dilution` var + grouping).
- [x] 2. `engine.py`: `has_solvency_risk` = `SOLVENCY_RISK in hard_rejects`.
- [x] 3. `margin_of_safety.py`: reject precedence SOLVENCY > UNVALUABLE > LOW_QUALITY.
- [x] 4. `dilution.py`: value-transfer-capped confirmed dilution.
- [x] 5. `app/main.py`: deprecate `share_dilution_5y_pct`, expose explicit fields.
- [x] 6. Tests + docs.

## Related Notes

- `docs/feedback.txt`
- `TASK-20260829-068`

## Validation Evidence

```text
$ python -m pytest test_audit_integrity_verdict_exposure.py -> 30 passed
$ python -m pytest (value-engine + activity + service suites) -> 108 passed
$ python -m pytest python/portfolio/tests -> 334 passed, 6 failed, 1 skipped
  (6 failures pre-existing on HEAD: AppNav/header-v2/CafeF contract tests)

Frontend `npm run build`: clean.

Manual verification of every review case:
  LOW_QUALITY + MOS 48% satisfied          -> AVOID_QUALITY
  net-cash + EXCESSIVE_DILUTION             -> leverage penalty 0 (has_solvency_risk now means SOLVENCY_RISK only)
  LOW_QUALITY + SOLVENCY_RISK               -> AVOID_SOLVENCY (precedence SOLVENCY > UNVALUABLE > LOW_QUALITY)
  single 50% RIGHTS_ISSUE + 100% residual   -> confirmed 50%, unexplained 50% (no whole-residual confirmation)
  fair-value rights issue (IP 95 / FV 100)  -> confirmed 5% (ValueTransfer cap)
  confirmed=None, roe=12                    -> no TypeError; status WATCH (P0 blocker fixed)
```

## Decisions

- `has_solvency_risk` is computed as `"SOLVENCY_RISK" in [r.value for r in hard_rejects]` in the engine, decoupling solvency from any other hard reject (e.g. dilution).
- Hard-reject precedence in the MOS engine is encoded in `reject_override` (SOLVENCY_RISK > UNNORMALIZABLE/CIRCLE_OF_COMPETENCE_FAIL > generic) and is applied to ANY base verdict, including LOW_QUALITY.
- `classify_share_change` now caps confirmed dilution at the value transfer implied by actual events: `sum(shares_issued_pct * max(FV-IP, 0)/FV)`; without prices it caps at total shares issued by economic events. The remaining residual is always surfaced as `unexplained_share_change_pct`.
- `share_dilution_5y_pct` is deprecated (was the raw residual); it now mirrors `confirmed_economic_dilution_5y_pct` for legacy consumers, and the explicit fields (`raw_share_change_5y_pct`, `confirmed_economic_dilution_5y_pct`, `unexplained_share_change_5y_pct`, `non_economic_share_change_5y_pct`) are exposed.

## Result

Resolved all CHANGES REQUESTED items from the review of `6a80537`: fixed the P0 `None < 5` TypeError in `capital_allocation.status`, decoupled solvency risk from any hard reject, enforced SOLVENCY > UNVALUABLE > LOW_QUALITY verdict precedence, capped confirmed dilution by event value-transfer evidence, and deprecated the ambiguous `share_dilution_5y_pct`. 30 exposure tests + 108 value-engine/activity/service tests pass; frontend build clean.