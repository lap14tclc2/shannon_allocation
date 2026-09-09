---
id: TASK-20260909-115
title: QPort Buffett Terminal Architecture Audit (T00)
status: completed
priority: high
created: 2026-09-09
updated: 2026-09-09
tags: [architecture, audit, buffett-munger, refactor]
related: []
---

## Requirement
Perform comprehensive codebase audit across backend (`python/portfolio/`, `app/`, `api/`) and frontend (`frontend/src/pages/`, `frontend/src/lib/`, `frontend/src/components/`) to establish the component classification matrix (KEEP, REUSE, REFACTOR, MERGE, HIDE, DEPRECATE, DELETE_LATER) and explicit dependency graph for the QPort Buffett-Munger Terminal Refactor.

## Context
QPort is refactoring from a fragmented portfolio/allocation/risk dashboard into a Buffett-Munger personal capital decision system. Task T00 requires auditing all modules before any code modifications.

## Acceptance Criteria
- [x] Comprehensive audit document `docs/QPORT_BUFFETT_TERMINAL_ARCHITECTURE_AUDIT.md` produced.
- [x] Every major backend package/module classified (`KEEP`, `REUSE`, `REFACTOR`, `MERGE`, `HIDE`, `DEPRECATE`, `DELETE_LATER`).
- [x] Every major frontend page/component classified (`KEEP`, `REUSE`, `REFACTOR`, `MERGE`, `HIDE`, `DEPRECATE`, `DELETE_LATER`).
- [x] Explicit dependency graph produced.
- [x] Legacy route migration risks and baseline non-regression requirements documented.
- [x] No production behavior changes during audit.

## Constraints and Invariants
- Zero runtime behavior modifications during audit task T00.
- Independent data-source boundary (no mandatory dependency on SSI/TCBS during refactor).
- Preservation of golden baseline calculations for ACB, DGC, FPT.

## Implementation Tasks
- [x] Audit `python/portfolio/value_engine/` and classify modules.
- [x] Audit `python/portfolio/allocation/` and classify modules.
- [x] Audit `python/portfolio/financial_data/` and classify modules.
- [x] Audit `python/portfolio/risk.py`, `market_data.py`, `permanent_loss_risk.py`, `accounting.py`, `service.py`.
- [x] Audit `app/main.py` endpoint routes.
- [x] Audit `frontend/src/pages/` and `frontend/src/components/AppNav.jsx`.
- [x] Write `docs/QPORT_BUFFETT_TERMINAL_ARCHITECTURE_AUDIT.md`.

## Related Notes
- Refactor Master Plan: `QPort Buffett–Munger Refactor Plan for Antigravity`

## Validation Evidence
- Created `docs/QPORT_BUFFETT_TERMINAL_ARCHITECTURE_AUDIT.md`.
- Verified all 33 python portfolio modules, 22 frontend pages, AppNav navigation components, and FastAPI routes.
- Produced component classification matrix and target dependency graph.

## Decisions
- Architectural classifications finalized based on Buffett-Munger core principles and non-goals.

## Result
- Task T00 architecture audit successfully completed without runtime code modification.

