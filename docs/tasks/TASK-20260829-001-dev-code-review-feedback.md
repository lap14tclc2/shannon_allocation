---
id: TASK-20260829-001
title: Review dev branch and annotate code-level findings
status: completed
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

- [x] Add code-local `REVIEW(P0/P1)` comments only; do not change runtime behavior.
- [x] Flag Owner Earnings equity-cash-flow vs Enterprise Value/net-debt inconsistency.
- [x] Flag hard-coded generic growth assumptions and missing archetype/model routing in the dev valuation orchestrator.
- [x] Flag activity hash-chain concurrency/idempotency risk.
- [x] Flag `AI_EXPORT` activity logging as a side-effect risk for a read-only audit/export contract.
- [x] Flag missing regression tests for the above invariants.
- [x] Keep review changes isolated on a review branch; do not merge.

## Constraints and Invariants

- No production logic changes.
- No merge to `dev` or `main`.
- Comments must be precise enough for a developer/AI agent to turn into implementation tasks.
- Owner Earnings starting from Net Income is equity-basis cash flow unless explicitly reconstructed to FCFF.

## Implementation Tasks

- [x] Annotate `python/portfolio/value_engine/dcf.py`.
- [x] Annotate `python/portfolio/value_engine/engine.py`.
- [x] Annotate `python/portfolio/activity.py`.
- [x] Annotate `python/portfolio/correctable_service.py`.
- [x] Annotate `python/portfolio/tests/test_value_engine.py`.

## Related Notes

The review branch intentionally starts from `dev`, not `main`, because the request explicitly targets `dev`.

## Validation Evidence

Validated with `compare_commits(dev, review/dev-code-feedback-20260829)`: only the task file plus comment-only additions in five reviewed source/test files; 0 deletions and no runtime statements changed.

## Decisions

Use a dedicated review branch `review/dev-code-feedback-20260829` so feedback appears directly in source without polluting `dev`.

## Result

Completed. Review comments are present directly in code on the dedicated review branch; no product behavior was modified and nothing was merged.
