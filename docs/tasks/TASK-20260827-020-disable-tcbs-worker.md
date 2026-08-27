---
id: TASK-20260827-020
title: Temporarily disable TCBS finance worker provider
status: ready
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

- [ ] Worker provider iteration uses CafeF only.
- [ ] TCBS is not requested by normal worker runs.
- [ ] Existing TCBS database records are not deleted or rewritten.
- [ ] Logs and crawl summaries show the active provider scope clearly.
- [ ] Add/update contract tests and documentation.

## Constraints and Invariants

- This is a runtime/provider-scope change, not a data migration.
- Preserve the provider abstraction so TCBS can be re-enabled later.
- Do not expose or log bearer tokens.
- Keep queue claiming, incremental document logic, and deduplication unchanged.

## Result

Pending implementation.
