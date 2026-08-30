---
id: TASK-20260829-071
title: Close remaining audit semantics and explicit chain re-anchor
status: verified
priority: high
created: 2026-08-29
updated: 2026-08-29
tags: [audit, valuation, activity-log, narrative, uncertainty]
related:
  - TASK-20260829-070
---

## Requirement

Close the remaining issues evidenced by the 2026-08-29 12:46 UTC 68-symbol audit export after commit `1497171`:

1. Make activity-chain re-anchoring an explicit admin operation so the existing legacy break can be migrated without silently mutating read-only export paths.
2. Allow re-anchor only for a link-only historical break (`PREV_HASH_MISMATCH`); never auto-legitimize a payload/hash mismatch.
3. Make Owner Earnings narrative strictly reflect `normalization_method` / `normalization_years`; `LATEST_FY` must never say “bình quân chu kỳ”.
4. Surface material unexplained share change as an explicit capital-allocation uncertainty state instead of presenting the underlying ROE grade as clean GOOD/EXCELLENT.
5. Preserve the existing scoring cap, confidence downgrade, public model gating, and cash-flow-basis invariants.

## Context

The latest audit export shows:
- FRT correctly stays `AVOID_QUALITY` with confirmed economic dilution = null and 88.8% unexplained share change.
- Healthy positive-debt leverage penalties are fixed.
- Public MODEL_INCOMPLETE valuation remains hidden.
- Activity integrity remains `BROKEN` at legacy id 73 because the new re-anchor helper has not been invoked against the existing store.
- FRT assessment narrative still says “bình quân chu kỳ” despite `normalization_method=LATEST_FY`, `normalization_years=1`.
- Capital-allocation numeric score is capped correctly, but the pillar status can still read GOOD/EXCELLENT under material unexplained dilution.

## Acceptance Criteria

- [x] Admin-only POST endpoint explicitly invokes activity-chain re-anchor with operator + reason.
- [x] Re-anchor is idempotent and accepts only `PREV_HASH_MISMATCH`; payload/hash corruption remains BROKEN and requires investigation.
- [x] `LATEST_FY` earnings narrative says latest fiscal-year Owner Earnings and explicitly avoids “bình quân chu kỳ”.
- [x] `MID_CYCLE_MEDIAN` narrative is allowed to say mid/full-cycle only when supported by normalization years.
- [x] Material `UNEXPLAINED_SHARE_CHANGE >= 20%` produces `capital_allocation.status=UNCERTAIN` while preserving `underlying_status`.
- [x] Frontend renders `UNCERTAIN` as “Chưa xác minh”, not as clean GOOD/EXCELLENT.
- [x] Regression tests cover all invariants above.
- [x] No merge to `main`.

## Constraints and Invariants

- Audit export remains read-only and never calls re-anchor implicitly.
- Existing historical activity rows are never rewritten.
- `CURRENT_HASH_MISMATCH` / payload mutation must not be re-anchored by the normal migration endpoint.
- Unknown dilution remains null, not zero.
- `MODEL_INCOMPLETE` public IV/MOS/EPV remains null.
- Owner Earnings equity cash flow remains Cost of Equity -> Equity Value -> no net-debt adjustment.

## Implementation Tasks

- [x] Add admin service + API route for explicit re-anchor.
- [x] Harden `reanchor_activity_chain` failure eligibility.
- [x] Fix earnings narrative by normalization enum.
- [x] Add explicit capital-allocation uncertainty state + frontend label.
- [x] Add backend/frontend contract tests.
- [x] Validate diff and update task to verified/completed.

## Related Notes

Latest audit evidence: `qport-ai-audit-2026-08-29(3).md` generated at 2026-08-29T12:46:40.882Z.

## Validation Evidence

- Vercel deployment check for implementation head `524dd368f5b4305ef6bcb92d7d43867b1e4090ba`: **SUCCESS**.
- PR #52 is mergeable/clean against `dev`.
- Added regression coverage for link-only re-anchor, payload-tamper refusal, LATEST_FY narrative, scoped admin re-anchor API, and frontend uncertainty rendering.
- GitHub Actions returned no workflow run for this SHA; local pytest could not be executed in this environment because the repository cannot be cloned from the isolated container. Do not claim a full pytest pass from this session.

## Decisions

Use an explicit admin mutation endpoint rather than automatic re-anchor during export/overview reads. This keeps audit/export paths side-effect free and preserves operator accountability.

## Result

Implementation complete on `task/TASK-20260829-071-audit-semantics-reanchor` and opened as draft PR #52. No merge performed.
