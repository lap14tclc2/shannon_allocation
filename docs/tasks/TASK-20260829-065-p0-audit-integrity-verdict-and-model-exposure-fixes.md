# TASK-20260829-065: P0 Audit Integrity, Verdict & Model-Exposure Fixes

- **ID**: `TASK-20260829-065`
- **Title**: P0 Audit Integrity, Verdict & Model-Exposure Fixes
- **Status**: `completed`
- **Priority**: `high`
- **Date**: `2026-08-29`

## Requirement

Address the P0/P1 items in `docs/feedback.txt` (audit export 2026-08-29 10:06 UTC):

1. **P0 – activity_integrity BROKEN** (`first_bad_id=73`) and **export appends +69 activity records** (equal to ledger rows) per export.
2. **P0 – HARD_REJECT must override final verdict**: if `hard_rejects.length > 0`, `final_status` cannot be `ATTRACTIVE` or `HIGH_CONVICTION_VALUE`.
3. **P0 – economic dilution semantics**: separate `NON_ECONOMIC_SHARE_CHANGE` (stock dividend, bonus shares, stock split) from `ECONOMIC_DILUTION` (ESOP below fair value, rights issue with value transfer, new capital, convertibles, share-funded acquisition); only the latter feeds `EXCESSIVE_DILUTION`.
4. **P0 – MODEL_INCOMPLETE must hide public IV/MOS**: when `model_status != MODEL_VERIFIED`, public `bear/base/bull_iv` and `mos` must be `null`; generic DCF kept under `diagnostic_fallback` with `usage=AUDIT_ONLY`.
5. **P1 – NO_HISTORY → XIRR = null** (currently a `-99.97%` artifact).

## Context

Auditor compared 10:06 UTC vs 09:59 UTC exports; valuation engine unchanged across all 68 symbols (8.1–8.3/10). The new blocker is `activity_integrity = BROKEN` at `first_bad_id=73` and an export that appends exactly 69 activity records. Root cause identified:

- `GET /api/portfolio/dividends/latest/{symbol}` logged one `DIVIDEND_HISTORY_LOOKUP` activity record per symbol; the AI export audits ~68 holdings → ~68 records + 1 `AI_EXPORT` = 69 records per export.
- The hash chain race: `append_activity` read the last `record_hash` then inserted without serialization; two concurrent appends could both read the same previous hash and branch the chain (matches `first_bad_id=73`).
- `MarginOfSafetyEngine` only blocked `HIGH_CONVICTION_VALUE` with `has_solvency_risk`; a satisfied MOS still yielded `ATTRACTIVE` with `hard_rejects` non-empty (FRT/SCS with `EXCESSIVE_DILUTION`).
- Dilution classifier conflated raw share-count increase with economic dilution (only `STOCK_DIVIDEND` stripped; bonus shares/splits in `corporate_actions` ignored).
- Report serialization exposed `scenarios.*.intrinsic_value_per_share` and `base_iv`/`mos` even for `MODEL_INCOMPLETE` (KSV/HAH/VHM).

## Acceptance Criteria

- [x] Repeated export with identical DB state produces an identical activity count (export is read-only / idempotent).
- [x] `append_activity` is concurrency-safe: no two concurrent appends can share the same `prev_hash`.
- [x] Optional explicit repair tool recomputes the activity hash chain after operator confirmation.
- [x] `hard_rejects` non-empty → verdict is never `ATTRACTIVE` / `HIGH_CONVICTION_VALUE`.
- [x] Dilution classifier distinguishes non-economic share changes from economic dilution; `EXCESSIVE_DILUTION` fires only on economic dilution ≥ 20%.
- [x] `model_status != MODEL_VERIFIED` → public IV/MOS fields are `null`; diagnostic values moved under `diagnostic_fallback` (`usage=AUDIT_ONLY`).
- [x] `NO_HISTORY` → `xirr = null` (no spurious `-99.97%`).
- [x] Regression tests pass; value-engine / activity suites green.

## Constraints and Invariants

- `BUY_AND_HOLD_INFORMATION_SYSTEM` — no auto trade generation.
- Ledger/activity immutability: no update/delete API for `activity_log`.
- Audit-only reads must not mutate the activity log.
- Model verdicts must never claim `MODEL_VERIFIED` for a model that did not actually run.

## Implementation Tasks

