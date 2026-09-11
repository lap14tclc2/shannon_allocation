# TASK-20260910-134: Final Buffett-Munger Decision Precedence Policy Engine

**Status**: completed  
**Priority**: High  
**Date**: 2026-09-10  
**Author**: Antigravity Agent  

---

## ## Requirement

Finalize and lock the canonical deterministic Buffett/Munger decision policy precedence engine in QPort (`lap14tclc2/shannon_allocation`).

The decision engine must strictly distinguish between:
1. Business quality & eligibility (`REVIEW_BUSINESS`, `AVOID`, `SELL_REVIEW`)
2. Business uncertainty & evidence readiness (`REVIEW_BUSINESS`)
3. Value trap risk (`AVOID`, `SELL_REVIEW`, `REVIEW_BUSINESS`)
4. Valuation & Margin of Safety (`WAIT_FOR_MOS`, `HOLD`)
5. Personal financial capacity (`BUILD_RESERVE_FIRST`, `HOLD_NO_NEW_CAPITAL`)
6. Position capacity & limits (`HOLD_NO_NEW_CAPITAL`)
7. Existing holding vs new candidate state (`HOLD`, `HOLD_NO_NEW_CAPITAL`, `SELL_REVIEW`, `SELL`)

Fix semantic ambiguity where `BusinessReview = UNKNOWN` fell back to `WAIT_FOR_MOS` or other valuation/price checks. `WAIT_FOR_MOS` must mean strictly: "The business is sufficiently investable, but price is not attractive enough." It MUST NOT mean "We do not know whether the business is investable."

---

## ## Context

Task 132B established SSI/TCBS canonical database fact cutover and verified PostgreSQL runtime state.
Task 133 established the qualitative-evidence framework. Real qualitative state for symbols (such as ACB, DGC, FPT, VIX) may legitimately contain `UNKNOWN` dimensions (`Understandability = UNKNOWN`, `Moat = UNKNOWN`, `Management = UNKNOWN`, `Accounting qualitative = UNKNOWN`, `Circle of Competence = UNKNOWN`).

Currently:
- `evaluate_decision` in `python/policy/engine.py` evaluates gates, but when `business_review_status` is `UNKNOWN`, it fell through to valuation/MOS gates, resulting in `WAIT_FOR_MOS` when price was above MOS.
- Multiple unresolved blocking reasons were not systematically tracked or surfaced (e.g. `BUSINESS_REVIEW_INCOMPLETE` + `PERSONAL_BALANCE_SHEET_UNKNOWN`).
- Canonical blocking reason codes and evidence structure needed standardization with `primary_reason` and `blocking_reasons[]`.

---

## ## Acceptance Criteria

- [x] Exactly ONE canonical decision authority exists (`evaluate_decision` in `python/portfolio/policy/engine.py`). Frontend and API components consume this output directly without re-deriving decisions.
- [x] Explicit decision precedence documented and implemented:
  1. Solvency/Accounting/Structural Failure (`AVOID` / `SELL_REVIEW` / `SELL`)
  2. Business Eligibility & Evidence Readiness (`REVIEW_BUSINESS` if incomplete/UNKNOWN, `AVOID` / `SELL_REVIEW` if FAIL)
  3. Value Trap Status (`AVOID` / `SELL_REVIEW` / `REVIEW_BUSINESS`)
  4. Valuation Readiness & Base IV (`WAIT_FOR_MOS` / `HOLD` if invalid/missing)
  5. Margin of Safety Gate (`WAIT_FOR_MOS` for candidate, `HOLD` for holding)
  6. Personal Balance Sheet Gate (`BUILD_RESERVE_FIRST` if unconfigured/unsafe)
  7. Position Capacity Gate (`HOLD_NO_NEW_CAPITAL` if capacity exceeded)
  8. Qualified Allocation Action (`BUY` for candidate, `BUY_MORE` for holding)
