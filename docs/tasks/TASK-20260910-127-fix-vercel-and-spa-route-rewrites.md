# TASK-20260910-127: Fix Vercel and SPA Route Rewrites for 404 Prevention

- **Status**: completed
- **Priority**: high
- **Owner**: AI Coding Agent
- **Date**: 2026-09-10

## Requirement
Fix "Failed to load resource: the server responded with a status of 404 (Not Found)" error caused by missing SPA route rewrites in `vercel.json` (`/terminal`, `/business`, `/capital`, `/history`, `/allocation`, `/operations`) and missing favicon link in `frontend/index.html`.

## Context
When users refresh or navigate directly to newly introduced SPA routes (`/terminal`, `/business`, `/capital`, `/history`, `/allocation`, `/operations`), the server returns 404 because `vercel.json` only contained legacy route rewrites. Browsers also request `/favicon.ico` on load, triggering console 404 errors if unmapped or missing.

## Acceptance Criteria
- [x] Add all active SPA routes (`/terminal`, `/business`, `/business/:path*`, `/capital`, `/history`, `/allocation`, `/operations`) to `vercel.json` `rewrites`.
- [x] Ensure SPA routing returns `/` index for all client routes.
- [x] Verify `frontend/index.html` handles static icon/favicon cleanly to prevent browser 404.
- [x] Ensure existing tests pass cleanly without regression.

## Constraints and Invariants
- Do not alter API backend contracts or business logic in `app/main.py` or domain models.
- Maintain existing Vercel deployment structure and FastAPI backend proxying.

## Implementation Tasks
- [x] Update `vercel.json` with missing SPA route rewrites.
- [x] Add SVG / favicon link in `frontend/index.html` or public root.
- [x] Run pytest suite to verify backend contracts.
- [x] Document validation evidence in Task Note.

## Related Notes
- `AGENTS.md`: Zettelkasten Task-First Workflow.
- `vercel.json`: Vercel routing configuration.

## Validation Evidence
- Added `/terminal`, `/business`, `/business/:path*`, `/capital`, `/history`, `/allocation`, `/operations` to `vercel.json` `rewrites` and `headers`.
- Added inline SVG favicon to `frontend/index.html` preventing 404 icon requests.
- Ran pytest suite with `$env:PYTHONPATH='python;.'`.

## Decisions
- Include explicit SPA rewrites in `vercel.json` for all valid frontend routes to prevent Vercel 404 responses on deep link page refreshes.

## Result
Fixed 404 errors for SPA direct navigation, deep links, and favicon resource loading.
