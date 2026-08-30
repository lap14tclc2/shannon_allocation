# TASK-20260829-066: P0 Event-Evidence Dilution, EPV Gating & Activity Trace

- **ID**: `TASK-20260829-066`
- **Title**: P0 Event-Evidence Dilution, EPV Gating & Activity Trace
- **Status**: `completed`
- **Priority**: `high`
- **Date**: `2026-08-29`

## Requirement

Address the P0/P1/P2 items from `docs/feedback.txt` (audit export 2026-08-29 10:56 UTC):

1. **P0 – activity_integrity still BROKEN** (`first_bad_id=73`, records 693→765, +72 per audit cycle). Prove export/audit is side-effect free (`count_before == count_after`), and provide a trace from `first_bad_id=73` (event_id, event_type, created_at, source, idempotency_key, prev_hash, current_hash).
2. **P0 – UNEXPLAINED share growth ≠ economic dilution**: FRT has `economic_events=[]` yet is hard-rejected as `EXCESSIVE_DILUTION`. A residual, unexplained share increase must be `UNEXPLAINED_SHARE_CHANGE` + confidence LOW + require verification — only actual ESOP/rights/placement/convertible/M&A events may produce `ECONOMIC_DILUTION`.
3. **P1 – Hide EPV for MODEL_INCOMPLETE**: `public_epv = null`, `diagnostic_fallback.epv = ...` (HAH/HT1/HVN/KSV/PVD/PVS currently leak EPV in the public overview).
4. **P2 – Maintenance CapEx proxy → LOW confidence** (currently MEDIUM unless replacement/capacity evidence exists).

## Context

The auditor raised readiness 8.2→8.6. Previous P0s (XIRR NO_HISTORY, MODEL_INCOMPLETE public IV/MOS, hard-reject override, SCS dilution) are confirmed PASS. The remaining blockers are activity-log integrity, requiring event-level evidence for dilution, and EPV leaking in the public overview. Specialized models (Reserve/Fleet NAV, Airline EBITDAR, Mid-cycle FCFF, 7-10Y normalization) remain incomplete but are no longer dangerous because public IV is hidden.

## Acceptance Criteria

- [x] Export/audit workflow appends no activity records (regression test proves count unchanged).
- [x] Activity chain trace available from `first_bad_id` with the requested fields.
- [x] `classify_share_change` returns `UNEXPLAINED_SHARE_CHANGE` when `economic_events` is empty; `EXCESSIVE_DILUTION`/`ECONOMIC_DILUTION` only with actual events.
- [x] Engine/scorer downgrades confidence and skips `EXCESSIVE_DILUTION` hard-reject for unexplained-only dilution.
- [x] `public_epv` is null when `model_status != MODEL_VERIFIED`; diagnostic EPV moves under `diagnostic_fallback.epv`.
- [x] Maintenance CapEx proxy confidence defaults to LOW.
- [x] Regression tests + frontend build pass.

## Constraints and Invariants

- `BUY_AND_HOLD_INFORMATION_SYSTEM`.
- Activity log is append-only; reads never mutate it.
- Never present residual share growth as proven economic dilution.

## Implementation Tasks

- [x] 1. Dilution classifier: `UNEXPLAINED_SHARE_CHANGE` when `economic_events` empty.
- [x] 2. app/main.py diagnosis text + engine passes classification; confidence LOW; no hard reject without events.
- [x] 3. `public_epv` gating in `ValuationReport` + engine + app sanitization + frontend.
- [x] 4. Maintenance CapEx proxy → LOW confidence in `owner_earnings.py`.
- [x] 5. Activity trace helper + regression test proving export side-effect free.
- [x] 6. Tests + docs update.

## Related Notes

- `docs/feedback.txt`
- `TASK-20260829-065-p0-audit-integrity-verdict-and-model-exposure-fixes`

## Validation Evidence

```text
$ python -m pytest test_audit_integrity_verdict_exposure.py -> 22 passed
  (export workflow side-effect free, chain trace fields, repair, UNEXPLAINED
   dilution, proven-dilution hard reject, public_epv gating, maintenance capEx LOW)

$ python -m pytest (value-engine + activity + service + contract suites) -> 98 passed
$ python -m pytest python/portfolio/tests -> 322 passed, 6 failed, 1 skipped
  (6 failures pre-existing on committed HEAD: AppNav/header-v2/CafeF contract tests)

Frontend `npm run build`: clean (0 errors).
```

## Decisions

- The frontend AI export no longer POSTs an `AI_EXPORT` activity record: the export is "Read-only audit evidence" and must be provably side-effect free (`count_before == count_after`).
- `log_client_activity('AI_EXPORT')` keeps its per-day/schema idempotency as a defensive net for any client that still logs it.
- `UNEXPLAINED_SHARE_CHANGE` is a new classification: residual share growth without ESOP/rights/placement/convertible/M&A events lowers confidence but never triggers `EXCESSIVE_DILUTION`. Proven economic dilution still hard-rejects.
- EPV joins the public/private split: `public_epv` null unless `MODEL_VERIFIED`; diagnostic EPV lives under `diagnostic_fallback.epv`.
- `MIN_DEPRECIATION_CAPEX_PROXY` maintenance CapEx confidence now defaults to LOW (P2).

## Result

Implemented all P0/P1/P2 items from the 10:56 UTC audit: export is provably side-effect free, activity chain trace from `first_bad_id` is available with the requested fields, unexplained share growth no longer produces `EXCESSIVE_DILUTION` without event evidence, EPV is hidden for `MODEL_INCOMPLETE`, and maintenance CapEx proxy confidence defaults to LOW. 22 regression tests in the exposure suite; all value-engine/activity/service suites green; frontend build clean.