- [x] Mandatory invariant: `BusinessReview = UNKNOWN` CANNOT become `WAIT_FOR_MOS`, `BUY`, or `BUY_MORE` regardless of MOS or price.
- [x] `WAIT_FOR_MOS` strictly enforced only when business eligibility is established (PASS/WATCH), ValueTrap acceptable (CLEAR), valuation valid, and personal capital permits investment.
- [x] `ValueTrap CLEAR != BUY`: `CLEAR` means no evidence of value trap, not a qualification for `BUY`. `ValueTrap HIGH_RISK` blocks BUY/BUY_MORE.
- [x] Personal Balance Sheet (`PBS`) constrains capital allocation without redefining business quality:
  - Business PASS + PBS UNKNOWN -> `BUILD_RESERVE_FIRST`
  - Business UNKNOWN + PBS UNKNOWN -> `REVIEW_BUSINESS` with PBS blocker retained in `blocking_reasons`
  - Business FAIL + PBS UNKNOWN -> `AVOID` / `SELL_REVIEW`
- [x] Canonical blocking reason codes introduced/reused:
  `BUSINESS_REVIEW_INCOMPLETE`, `UNDERSTANDABILITY_UNKNOWN`, `MOAT_UNKNOWN`, `MANAGEMENT_EVIDENCE_UNKNOWN`, `ACCOUNTING_RELIABILITY_UNKNOWN`, `CIRCLE_OF_COMPETENCE_UNKNOWN`, `VALUE_TRAP_HIGH_RISK`, `VALUE_TRAP_INSUFFICIENT`, `VALUATION_UNAVAILABLE`, `MOS_INSUFFICIENT`, `PERSONAL_BALANCE_SHEET_UNKNOWN`, `SURVIVAL_RESERVE_INSUFFICIENT`, `POSITION_CAP_REACHED`, `STRUCTURAL_DETERIORATION`, `SOLVENCY_FAILURE`, `ACCOUNTING_FAILURE`.
- [x] Preserved multiple blocking reasons in `DecisionEvidence` (`primary_reason`, `blocking_reasons[]`).
- [x] Candidate vs existing holding decision matrix implemented cleanly.
- [x] Missing qualitative evidence (`UNKNOWN`) does not trigger `SELL` (yields `REVIEW_BUSINESS`).
- [x] Price decline (-50%), position overweight, and MOS shrinking do NOT trigger automatic `SELL`.
- [x] `HOLD` and `HOLD_NO_NEW_CAPITAL` work cleanly for existing holdings.
- [x] `AVOID` and `SELL_REVIEW` semantics strictly enforced.
- [x] `SELL` remains rare and reserved for confirmed hard exit criteria.
- [x] Decision matrix report `docs/reports/buffett-munger-decision-matrix.md` generated covering all decision enums and scenario combinations.
- [x] Mandatory scenario tests (A through J) implemented and passing in `python/portfolio/tests/test_decision_precedence.py`.
- [x] Real runtime golden audit report `docs/reports/buffett-munger-final-decision-audit.md` generated for `ACB`, `DGC`, `FPT`, `VIX` using real PostgreSQL DB facts.
- [x] Terminal (`/`) and Business pages (`/business/{symbol}`) use identical decision authority & payload format.
- [x] Zero evidence fabrication (do not hardcode moats, management ratings, or convert numeric PASS to qualitative PASS).
- [x] Zero SSI ingestion changes, zero quarterly dependencies, zero risk-contribution/ERC regression.
- [x] All unit and integration test suites pass (`pytest` / `python -m pytest`).
- [x] Frontend build (`npm run build`) passes cleanly if frontend files are modified.

---

## ## Constraints and Invariants

1. **Buy & Hold Philosophy**: `BUY_AND_HOLD_INFORMATION_SYSTEM`. Observation and explanation only.
2. **Ledger Invariant**: Market price, risk, or time passage never alters share counts.
3. **Single Policy Authority**: Exactly one engine (`python/portfolio/policy/engine.py`).
4. **UNKNOWN != FAIL**: Missing evidence is not failure.
5. **No Evidence Fabrication**: Qualitative UNKNOWNs remain UNKNOWN.
6. **FY-Only Data**: No quarterly data dependencies.
7. **No Portfolio-Risk Regression**: No ERC, VaR, CVaR, or volatility mixed into investment policy decisions.

---

## ## Implementation Tasks

