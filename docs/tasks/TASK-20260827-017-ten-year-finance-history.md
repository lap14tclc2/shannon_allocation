---
id: TASK-20260827-017
title: Extend finance crawl history to ten fiscal years
status: ready
priority: high
created: 2026-08-27
updated: 2026-08-27
---

## Requirement

Crawl the ten most recently completed fiscal years instead of the current four-year window, while retaining only completed quarters for the current fiscal year.

## Acceptance Criteria

- [ ] On 2026-08-27, the required FY set is 2016 through 2025.
- [ ] Q1 and Q2 2026 remain included; Q3/Q4 are not requested until completed.
- [ ] Incremental eligibility queues older FY documents only when absent or not SUCCESS.
- [ ] Existing SUCCESS documents are not refetched.
- [ ] Add a regression test for the ten-year FY window and completed-quarter policy.

## Constraints and Invariants

- Do not create an unfinished FY.
- Do not create future quarters.
- Keep the provider-independent period policy shared by TCBS and CafeF.
- Preserve incremental queue and duplicate-document safeguards.

## Result

Pending implementation.
