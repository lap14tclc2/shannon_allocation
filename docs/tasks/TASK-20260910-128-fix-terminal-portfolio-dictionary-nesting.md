# TASK-20260910-128: Fix Terminal Workspace Portfolio Dictionary Nesting

- **Status**: completed
- **Priority**: high
- **Owner**: AI Coding Agent
- **Date**: 2026-09-10

## Requirement
Fix missing holdings matrix data on `/terminal`, `/capital`, and `/history` endpoints caused by incorrectly querying top-level `dash.get("positions")` instead of nested `dash.get("portfolio", {}).get("positions")`.

## Context
`svc.dashboard()` returns a structured dictionary containing `"portfolio": { "positions": [...], "cash": ..., "equity_value": ..., "nav": ... }`. `api_portfolio_terminal`, `api_portfolio_capital`, and `api_portfolio_history` in `app/main.py` were reading `dash.get("positions")` directly from the top level, resolving to `None`/`[]` and rendering 0 positions in the UI.

## Acceptance Criteria
- [x] Update `api_portfolio_terminal` to read `pf = dash.get("portfolio") or {}` then extract `positions`, `cash`, and `equity`.
- [x] Update `api_portfolio_capital` to read `pf = dash.get("portfolio") or {}` for `cash` and `equity`.
- [x] Update `api_portfolio_history` to read `pf = dash.get("portfolio") or {}` for summary NAV and cost metrics.
- [x] Verify `/api/portfolio/terminal` returns user holdings matrix correctly when positions exist.

## Constraints and Invariants
- Maintain `AutomatedPortfolioService.dashboard()` contract structure.
- Do not alter underlying ledger events or accounting calculations.

## Implementation Tasks
- [x] Fix portfolio dict extraction in `app/main.py` (`api_portfolio_terminal`, `api_portfolio_capital`, `api_portfolio_history`).
- [x] Run python tests / API checks to verify holdings matrix populates correctly.
- [x] Document validation evidence in Task Note.

## Related Notes
- `app/main.py`: Buffett-Munger Workspaces API Routes.

## Validation Evidence
- Extracted `pf = dash.get("portfolio") if isinstance(dash.get("portfolio"), dict) else dash` in `api_portfolio_terminal`, `api_portfolio_capital`, and `api_portfolio_history` in `app/main.py`.
- Tested position extraction against `qport_user_2` (Alice's portfolio 1), correctly recovering positions (`DGC`, `ACB`, `FPT`).

## Decisions
- Extract `pf = dash.get("portfolio") or {}` across all workspace endpoints for dictionary schema compatibility.

## Result
Holdings matrix and portfolio summary data correctly populates across Terminal, Capital, and History workspaces.
