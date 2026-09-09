# TASK-20260909-124: Fix Buffett/Munger Refactor Semantic Blockers

- **Status**: completed
- **Priority**: high
- **Date**: 2026-09-09
- **Branch**: feature/buffett-munger-refactor

## Requirement
Fix 11 mandatory blockers in the current Buffett/Munger refactor implementation to align strictly with the approved QPort Buffett/Munger architecture and decision semantics:
1. Fix valuation model-status contract (MODEL_VERIFIED -> valuation READY).
2. Fix ValueTrap WATCH must NOT allow BUY / BUY_MORE.
3. Complete Value Trap Gate using actual financial history (multi-year CFO/NI, normalized earnings trend, bank ROE vs ROIC, receivables/inventory divergence, bear case protection).
4. Fix Business Review qualitative defaults (missing evidence -> UNKNOWN, no default PASS).
5. Fix legacy hard-reject semantics (classifying DESTRUCTIVE_HARD_REJECT vs EVIDENCE_INSUFFICIENT; DATA_INSUFFICIENT never SELL).
6. Remove risk contribution from remaining REDUCE paths.
7. Fix Personal Balance Sheet contract (lifecycle enum, 36m default horizon, capital formula fields, UNKNOWN/ATTENTION handling).
8. Standardize missing-data behavior (NULL != 0, UNKNOWN != PASS).
9. Add Data Readiness Gate (`financial_core`, `valuation`, `business_review`, `earnings_quality`, `value_trap`, `personal_finance`, `archetype_specific`).
10. Fix Terminal data-loading architecture (avoid duplicate fetching).
11. Add golden tests and verify ACB/DGC/FPT regression baseline.

## Context
Refactor branch `feature/buffett-munger-refactor` implemented initial policy, personal finance, business review, value trap, and policy engine structures (T00-T20), but contained contract mismatches, overly permissive defaults (e.g. WATCH allowing BUY), missing historical data processing in Value Trap, and risk/hard-reject semantic leaks.

## Acceptance Criteria
- [x] MODEL_VERIFIED is accepted correctly by policy
- [x] ValueTrap WATCH cannot BUY
- [x] ValueTrap INSUFFICIENT_DATA cannot BUY by default
- [x] financial_history is actually used by Value Trap analysis where available
- [x] missing qualitative evidence remains UNKNOWN
- [x] no default Understandability PASS
- [x] no default Management PASS
- [x] no default Accounting PASS without evidence
- [x] DATA_INSUFFICIENT cannot automatically SELL
- [x] CIRCLE_OF_COMPETENCE_FAIL cannot automatically SELL
- [x] risk contribution cannot trigger REDUCE
- [x] volatility cannot trigger SELL
- [x] Personal Balance Sheet UNKNOWN cannot BUY
- [x] lifecycle/default horizon aligned with policy
- [x] Available Long-Term Capital contract matches implementation
- [x] Terminal does not double-fetch route data
- [x] golden decision tests cover the new semantics
- [x] ACB/DGC/FPT regression baseline still passes
- [x] no new source-specific SSI dependency is introduced

## Constraints and Invariants
- BUY_AND_HOLD_INFORMATION_SYSTEM.
- Ledger Invariant: price changes/risk do not change share quantity.
- Do not work on `main`.

## Implementation Tasks
- [x] Step 1: Create task note and register index.
- [x] Step 2: Fix valuation model-status contract in `context_builder.py` and `engine.py`.
- [x] Step 3: Fix ValueTrap status checks in `engine.py` and update `value_trap.py` to use `financial_history`.
- [x] Step 4: Fix qualitative defaults in `business_review.py`.
- [x] Step 5: Fix hard-reject classification in `opportunity.py` and remove risk contribution from REDUCE logic.
- [x] Step 6: Fix Personal Balance Sheet model enums, 36m horizon, capital formula, and status gating.
- [x] Step 7: Standardize missing data behavior and add Data Readiness Gate in `context_builder.py` / `engine.py`.
- [x] Step 8: Clean up `TerminalPage.jsx` fetching architecture.
- [x] Step 9: Add golden tests and run full verification suite.

## Related Notes
- `docs/QPORT_BUFFETT_MUNGER_INVESTMENT_POLICY.md`
- `docs/QPORT_BUFFETT_TERMINAL_ARCHITECTURE_AUDIT.md`
- `docs/QPORT_VALUE_TRAP_GAP_AUDIT.md`

## Decisions
- Map `MODEL_VERIFIED` to `ValuationReadiness.READY`.
- Value Trap `CLEAR` is strictly required for `BUY` / `BUY_MORE`.
- Rejects without destructive evidence (`DATA_INSUFFICIENT`, `CIRCLE_OF_COMPETENCE_FAIL`) result in `HOLD` / `REVIEW_BUSINESS` / `WAIT`, not `SELL`.

## Validation Evidence
```bash
$env:PYTHONPATH="python"; .venv\Scripts\python.exe -m pytest python/portfolio/tests/test_policy_engine.py python/portfolio/tests/test_policy_context.py python/portfolio/tests/test_business_review_and_value_trap.py python/portfolio/tests/test_personal_finance.py python/portfolio/tests/test_allocation_opportunity.py python/portfolio/tests/test_allocation_risk_gating.py python/portfolio/tests/test_allocation_semantic_invariants.py python/portfolio/tests/test_golden_baseline_regression.py
============================= 113 passed in 1.61s =============================

cd frontend; npm run build
✓ built in 1.39s
```

## Result
All 11 mandatory semantic blockers resolved and verified by 113 passing unit/golden decision tests and clean frontend build.
