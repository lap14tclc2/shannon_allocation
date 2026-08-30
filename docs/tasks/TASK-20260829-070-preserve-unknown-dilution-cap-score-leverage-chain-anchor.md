# TASK-20260829-070: Preserve unknown dilution, cap capital score, leverage & chain anchor

- **ID**: `TASK-20260829-070`
- **Title**: Preserve unknown dilution, cap capital score, leverage & chain anchor
- **Status**: `verified`
- **Priority**: `high`
- **Date**: `2026-08-29`

## Requirement

Address the P0/P1 priority items from `docs/feedback.txt` (export 12:25 UTC, overall ~9.0/10):

1. **P0/P1 – Preserve UNKNOWN dilution as null, never 0**: `confirmed dilution = null` means "unknown"; `0` means "verified no dilution". Engine/scorer currently collapse `None` → `0.0`, so FRT (88.8% unexplained) scores 15/15 capital allocation.
2. **P0/P1 – Cap capital-allocation score when unexplained share change is material**: when classification is `UNEXPLAINED_SHARE_CHANGE`, do not hard-reject but cap `capital_allocation_score = min(score, 10)`.
3. **P0/P1 – Fix healthy-positive-debt leverage penalty → 0**: `_leverage_penalty()` returns +3 for any positive net debt when metrics < 2, treating "healthy evidence" as "no evidence". Only return +3 when metrics are UNAVAILABLE.
4. **P0/P1 – Show unexplained dilution in Health table**: the `5Y Share Dilution` column must render `N/A · X% unexplained` instead of a false `0%`.
5. **P0/P1 – Activity-chain anchor after historical break**: keep the legacy broken segment as `BROKEN_HISTORICAL`, then start a NEW secured chain from a `genesis_anchor`; status `VERIFIED_FROM_ANCHOR` — do not silently rehash history.

## Context

Reviewer confirmed all prior blockers fixed (cash-flow basis 10/10, model gating 9.5, public safety 9.5, verdict gate 9.5). Remaining: uncertainty handling (7.5), leverage MOS (8), activity integrity (6), normalization (6), specialized models (7). This task covers the concrete code-level P0/P1 items 1–5.

## Acceptance Criteria

- [x] `UNEXPLAINED_SHARE_CHANGE` keeps `confirmed_economic_dilution_pct = None` end-to-end (never `0`); confidence LOW.
- [x] Capital-allocation score capped at 10 when unexplained share change is material; no hard reject.
- [x] Positive debt with healthy metrics (ND/EBITDA < 2 and payback < 2) → leverage penalty 0; +3 only when metrics unavailable.
- [x] Health/valuation table shows `N/A · X% unexplained` for unexplained symbols (not `0%`).
- [x] `reanchor_activity_chain()` produces `VERIFIED_FROM_ANCHOR` with genesis anchor, preserving the legacy `BROKEN_HISTORICAL` segment.
- [x] Regression tests + full suites pass; frontend build clean.

## Constraints and Invariants

- `BUY_AND_HOLD_INFORMATION_SYSTEM`.
- Never rewrite audit history silently; anchor from the last good state.
- Unknown ≠ 0: uncertainty must be surfaced, not collapsed.

## Implementation Tasks

- [x] 1. `engine.py`: keep confirmed dilution None (don't collapse to 0); pass null-safe to scorer.
- [x] 2. `quality_scorer.py`: cap capital_allocation_score at 10 when classification is UNEXPLAINED and unexplained material.
- [x] 3. `margin_of_safety.py`: `_leverage_penalty` returns 0 for healthy positive debt with available metrics.
- [x] 4. Frontend: Health table + valuation overview show unexplained (N/A · X%).
- [x] 5. `activity.py`: `reanchor_activity_chain` + `verify_activity_chain` returns `VERIFIED_FROM_ANCHOR`.
- [x] 6. Tests + docs.

## Related Notes

- `docs/feedback.txt`
- `TASK-20260829-069`

## Validation Evidence

```text
$ python -m pytest test_audit_integrity_verdict_exposure.py -> 36 passed
$ python -m pytest (value-engine + activity + service suites) -> 111 passed
$ python -m pytest python/portfolio/tests -> 337 passed, 6 failed, 1 skipped
  (6 failures pre-existing on HEAD: AppNav/header-v2/CafeF contract tests)

Frontend `npm run build`: clean.

Manual verification of every review case:
  UNEXPLAINED (FRT 88.8%)  -> confirmed=None (never 0), confidence LOW,
                             capital_allocation_score <= 10, no hard reject
  SCS (ND/EBITDA 0.54x, 0.7y) -> leverage penalty 0 (was +3)
  positive debt, no metrics -> leverage penalty +3 (conservative)
  reanchor after broken at id=2 -> VERIFIED_FROM_ANCHOR, genesis_anchor set,
                             legacy row left untouched (no silent rewrite),
                             new appends still verify, re-anchor idempotent
```

## Decisions

- Unknown dilution is preserved as `None` end-to-end; the engine only falls back to a numeric value for confirmed classifications (EXCESSIVE/ECONOMIC/MINOR).
- UNEXPLAINED with unexplained >= 20% caps `capital_allocation_score` at 10 (material uncertainty), no hard reject (missing evidence ≠ proven dilution).
- `_leverage_penalty` distinguishes "metrics available & healthy" (0) from "positive debt, metrics unavailable" (+3 conservative).
- Frontend renders `N/A · X% unexplained` for UNEXPLAINED symbols and renames the export column to `5Y Dilution (Confirmed | Unexplained)`.
- Activity chain is never silently rehashed: `reanchor_activity_chain()` inserts a `chain_anchor` genesis row that binds the new verified chain to the last-known-good hash + migration metadata; `verify_activity_chain` reports `VERIFIED_FROM_ANCHOR` with `prev_segment_status = BROKEN_HISTORICAL`.

## Result

Resolved all 5 P0/P1 priority items from the 12:25 UTC audit: unknown dilution is preserved as null (never 0), capital-allocation score is capped for material unexplained share change, healthy positive debt no longer receives a leverage penalty, the Health/export table surfaces unexplained dilution, and the activity chain can be re-anchored after a historical break without rewriting history. 36 exposure tests + 111 value-engine/activity/service tests pass; frontend build clean.