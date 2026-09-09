---
id: TASK-20260909-122
title: QPort Buffett Workspaces, API Endpoints & Navigation (T10-T16)
status: completed
priority: high
created: 2026-09-09
updated: 2026-09-09
tags: [ui, terminal, business, capital, history, navigation, api]
related: [TASK-20260909-121]
---

## Requirement
Build 4 new Buffett-Munger workspaces (`/terminal`, `/business`, `/capital`, `/history`), corresponding FastAPI endpoints in `app/main.py`, Munger Pre-Commitment Checklist (T15), AI Coach evidence summary (T14), and simplify AppNav navigation (T16).

## Context
Replaces fragmented legacy pages with a unified personal capital decision terminal enforcing the Buffett-Munger hierarchy.

## Acceptance Criteria
- [x] Implement backend API endpoints in `app/main.py`:
  - `/api/portfolio/terminal`
  - `/api/portfolio/business/{symbol}`
  - `/api/portfolio/capital`
  - `/api/portfolio/history`
- [x] Create frontend pages:
  - `frontend/src/pages/TerminalPage.jsx` (T10)
  - `frontend/src/pages/BusinessPage.jsx` (T11)
  - `frontend/src/pages/CapitalPage.jsx` (T12)
  - `frontend/src/pages/HistoryPage.jsx` (T13)
- [x] Implement Munger Pre-Commitment Checklist component (T15).
- [x] Implement Buffett/Munger AI Coach evidence summary component (T14).
- [x] Update `frontend/src/components/AppNav.jsx` with primary navigation: `Terminal`, `Business`, `Capital`, `History` (T16).
- [x] Update frontend routing in `frontend/src/entry-vercel.jsx`.

## Constraints and Invariants
- Laws of UX responsive layout across mobile (<720px) and desktop.
- `NO ACTION REQUIRED` displayed prominently when portfolio is healthy and no MOS entry exists.
- Diagnostic risk analytics accessible via link from `/terminal`.

## Implementation Tasks
- [x] Add endpoints to `app/main.py`.
- [x] Create `frontend/src/pages/TerminalPage.jsx`.
- [x] Create `frontend/src/pages/BusinessPage.jsx`.
- [x] Create `frontend/src/pages/CapitalPage.jsx`.
- [x] Create `frontend/src/pages/HistoryPage.jsx`.
- [x] Update `frontend/src/components/AppNav.jsx`.
- [x] Update `frontend/src/entry-vercel.jsx` routing.
- [x] Register task in `docs/tasks/README.md`.

## Related Notes
- Investment Policy: `docs/QPORT_BUFFETT_MUNGER_INVESTMENT_POLICY.md`

## Validation Evidence
- Added 4 API endpoints to `app/main.py`.
- Created frontend workspace components `TerminalPage.jsx`, `BusinessPage.jsx`, `CapitalPage.jsx`, `HistoryPage.jsx`.
- Updated `AppNav.jsx` navigation links and `entry-vercel.jsx` route handler.
- Verified frontend build (`npm run build`) succeeded in 1.34s without errors.
- Verified backend test suites (51/51 tests passed).

## Decisions
- 4 clean workspaces streamline personal capital decision making.

## Result
- Tasks T10-T16 completed successfully.

