---
id: TASK-20260827-020
title: Temporarily disable TCBS finance worker provider
status: in_progress
priority: high
created: 2026-08-27
updated: 2026-08-27
tags: [finance-data, crawler, tcbs]
related: [TASK-20260827-019]
---

## Requirement

Temporarily remove TCBS from the external finance worker crawl path while keeping
CafeF active. Existing TCBS documents and canonical records must remain intact.

## Acceptance Criteria

- [x] Worker provider iteration uses CafeF only.
- [x] TCBS is not requested by normal worker runs.
- [x] Existing TCBS database records are not deleted or rewritten.
- [x] Logs and crawl summaries show the active provider scope clearly.
- [x] Add/update contract tests and documentation.

## Constraints and Invariants

- This is a runtime/provider-scope change, not a data migration.
- Preserve the provider abstraction so TCBS can be re-enabled later.
- Do not expose or log bearer tokens.
- Keep queue claiming, incremental document logic, and deduplication unchanged.

## Implementation

- Added WORKER_PROVIDERS = (cafef,) while retaining the supported-provider
  registry for future TCBS re-enable.
- Changed required-document planning and crawl iteration to use the worker scope.
- Added worker/crawl logs showing providers=cafef.
- Removed the TCBS token smoke-test instruction from the active runbook and
  documented that existing TCBS data is preserved.
- Added regression contract coverage.

## Remaining Validation

- [ ] Run one local worker job and verify no TCBS request appears in logs.
- [ ] Run the full Python test suite and Vite build.

## Result

Implementation complete; runtime validation pending.
