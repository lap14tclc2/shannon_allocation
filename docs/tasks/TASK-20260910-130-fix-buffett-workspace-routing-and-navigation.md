---
id: TASK-20260910-130
title: Fix Buffett/Munger workspace routing and navigation
status: completed
priority: high
created: 2026-09-10
updated: 2026-09-10
tags:
  - buffett-munger
  - routing
  - frontend
  - workspace
related: []
---

# TASK-20260910-130: Fix Buffett/Munger Workspace Routing and Navigation

- **Status**: completed
- **Priority**: high
- **Owner**: AI Coding Agent
- **Date**: 2026-09-10

## Requirement
Fix client-side and server-side route resolution so that all four primary Buffett/Munger workspaces function seamlessly:
- `/` → Terminal Workspace
- `/business` → Business landing/search/select workspace
- `/business/:symbol` → Business detail workspace (e.g. `/business/FPT`)
- `/capital` → Capital / Personal Fortress workspace
- `/history` → Compounding History workspace

Direct browser navigation (entering URL) and F5 refresh must render the corresponding workspace instead of falling through to "Trang không tồn tại".

## Context
Currently, `/` works and displays real portfolio holdings (DGC, ACB, FPT). However, navigation or direct access to `/business`, `/capital`, and `/history` returns "Trang không tồn tại" / "Không thể tải dữ liệu" due to `fetchRoutePayload` in `frontend/src/lib/store.js` throwing an unhandled route error for unlisted pathnames.

## Acceptance Criteria
- [x] `/` renders TerminalPage with actual holdings.
- [x] `/business` renders BusinessPage landing state (does not require symbol, shows portfolio symbol list + search).
- [x] `/business/FPT`, `/business/ACB`, `/business/DGC` render BusinessPage detail view for the requested symbol.
- [x] `/capital` renders CapitalPage (shows setup/empty state when Personal Balance Sheet unconfigured instead of 404).
- [x] `/history` renders HistoryPage (compounding history & transactions).
- [x] Direct browser navigation and F5 refresh work on `/`, `/business`, `/business/:symbol`, `/capital`, `/history`.
- [x] Navigation dropdown / header points to canonical routes (`/`, `/business`, `/capital`, `/history`).
- [x] `[Cấu hình tài chính cá nhân]` CTA in Terminal navigates to `/capital`.
- [x] Unknown routes (e.g. `/unknown-path`) continue rendering 404 "Trang không tồn tại".
- [x] Frontend build (`npm run build`) passes cleanly.

## Constraints and Invariants
- Target branch: `feature/buffett-munger-refactor`.
- Do NOT modify `main`.
- Do NOT merge into `main`.
- Do NOT change Personal Finance decision semantics (`BUILD_RESERVE_FIRST` when unconfigured).
- Do NOT change Value Trap decision semantics (`INSUFFICIENT_DATA` remains when data is missing).
- Do NOT delete legacy pages/routes.

## Implementation Tasks
- [x] Audit `frontend/src/entry-vercel.jsx`, `frontend/src/components/AppNav.jsx`, `frontend/src/pages/`, `frontend/src/lib/api.js` and Redux/route-loader registry to pinpoint exact root cause.
- [x] Update route registry & Redux route loader in `frontend/src/lib/store.js` to register canonical routes (`/terminal`, `/business`, `/business/:symbol`, `/capital`, `/history`).
- [x] Update `BusinessPage.jsx` to handle `/business` landing state (select symbol from portfolio or search).
- [x] Update `CapitalPage.jsx` to handle unconfigured Personal Finance state gracefully with interactive setup form.
- [x] Update `AppNav.jsx` links to use canonical URLs (`/`, `/business`, `/capital`, `/history`).
- [x] Add route resolution test cases in `python/portfolio/tests/test_workspace_routing_contracts.py`.
- [x] Run full test suite (135 tests passed) and frontend production build (`vite build` passed).
- [x] Perform runtime smoke test across all 5 canonical routes + refresh.
- [x] Update Task 130 note with validation evidence and mark `completed`.

## Related Notes
- `AGENTS.md`: Zettelkasten Task-First Workflow.
- `frontend/src/entry-vercel.jsx`: Route loading & Redux routing dispatcher.
- `frontend/src/components/AppNav.jsx`: Main navigation bar.
- `frontend/src/lib/store.js`: `fetchRoutePayload(pathname)`.

## Root Cause Analysis
In `frontend/src/lib/store.js`, `fetchRoutePayload(pathname)` evaluates `switch (pathname)` for Redux route loading:
Pathnames `/terminal`, `/business`, `/business/:symbol`, `/capital`, and `/history` were omitted from the `switch` statement and lacked a prefix match handler. As a result, when Redux dispatched `loadRoute({ pathname })` on direct navigation or link click, `fetchRoutePayload` executed `default: throw new Error('Trang không tồn tại.')`. `loadRoute.rejected` set `route.status = 'failed'`, causing `entry-vercel.jsx` to display `ErrorScreen` ("Không thể tải dữ liệu - Trang không tồn tại.").

## Validation Evidence
1. **Pytest Test Suite**:
   Command:
   ```bash
   $env:PYTHONPATH="python"; & "$HOME\.venv\Scripts\python.exe" -m pytest \
     python/portfolio/tests/test_workspace_routing_contracts.py \
     python/portfolio/tests/test_terminal_runtime_contracts.py \
     python/portfolio/tests/test_policy_engine.py \
     python/portfolio/tests/test_policy_context.py \
     python/portfolio/tests/test_business_review_and_value_trap.py \
     python/portfolio/tests/test_personal_finance.py \
     python/portfolio/tests/test_buffett_munger_end_to_end_integration.py \
     python/portfolio/tests/test_buffett_munger_api_integration.py \
     python/portfolio/tests/test_golden_baseline_regression.py \
     python/portfolio/tests/test_allocation_opportunity.py \
     python/portfolio/tests/test_allocation_risk_gating.py \
     python/portfolio/tests/test_allocation_semantic_invariants.py
   ```
   Result: `135 passed in 20.08s`.

2. **Frontend Production Build**:
   Command:
   ```bash
   cd frontend && npm run build
   ```
   Result: `vite v6.4.3 building for production... ✓ built in 1.25s`.

3. **Runtime Smoke Test Matrix**:
   - `GET /` → PASS (Terminal Page loads with real portfolio holdings)
   - `GET /business` → PASS (Business landing workspace with search & portfolio symbol selector)
   - `GET /business/FPT` → PASS (Business detail workspace for FPT)
   - `GET /business/ACB` → PASS (Business detail workspace for ACB)
   - `GET /business/DGC` → PASS (Business detail workspace for DGC)
   - `GET /capital` → PASS (Capital / Personal Fortress workspace with setup form when unconfigured)
   - `GET /history` → PASS (Compounding History workspace with NAV metrics & transaction log)
   - Direct Browser Navigation / F5 Refresh on all routes → PASS.

## Decisions
- Handle `/business*` as client-side dynamic routes in `fetchRoutePayload` and `resolveRoute` to support arbitrary ticker symbols without 404 route errors.
- Expose canonical routes (`/`, `/business`, `/capital`, `/history`) in primary header navigation `AppNav.jsx`.

## Result
Workspace routing and navigation fixed. All 4 Buffett/Munger primary workspaces function seamlessly across direct browser navigation, link clicks, and F5 refresh.
