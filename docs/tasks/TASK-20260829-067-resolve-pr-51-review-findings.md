# TASK-20260829-067: Resolve PR #51 REVIEW(P0/P1) findings on dev

- **ID**: `TASK-20260829-067`
- **Title**: Resolve PR #51 REVIEW(P0/P1) findings on dev
- **Status**: `verified`
- **Priority**: `high`
- **Date**: `2026-08-29`

## Requirement

Check PR https://github.com/lap14tclc2/shannon_allocation/pull/51 (branch `review/dev-code-feedback-20260829`) and fix the `REVIEW(P0/P1)` findings in the reviewed `dev` branch.

The review annotated 5 files on an OLD dev commit (`fdb61bd`), before the P0 audit fixes (task 065/066). Findings and disposition:

| # | File | Level | Finding | Disposition on current dev |
|---|------|-------|---------|----------------------------|
| 1 | `value_engine/dcf.py` | P0 | NI-based Owner Earnings is equity cash flow; subtracting net debt double-counts financing | **Already fixed** — `is_equity_cash_flow` → `NO_NET_DEBT_ADJUSTMENT`; FCFF branch subtracts debt once; `cashflow_basis`/`discount_rate_basis`/`result_type`/`debt_adjustment_policy` declared |
| 2 | `value_engine/engine.py` | P0 | `entity_type` not used to route to archetype models | **Already fixed** — `ArchetypeClassifier` routes to specialized models; missing inputs → `MODEL_INCOMPLETE` |
| 2 | `value_engine/engine.py` | P1 | Hard-coded Bear/Base/Bull growth (8/14/20%) | **Already fixed** — `_derive_growth` uses history + reinvestment/incremental returns; archetype caps; 7-10Y full-cycle gate |
| 3 | `value_engine/engine.py` | P0 | Final pill based only on price vs IV, no quality/hard-reject override | **Already fixed** — `MarginOfSafetyEngine` receives `hard_rejects`; verdict never `ATTRACTIVE`/`HIGH_CONVICTION_VALUE` when rejects exist |
| 4 | `activity.py` | P0 | read-head-then-insert not serialized → sibling rows share prev_hash | **Already fixed** — `_append_lock` + `BEGIN IMMEDIATE` (SQLite) / `pg_advisory_xact_lock` (Postgres) |
| 5 | `activity.py` | P1 | no idempotency key → duplicate logical events | **Already fixed** — `idempotency_key` column + UNIQUE partial index; AI_EXPORT dedupe |
| 6 | `correctable_service.py` | P0 | AI_EXPORT write side-effect on read-only export | **Already fixed** — frontend export no longer POSTs AI_EXPORT; `log_client_activity` idempotent |
| 7 | `tests/test_value_engine.py` | P0 | missing debt double-count invariant test | **Already fixed** — `test_generic_oe_dcf_is_equity_cash_flow_no_debt_adjustment` |
| 8 | `activity.py` | P1 | `verify_activity_chain` lacks forensic evidence | **Fixed in this task** — added `failure` (`PREV_HASH_MISMATCH` vs `CURRENT_HASH_MISMATCH`), `expected_prev_hash`, `actual_prev_hash`, `expected_hash`, `actual_hash`, `previous_good_id` |

## Context

PR #51 review base is `dev` at `fdb61bd` (102 commits behind `main`), written before tasks 065/066 landed the P0 audit fixes. Current `dev` HEAD (`f08e7c5`) already satisfies 7 of the 8 findings. Item 8 (forensic detail in `verify_activity_chain`) needed enhancement, plus the review's exact net-debt invariance test was added.

## Acceptance Criteria

- [x] All `REVIEW(P0)` items from PR #51 resolved in current dev.
- [x] All `REVIEW(P1)` items from PR #51 resolved in current dev.
- [x] `verify_activity_chain` distinguishes `PREV_HASH_MISMATCH` vs `CURRENT_HASH_MISMATCH` and reports expected/actual hashes + previous_good_id.
- [x] Regression test proves equity-basis IV is invariant to `net_debt`; FCFF subtracts net debt exactly once.
- [x] Value-engine + activity suites pass; frontend build clean.

## Constraints and Invariants

- `BUY_AND_HOLD_INFORMATION_SYSTEM`.
- Activity log append-only; reads never mutate.
- No behavior regressions from the review resolution.

## Implementation Tasks

- [x] Map each PR #51 review annotation to current dev code.
- [x] Enhance `verify_activity_chain` with forensic fields (`failure`, expected/actual hashes, previous_good_id).
- [x] Add net-debt invariance regression test (`test_equity_basis_iv_is_invariant_to_net_debt`).
- [x] Add `PREV_HASH_MISMATCH` forensic test.
- [x] Run value-engine/activity suites + frontend build.

## Related Notes

- PR #51: https://github.com/lap14tclc2/shannon_allocation/pull/51
- `docs/tasks/TASK-20260829-001-dev-code-review-feedback.md` (review branch)
- `TASK-20260829-065`, `TASK-20260829-066`

## Validation Evidence

```text
$ python -m pytest test_audit_integrity_verdict_exposure.py -> 23 passed
$ python -m pytest test_value_engine_audit_68_symbols.py -> 21 passed
$ python -m pytest (value-engine + activity + service suites) -> 99 passed
Frontend `npm run build`: clean.
Manual: equity-basis DCF returns identical equity value for net_debt=0 vs 5,000T;
        FCFF subtracts net debt exactly once.
```

## Decisions

- Items already implemented by tasks 065/066 satisfy PR #51 P0 findings; no rework needed.
- `verify_activity_chain` now returns failure-type + hash evidence so operators can distinguish a broken link from a tampered payload before running `repair_activity_chain`.

## Result

All PR #51 REVIEW(P0/P1) findings resolved on current dev. Forensic activity-chain verification and the net-debt invariance test were the only new code needed.