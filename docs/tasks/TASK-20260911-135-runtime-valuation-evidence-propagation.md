# TASK-20260911-135: Runtime Valuation & Evidence Propagation Repair

**Status**: completed  
**Priority**: High  
**Date**: 2026-09-11  
**Author**: Antigravity Agent  

---

## Requirement

Trace and repair the runtime valuation and quantitative evidence propagation path in QPort (`lap14tclc2/shannon_allocation`).

Specifically:
- Fix the contradiction where verified Finance DB facts (388 symbols `Valuation READY`) fail to propagate through `valuation_snapshot_from_catalog()`, `build_canonical_valuation()`, `build_decision_context()`, and `runtime_decision()`, resulting in false `VALUATION_UNAVAILABLE` and `VALUE_TRAP_INSUFFICIENT` blockers for golden symbols (`ACB`, `DGC`, `FPT`, `VIX`).
- Ensure `valuation_readiness_audit` and provider precedence correctly handle SSI primary facts without treating benign cross-provider variance (SSI vs TCBS) as a `CANONICAL_FACT_CONFLICT` that blocks valuation.
- Ensure ValueTrap quantitative evidence (CFO, earnings quality, debt, dilution, margins) propagates cleanly without requiring qualitative BusinessReview evidence.
- Preserve Task 134 decision precedence: `BusinessReview = UNKNOWN` resolves to `REVIEW_BUSINESS`, but quantitative Valuation (Base IV, Bear IV, Bull IV, MOS) and ValueTrap quantitative status must be correctly calculated and exposed in the context and API payloads.

---

## Context

Task 132B established real PostgreSQL canonical facts (`qport_finance.canonical_facts` with 117,759 SSI facts across 390 symbols).
Task 134 finalized decision precedence. However, during the Task 134 audit, calling `runtime_decision()` for `ACB`, `DGC`, `FPT`, and `VIX` produced `VALUATION_UNAVAILABLE` and `VALUE_TRAP_INSUFFICIENT` because `valuation_snapshot_from_catalog()` flagged `CANONICAL_FACT_CONFLICT` when both SSI and TCBS provided facts for the same period.

Because SSI has explicit primary provider precedence over TCBS, the presence of TCBS fallback facts when a valid SSI fact is available should NOT trigger a valuation block or destroy canonical valuation.

---

## Acceptance Criteria

- [x] Broken runtime boundaries identified and documented before code edits.
- [x] Reproduction table generated comparing `valuation_readiness_audit`, `valuation_snapshot_from_catalog`, `build_canonical_valuation`, `BusinessReview`, `ValueTrap`, `build_decision_context`, and `runtime_decision`.
- [x] Deterministic provider resolver selects SSI primary fact when present without treating cross-provider scale/source variance as `CANONICAL_FACT_CONFLICT`.
- [x] `valuation_snapshot_from_catalog` and `build_canonical_valuation` produce valid valuation reports for `ACB`, `DGC`, `FPT`, `VIX` from PostgreSQL facts.
- [x] `InvestmentDecisionContext` and `runtime_decision()` preserve Bear IV, Base IV, Bull IV, MOS, and ValueTrap quantitative verdicts.
- [x] Archetype-specific valuation paths work as designed:
  - `ACB` uses `BANK` (RIM / equity model, no CFO/CapEx penalty).
  - `DGC` uses `NORMAL_ENTERPRISE` / cyclical.
  - `FPT` uses `NORMAL_ENTERPRISE` (Owner Earnings).
  - `VIX` uses `SECURITIES` archetype.
- [x] ValueTrap quantitative assessment operates independently from qualitative BusinessReview evidence (does NOT return `INSUFFICIENT_DATA` solely because qualitative Moat/Management is `UNKNOWN`).
- [x] Task 134 decision precedence preserved: `BusinessReview = UNKNOWN` still yields `REVIEW_BUSINESS`, but quantitative valuation and MOS are fully computed and exposed in the API.
- [x] Terminal (`/api/portfolio/terminal`) and Business (`/api/portfolio/business/{symbol}`) endpoints return identical, complete valuation and decision payloads.
- [x] Comprehensive evidence-gap report `docs/reports/runtime-valuation-evidence-propagation-audit.md` generated.
- [x] Regression test suite `python/portfolio/tests/test_runtime_valuation_propagation.py` created and passing.
- [x] All existing test suites pass.
- [x] Frontend build (`npm run build`) passes cleanly.

---

## Constraints and Invariants

