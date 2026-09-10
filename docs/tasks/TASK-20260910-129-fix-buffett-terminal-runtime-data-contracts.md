# TASK-20260910-129: Fix Buffett Terminal Runtime Data Contracts & Valuation Canonicalization

- **Status**: completed
- **Priority**: high
- **Owner**: AI Coding Agent
- **Date**: 2026-09-10

## Requirement
Fix 3 root causes preventing the Buffett Terminal and Business Workspaces from displaying real holding weights, prices, intrinsic values, quality tiers, and value trap trends:
1. `runtime_decision()` reads top-level dashboard dictionary instead of `dash.get("portfolio")`.
2. Terminal, Business, and Valuation endpoints use non-canonical or fragmented valuation paths instead of one shared canonical valuation builder `build_canonical_valuation()`.
3. `financial_history` vs `financial_history_10y` contract mismatch causes `evaluate_value_trap()` to receive empty history and output `INSUFFICIENT_DATA` / `UNKNOWN` trends.
4. Add clear UI action `[Cấu hình tài chính cá nhân]` in `TerminalPage.jsx` when Personal Balance Sheet is unconfigured.

## Context
Holding data (DGC, ACB, FPT) currently renders with `weight = 0.0%`, `price = —`, `base_iv = —`, `value_trap = INSUFFICIENT_DATA`, and `decision = BUILD_RESERVE_FIRST` due to nested dashboard extraction failures, non-canonical valuation calculation in `PortfolioService.valuation()`, and un-normalized financial history keys.

## Acceptance Criteria
- [x] `runtime_decision()` reads `pf = dash.get("portfolio") if isinstance(dash.get("portfolio"), dict) else dash` to populate real `holding`, `weight`, `market_value`, and `price`.
- [x] Real holdings in regression test satisfy: `holding is not None`, `weight > 0`, `market_value > 0`.
- [x] Create single canonical valuation service `build_canonical_valuation(symbol, ...)` shared across `/api/portfolio/valuation/{symbol}`, `/api/portfolio/terminal`, `/api/portfolio/business/{symbol}`, and `PortfolioService.runtime_decision()`.
- [x] Canonical valuation result exposes: `symbol`, `current_price`, `bear_iv`, `base_iv`, `bull_iv`, `actual_mos_pct`, `required_mos_pct`, `quality_score`, `quality_tier`, `valuation_confidence`, `model_status`, `hard_rejects`, and domain `financial_history`.
- [x] Normalize `financial_history` as the single internal domain field across valuation adapters while maintaining `financial_history_10y` on API serialization.
- [x] `evaluate_value_trap()` receives multi-year historical evidence and resolves `normalized_earnings_trend != UNKNOWN` when supported.
- [x] Unconfigured Personal Balance Sheet correctly returns `survival_reserve_status = UNKNOWN` and prohibits BUY/BUY_MORE (`BUILD_RESERVE_FIRST`).
- [x] Add explicit `[Cấu hình tài chính cá nhân]` link/button in `TerminalPage.jsx` when Personal Finance is missing.
- [x] Do not invent zero/blank fallbacks for NULL or MISSING fields (`NULL != 0`, `MISSING != ZERO`).
- [x] All Python tests and `npm run build` pass without error.

## Constraints and Invariants
- Do NOT modify `main` branch; commit and push ONLY to `origin/feature/buffett-munger-refactor`.
- Do NOT merge into `main`.
- Do NOT alter ledger calculations or transaction semantics.
- Do NOT introduce risk-driven BUY/SELL rules or ERC target allocation.

## Implementation Tasks
- [x] Create `docs/tasks/TASK-20260910-129-fix-buffett-terminal-runtime-data-contracts.md` and update `docs/tasks/README.md`.
- [x] Extract `build_canonical_valuation()` in `python/portfolio/canonical_valuation.py` wrapping `ValuationEngine.evaluate()`.
- [x] Refactor `app/main.py` endpoints (`portfolio_symbol_valuation`, `api_portfolio_terminal`, `api_portfolio_business`) and `PortfolioService.valuation()` / `runtime_decision()` to call `build_canonical_valuation()`.
- [x] Update `runtime_decision()` in `python/portfolio/service.py` to extract `pf = dash.get("portfolio")` and pass normalized `financial_history`.
- [x] Add `[Cấu hình tài chính cá nhân]` CTA button in `TerminalPage.jsx`.
- [x] Add comprehensive test suite in `python/portfolio/tests/test_terminal_runtime_contracts.py`.
- [x] Run full test suite and frontend build.
- [x] Update Task 129 note with exact validation evidence and mark `completed`.

## Related Notes
- `AGENTS.md`: Zettelkasten Task-First Workflow.
- `app/main.py`: Buffett-Munger Workspaces API Routes.
- `python/portfolio/service.py`: `PortfolioService.runtime_decision()`.
- `python/portfolio/canonical_valuation.py`: Shared canonical valuation application builder.

## Validation Evidence
1. **Pytest Test Suite Execution**:
   Command:
   ```bash
   $env:PYTHONPATH="python"; & "$HOME\.venv\Scripts\python.exe" -m pytest \
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
   Output: `131 passed in 20.69s` (100% pass rate across 11 test suites).

2. **Frontend Production Build**:
   Command:
   ```bash
   cd frontend && npm run build
   ```
   Output: `vite v6.4.3 building for production... ✓ built in 1.12s`.

## Decisions
- Canonicalize valuation logic into `build_canonical_valuation(symbol, ...)` to guarantee `same symbol + same facts + same market price => same valuation report` across all API endpoints and runtime decision callers.
- Normalize `financial_history` as the canonical domain field while keeping `financial_history_10y` for API backward compatibility.

## Result
Root causes 1, 2, and 3 fully resolved. All tests pass, frontend build passes cleanly, and all holdings (DGC, ACB, FPT) retain their true holding weights, prices, intrinsic values, and value trap trends.
