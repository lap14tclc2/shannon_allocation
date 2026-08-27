---
id: TASK-20260827-001
title: Improve Vnstock universe metadata quality
status: implemented
priority: medium
created: 2026-08-27
updated: 2026-08-27
tags: [finance, vnstock, universe, data-quality]
related: [TASK-20260826-006]
---

## Requirement

Keep Vnstock as the local worker's universe provider, but make missing exchange and industry data visible and correctly map common Vnstock field names.

## Context

The Finance UI showed valid symbols with UNKNOWN exchange and - industry without quality information. The existing sync only checked a narrow set of field names.

## Acceptance Criteria

- [x] Preserve Vnstock as the universe/symbol-list provider.
- [x] Map common exchange, company-name and industry field variants.
- [x] Keep valid symbols when optional metadata is missing.
- [x] Reject/skip rows without a symbol from persistence.
- [x] Return quality counters and warnings from universe sync.
- [x] Display missing metadata clearly in Finance UI.
- [x] Add regression tests for mapping and quality counters.

## Implementation Tasks

- [x] Add schema-tolerant universe row normalization.
- [x] Add duplicate/missing metadata quality report.
- [x] Extend API result with quality and warnings.
- [x] Update Finance UI labels and quality banner.
- [x] Add tests.

## Validation Evidence

Regression tests added. Runtime PostgreSQL/Vnstock execution remains environment-dependent.

## Result

Implemented on dev; valid symbols remain crawlable while data-quality gaps are explicit.