1. **Deterministic Provider Precedence**: SSI primary if valid SSI fact exists -> TCBS fallback otherwise. No provider averaging.
2. **No False Conflicts**: Cross-provider source variance must not block valuation when primary SSI fact is valid.
3. **FY-Only Data**: No quarterly data dependencies for valuation readiness.
4. **Preserve Task 134 Precedence**: `Business UNKNOWN` yields `REVIEW_BUSINESS`. Do not alter precedence logic.
5. **No Metric Fabrication**: Do not hardcode intrinsic values, MOS, or qualitative ratings.
6. **No API Duplication**: Exactly one canonical valuation pipeline.

---

## Implementation Tasks

- [x] Step 1: Execute step-by-step diagnostic reproduction across golden symbols and generate pre-fix breakdown table.
- [x] Step 2: Trace end-to-end data pipeline for FPT and identify broken boundary.
- [x] Step 3: Audit canonical line-item code mapping and provider conflict resolution in `finance_catalog.py`.
- [x] Step 4: Refactor `finance_catalog.py` to distinguish `SOURCE_VARIANCE` from blocking `CANONICAL_FACT_CONFLICT` when primary SSI fact exists.
- [x] Step 5: Audit ValueTrap builder (`value_trap.py`) to ensure quantitative metrics propagate independently of qualitative evidence.
- [x] Step 6: Verify context builder (`context_builder.py`) and service endpoints propagate Bear/Base/Bull IV, MOS, and data readiness correctly.
- [x] Step 7: Create audit report `docs/reports/runtime-valuation-evidence-propagation-audit.md`.
- [x] Step 8: Create regression test file `python/portfolio/tests/test_runtime_valuation_propagation.py`.
- [x] Step 9: Run full test suite and verify frontend build.

---

## Related Notes

- [AGENTS.md](file:///c:/workspace/shannon_allocation/AGENTS.md)
- [TASK-20260910-132B](file:///c:/workspace/shannon_allocation/docs/tasks/TASK-20260910-132B-ssi-database-reality-check.md)
- [TASK-20260910-134](file:///c:/workspace/shannon_allocation/docs/tasks/TASK-20260910-134-final-buffett-munger-decision-precedence.md)
- [Audit Report](file:///c:/workspace/shannon_allocation/docs/reports/runtime-valuation-evidence-propagation-audit.md)

---

## Validation Evidence

Executed test suite:
```bash
$env:DATABASE_URL="postgresql://qport:qport@127.0.0.1:5432/qport"; & "$env:USERPROFILE\.venv\Scripts\python.exe" -m pytest -o pythonpath=python python/portfolio/tests/test_ssi_canonical_cutover.py python/portfolio/tests/test_ssi_bulk_ingestion.py python/portfolio/tests/test_policy_engine.py python/portfolio/tests/test_policy_context.py python/portfolio/tests/test_business_review_and_value_trap.py python/portfolio/tests/test_buffett_munger_end_to_end_integration.py python/portfolio/tests/test_buffett_munger_api_integration.py python/portfolio/tests/test_golden_baseline_regression.py python/portfolio/tests/test_qualitative_evidence.py python/portfolio/tests/test_decision_precedence.py python/portfolio/tests/test_runtime_valuation_propagation.py
```
Output: `82 passed in 19.34s`

Executed frontend build:
```bash
npm run build
```
Output: `built in 1.15s`

---

## Decisions

1. **Deterministic Primary Selection over False Conflicts**: `finance_catalog.py` selects SSI primary facts whenever valid SSI facts exist. Cross-provider variance between SSI and TCBS is logged as `SOURCE_VARIANCE` in audit warnings rather than dropping facts as `CANONICAL_FACT_CONFLICT`.
2. **Archetype Fact Requirements**: `BANK` and `SECURITIES` archetypes are audited against financial-appropriate facts, excluding industrial CFO/inventory requirements.
3. **Quantitative ValueTrap Independence**: ValueTrap quantitative assessment operates on financial metrics without requiring qualitative Moat or Management evidence.

---

## Result

- Root causes of false `VALUATION_UNAVAILABLE` and `VALUE_TRAP_INSUFFICIENT` identified and repaired.
- Golden symbols (`ACB`, `DGC`, `FPT`, `VIX`) produce valid canonical valuations (`READY`) and `CLEAR` ValueTrap assessments.
- Task 134 decision precedence preserved (`Business UNKNOWN` yields `REVIEW_BUSINESS` with quantitative valuation and MOS fully exposed).
- Evidence propagation audit report published at `docs/reports/runtime-valuation-evidence-propagation-audit.md`.