- [x] Audit decision path across backend and frontend to ensure single authority.
- [x] Define canonical blocking reason enum & update `DecisionEvidence` model to include `primary_reason` and `blocking_reasons`.
- [x] Refactor `python/portfolio/policy/engine.py` precedence logic to follow strict multi-gate waterfall preserving all blockers.
- [x] Update `context_builder.py` to populate data readiness and granular blocking reason codes.
- [x] Create decision matrix report `docs/reports/buffett-munger-decision-matrix.md`.
- [x] Create comprehensive precedence test suite `python/portfolio/tests/test_decision_precedence.py` covering Scenarios A-J and core invariants.
- [x] Update existing tests to align with new explicit `primary_reason` and `blocking_reasons` structure.
- [x] Conduct real runtime audit on PostgreSQL DB for `ACB`, `DGC`, `FPT`, `VIX` and write `docs/reports/buffett-munger-final-decision-audit.md`.
- [x] Verify Terminal (`/`) and Business (`/business/{symbol}`) pages consistency.
- [x] Run full test suite and verify frontend build.

---

## ## Related Notes

- [AGENTS.md](file:///c:/workspace/shannon_allocation/AGENTS.md)
- [TASK-20260910-132B](file:///c:/workspace/shannon_allocation/docs/tasks/TASK-20260910-132B-ssi-database-reality-check.md)
- [TASK-20260910-133](file:///c:/workspace/shannon_allocation/docs/tasks/TASK-20260910-133-buffett-munger-qualitative-evidence.md)

---

## ## Validation Evidence

1. **Precedence Test Suite**: `python/portfolio/tests/test_decision_precedence.py` (13 passed in 0.59s)
   ```text
   test_scenario_a_business_unknown_attractive_mos_safe_pbs PASSED
   test_scenario_b_business_pass_mos_insufficient_candidate PASSED
   test_scenario_c_business_pass_mos_sufficient_pbs_unknown PASSED
   test_scenario_d_business_unknown_pbs_unknown_multiple_blockers PASSED
   test_scenario_e_business_fail_cheap_price_candidate PASSED
   test_scenario_f_business_fail_existing_holding PASSED
   test_scenario_g_business_pass_overweight_holding PASSED
   test_scenario_h_business_pass_mos_insufficient_holding PASSED
   test_scenario_i_price_decline_no_sell_trigger PASSED
   test_scenario_j_accounting_fail_existing_holding PASSED
   test_invariant_unknown_not_equal_to_pass PASSED
   test_invariant_valuetrap_clear_not_equal_to_buy PASSED
   test_invariant_bad_business_cannot_be_rescued_by_cheap_price PASSED
   ```
2. **Core Policy Suite**: 52 passed in 5.87s (`test_policy_engine.py`, `test_policy_context.py`, `test_business_review_and_value_trap.py`, `test_buffett_munger_end_to_end_integration.py`, `test_buffett_munger_api_integration.py`, `test_golden_baseline_regression.py`, `test_qualitative_evidence.py`).
3. **Real Runtime Audit against PostgreSQL (`qport_finance.canonical_facts`)**:
   - `ACB`: `REVIEW_BUSINESS` (Primary reason: `BUSINESS_REVIEW_INCOMPLETE`)
   - `DGC`: `REVIEW_BUSINESS` (Primary reason: `BUSINESS_REVIEW_INCOMPLETE`)
   - `FPT`: `REVIEW_BUSINESS` (Primary reason: `BUSINESS_REVIEW_INCOMPLETE`)
   - `VIX`: `REVIEW_BUSINESS` (Primary reason: `BUSINESS_REVIEW_INCOMPLETE`)
4. **Frontend Production Build**: `npm run build` completed in 1.26s (`dist/assets/index-Bkxz4NBF.js`).

---

## ## Decisions

1. **Single Authority**: `evaluate_decision()` in `python/portfolio/policy/engine.py` is the single source of truth for all decision outputs.
2. **Multi-Gate Blocking Reasons**: `DecisionEvidence` retains all blocking reasons in `blocking_reasons[]` list while exposing the top-level gate conflict as `primary_reason`.
3. **Business Review Incomplete Precedence**: `BusinessReview = UNKNOWN` takes precedence over valuation, MOS, or personal balance sheet gates, resolving strictly to `REVIEW_BUSINESS`.

---

## ## Result

Task 134 completed successfully. Canonical decision precedence locked, tested, and audited against PostgreSQL runtime database.