- [x] 1. Make dividend-latest GET endpoints read-only (drop `DIVIDEND_HISTORY_LOOKUP` logging in `app/main.py` + `python/buyhold_server.py`).
- [x] 2. Serialize `append_activity` (SQLite `BEGIN IMMEDIATE` / Postgres `pg_advisory_xact_lock`) to eliminate the prev_hash race.
- [x] 3. Make `log_client_activity('AI_EXPORT')` idempotent (dedupe by actor+action+UTC day via `idempotency_key` column + UNIQUE partial index).
- [x] 4. Add explicit `repair_activity_chain(store, checkpoint_id=...)` for operator-confirmed rebase.
- [x] 5. `MarginOfSafetyEngine`/`engine.py`: downgrade verdict when `hard_rejects` non-empty (`SOLVENCY_RISK`→`AVOID_SOLVENCY`, else `AVOID_QUALITY`/`UNVALUABLE`).
- [x] 6. Dilution classifier: `python/portfolio/value_engine/dilution.py` splits `non_economic_share_change_pct` vs `economic_dilution_pct`; app feeds both; engine/scorer use economic dilution only.
- [x] 7. Add `public_bear_iv`/`public_base_iv`/`public_bull_iv`/`public_mos` + `diagnostic_fallback` to `ValuationReport`; gated on `model_status == MODEL_VERIFIED`.
- [x] 8. `service.performance()`: `NO_HISTORY` → `xirr = null`.
- [x] 9. Frontend: `ValuationPage.jsx` + `aiExport.js` use public IV/MOS fields (hide when null); methodology guide de-jargoned to Vietnamese.
- [x] 10. Regression tests in `python/portfolio/tests/test_audit_integrity_verdict_exposure.py`.

## Related Notes

- `docs/feedback.txt`
- `TASK-20260829-058-p0-valuation-engine-audit-fixes`
- `TASK-20260829-060-p0-cashflow-basis-normalization-gate`

## Validation Evidence

```text
$ python -m pytest test_audit_integrity_verdict_exposure.py -> 14 passed
  (export idempotency, concurrent-append chain, repair, hard-reject override,
   dilution semantics, MODEL_INCOMPLETE public gating, NO_HISTORY XIRR null)

$ python -m pytest (value-engine + activity + service + contract suites) -> 119 passed
$ python -m pytest python/portfolio/tests -> 314 passed, 6 failed, 1 skipped
  (the 6 failures are pre-existing on committed HEAD: AppNav/header-v2/CafeF
   contract tests, reproduced via git stash, unrelated to this task)

Frontend `npm run build`: clean (0 errors).

Manual verification:
  FRT (EXCESSIVE_DILUTION + MOS 48.2%)  -> verdict AVOID_QUALITY (was ATTRACTIVE)
  KSV (MODEL_INCOMPLETE, mining)         -> public_base_iv=None, public_mos=None,
                                            diagnostic_fallback.usage=AUDIT_ONLY
  FPT (MODEL_VERIFIED)                   -> public_base_iv present, fallback=None
  NO_HISTORY portfolio                    -> xirr=null, xirr_status=NO_HISTORY
```

## Decisions

- Activity log reads are strictly read-only. `DIVIDEND_HISTORY_LOOKUP` is no longer recorded on GET; the AI export is the single idempotent client marker.
- `append_activity` now serializes writers with a process-wide `threading.Lock` plus a DB-level lock (`BEGIN IMMEDIATE` on SQLite, `pg_advisory_xact_lock` on Postgres), so the tail `prev_hash` can never branch.
- `idempotency_key` is stored in a dedicated column with a UNIQUE partial index but is intentionally NOT part of the tamper-evident hash payload, keeping pre-existing rows verifiable.
- Hard rejects are surfaced through the same `MarginOfSafetyEngine.verdict_status` so the report's `margin_of_safety_analysis` and `valuation_pill` stay consistent.
- Economic dilution uses the same 20% excess threshold as before but now only on the economic component; the `EXCESSIVE_DILUTION` reject is reserved for genuine capital-raising dilution.

## Result

Implemented all P0 items and the P1 XIRR null fix from the latest audit. Export is now read-only and idempotent; the activity hash chain cannot branch under concurrency; a repair tool is provided; hard rejects override valuation-positive verdicts; economic dilution is separated from non-economic share changes; MODEL_INCOMPLETE reports hide public IV/MOS behind an AUDIT_ONLY diagnostic fallback; NO_HISTORY portfolios no longer show a spurious -99.97% XIRR. 14 new regression tests; all value-engine/activity/service suites green; frontend build clean.