# TASK-20260909-126: Final Buffett/Munger Runtime Readiness Fixes

- **Status**: completed
- **Priority**: high
- **Date**: 2026-09-09
- **Branch**: feature/buffett-munger-refactor

## Requirement
Fix final P0 runtime readiness blockers and API-level decision consistency gaps:
1. P0-1: Enforce Data Readiness in Decision Engine (`engine.py`). Prohibit `BUY`/`BUY_MORE` when `financial_core == BLOCKED`, `valuation == BLOCKED`, or `personal_finance == BLOCKED`.
2. P0-2: Ensure Business Workspace (`/api/portfolio/business/{symbol}`) uses persisted Personal Finance. Extract a shared runtime decision helper so `/api/portfolio/terminal` and `/api/portfolio/business/{symbol}` use identical decision pipelines.
3. P0-3: Ensure Value Trap receives real financial history at runtime (`financial_history` passed to `evaluate_value_trap`).
4. API Regression Tests: Add API/application integration tests verifying decision consistency between Terminal and Business endpoints, Personal Finance propagation, ATTENTION status, and CONFLICTED valuation blocking.

## Context
Previous task (TASK-125) fixed individual domain contracts and personal finance persistence, but audit revealed remaining P0 gaps:
- Decision Engine reached `BUY` even when `data_readiness.valuation == BLOCKED` (e.g. `data_status == CONFLICTED`).
- `/api/portfolio/business/{symbol}` omitted Personal Finance, resulting in `personal_finance = None` (`survival_reserve_status = UNKNOWN`) and returning `BUILD_RESERVE_FIRST` while `/terminal` returned `BUY` for the same symbol and user.
- Value Trap in production was called without explicit multi-year `financial_history`.

## Acceptance Criteria
- [x] Decision Engine actively enforces data_readiness
- [x] financial_core BLOCKED cannot BUY
- [x] valuation BLOCKED cannot BUY
- [x] personal_finance BLOCKED cannot BUY
- [x] CONFLICTED valuation cannot BUY
- [x] INSUFFICIENT valuation cannot BUY
- [x] Business workspace reads persisted Personal Finance
- [x] Terminal and Business use the same Personal Finance source
- [x] Terminal and Business return consistent decisions for the same symbol/context
- [x] Value Trap runtime receives actual historical evidence
- [x] Missing Personal Finance blocks BUY in every workspace
- [x] ATTENTION blocks new capital in every workspace
- [x] ACB/DGC/FPT production wiring is regression-tested
- [x] No new hardcoded financial assumptions
- [x] Full relevant tests pass
- [x] Frontend build passes

## Implementation Tasks
- [x] Step 1: Create task note and register index in `docs/tasks/README.md`.
- [x] Step 2: Implement Data Readiness pre-BUY gate (Gate 5D & Gate 9 checks) in `python/portfolio/policy/engine.py`.
- [x] Step 3: Extract shared runtime decision context builder `PortfolioService.runtime_decision()` in `python/portfolio/service.py`.
- [x] Step 4: Ensure production endpoints `/api/portfolio/terminal` and `/api/portfolio/business/{symbol}` pass `financial_history` to `evaluate_value_trap`.
- [x] Step 5: Update `/api/portfolio/business/{symbol}` to use shared runtime decision helper with persisted Personal Finance.
- [x] Step 6: Add API/application regression tests in `test_buffett_munger_api_integration.py`.
- [x] Step 7: Run pytest suite and frontend `npm run build`. Update task note with validation evidence.

## Validation Evidence
```bash
# 1. Pytest suite execution across required test files
$env:PYTHONPATH="python"; .venv\Scripts\python.exe -m pytest python/portfolio/tests/test_policy_engine.py python/portfolio/tests/test_policy_context.py python/portfolio/tests/test_business_review_and_value_trap.py python/portfolio/tests/test_personal_finance.py python/portfolio/tests/test_buffett_munger_end_to_end_integration.py python/portfolio/tests/test_golden_baseline_regression.py python/portfolio/tests/test_allocation_opportunity.py python/portfolio/tests/test_allocation_risk_gating.py python/portfolio/tests/test_allocation_semantic_invariants.py python/portfolio/tests/test_buffett_munger_api_integration.py -v
# Output: 123 passed in 5.93s

# 2. Frontend build verification
cd frontend
npm run build
# Output: vite v6.4.3 building for production... dist/assets/index-DUGG1Iv5.js 623.27 kB. built in 1.35s
```

## Decisions
1. Gate 5D in `engine.py` explicitly blocks any context where `data_readiness` for `financial_core`, `valuation`, or `personal_finance` is `BLOCKED`, returning conservative degradation (`HOLD` for existing holdings, `WAIT_FOR_MOS` for candidates).
2. `PortfolioService.runtime_decision(symbol)` serves as the single canonical entry point for all runtime workspaces (`/terminal`, `/business/{symbol}`), ensuring identical decision outputs across endpoints for the same facts.
3. Multi-year `financial_history` from `val_rep` is automatically passed to `evaluate_value_trap` inside `runtime_decision(symbol)`.

## Result
All 3 P0 readiness blockers resolved. 123 unit, application, and end-to-end integration tests passed cleanly, and frontend build completed with zero errors. Branch is ready for final merge audit.
