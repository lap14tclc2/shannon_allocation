---
id: TASK-20260829-001
title: Review dev branch and annotate code-level findings
status: in-progress
priority: high
created: 2026-08-29
updated: 2026-08-29
tags: [audit, review, valuation, activity-log, dev-branch]
related: []
---

## Requirement

Read the `dev` branch of `lap14tclc2/shannon_allocation` and place actionable review feedback directly next to the relevant code without changing product behavior.

## Context

- Review base: `dev` at `fdb61bdcae66d0924ff8b61d27d15fcceef78b46`.
- `dev` is 102 commits behind `main`, so comments must describe issues in the reviewed branch and must not assume parity with current production behavior.
- Recent audit evidence exposed valuation-basis, model-gating, activity-integrity, and audit-side-effect risks.

## Acceptance Criteria

- [ ] Add code-local `REVIEW(P0/P1)` comments only; do not change runtime behavior.
- [ ] Flag Owner Earnings equity-cash-flow vs Enterprise Value/net-debt inconsistency.
- [ ] Flag hard-coded generic growth assumptions and missing archetype/model routing in the dev valuation orchestrator.
- [ ] Flag activity hash-chain concurrency/idempotency risk.
- [ ] Flag `AI_EXPORT` activity logging as a side-effect risk for a read-only audit/export contract.
- [ ] Flag missing regression tests for the above invariants.
- [ ] Keep review changes isolated on a review branch; do not merge.

## Constraints and Invariants

- No production logic changes.
- No merge to `dev` or `main`.
- Comments must be precise enough for a developer/AI agent to turn into implementation tasks.
- Owner Earnings starting from Net Income is equity-basis cash flow unless explicitly reconstructed to FCFF.

## Implementation Tasks

- [ ] Annotate `python/portfolio/value_engine/dcf.py`.
- [ ] Annotate `python/portfolio/value_engine/engine.py`.
- [ ] Annotate `python/portfolio/activity.py`.
- [ ] Annotate `python/portfolio/correctable_service.py`.
- [ ] Annotate `python/portfolio/tests/test_value_engine.py`.

## Related Notes

The review branch intentionally starts from `dev`, not `main`, because the request explicitly targets `dev`.

## Validation Evidence

Pending code diff review.

## Decisions

Use a dedicated review branch `review/dev-code-feedback-20260829` so feedback appears directly in source without polluting `dev`.

## Result

Pending.
