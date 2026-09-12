# TASK-20260912-139 — Forensic Correctness + Canonical MOS Authority Audit

- **Status**: completed
- **Priority**: high
- **Date**: 2026-09-12
- **Branch**: feature/buffett-munger-refactor

---

## ## Requirement

1. **DGC Receivables Forensic Investigation & Repair**:
   - Audit end-to-end lineage from SSI raw XLSX / database observations (`s_bi_raw_financial_observations`) to `BS.ASSETS.RECEIVABLES`, financial history, Munger forensics, ValueTrap, and `InvestmentDecisionContext`.
   - Ensure mapping logic does not collapse subcomponents/detailed rows into aggregate `BS.ASSETS.RECEIVABLES`.
   - Evaluate whether `RECEIVABLES_GROW_FASTER_THAN_REVENUE` for DGC is `TRUE_FINANCIAL_WARNING`, `CANONICAL_MAPPING_ERROR`, `AGGREGATION_ERROR`, `PERIOD_ALIGNMENT_ERROR`, `FORMULA_ERROR`, or `INSUFFICIENT_EVIDENCE`.
   - Refactor forensic rule semantics so single multi-year fluctuations or watch-level signals distinguish `WATCH` from `FAIL` and do not automatically flag structural deterioration (`HIGH_RISK` ValueTrap -> `DETERIORATING_BUSINESS` -> `AVOID`) without persistent economic evidence.

2. **Canonical Margin of Safety (MOS) Single Authority**:
   - Establish ONE single authoritative source for required MOS across the entire system (`munger_analyzer.py`, `canonical_valuation.py`, `context_builder.py`, Business API, Terminal API, AI export).
   - Downstream components must consume the canonical `required_mos_pct` and never recompute or silently fallback (e.g. `|| 0.40`).
   - Explicit states (`MOS_READY`, `MOS_UNKNOWN`, `MOS_NOT_APPLICABLE`) must be preserved; missing MOS must remain missing (`NULL != DEFAULT`).

3. **Archetype Correctness**:
   - Ensure forensic rules are archetype-aware. Banking (`BANK`) and Securities (`SECURITIES`) must treat traditional industrial receivables/CFO rules as `NOT_APPLICABLE` rather than `FAIL` or `UNKNOWN`.

4. **Golden Symbols Verification**:
   - Verify runtime behavior and integration for golden symbols: `ACB` (Bank), `DGC` (Industrial), `FPT` (Technology/Normal), `VIX` (Securities).

---

## ## Context

- Task 138 added AI export which surfaced potential false-positive forensic warnings for DGC (`RECEIVABLES_GROW_FASTER_THAN_REVENUE`).
- Required MOS discrepancies were observed (e.g., Munger decision required MOS ≈ 40%, while canonical valuation showed required MOS ≈ 50%).
- System Invariant: Buy & Hold information system, Ledger invariant, FY-only long-term fundamental analysis, No hardcoded symbol logic, Explicit error handling without silent defaults.

---

## ## Acceptance Criteria

- [x] DGC receivables result is proven from raw SSI evidence in `docs/QPORT_FORENSIC_MOS_CORRECTNESS_AUDIT.md`.
- [x] No unsafe mapping causes detail -> aggregate collision in `BS.ASSETS.RECEIVABLES`.
- [x] Forensic rules distinguish `WATCH` from `FAIL`.
- [x] A single forensic warning (`WATCH`) cannot incorrectly escalate to `HIGH_RISK` ValueTrap or `DETERIORATING_BUSINESS` (`AVOID`).
- [x] `BANK` and `SECURITIES` archetype applicability for forensics is correct (`NOT_APPLICABLE`).
- [x] One canonical required MOS authority exists across all runtime endpoints and engines.
- [x] All runtime consumers (Munger analyzer, valuation engine, decision context, Business API, AI export) receive the exact same required MOS.
- [x] Missing MOS is never silently defaulted (`NULL != DEFAULT`).
- [x] Integration & regression tests for `ACB`, `DGC`, `FPT`, `VIX` pass.
- [x] FY-only invariant preserved. No quarterly data added or required.
- [x] No unrelated UI/risk/PBS changes.
- [x] Python test suite passes cleanly.
- [x] Frontend build (`npm run build`) passes cleanly.
- [x] `docs/QPORT_FORENSIC_MOS_CORRECTNESS_AUDIT.md` contains before/after runtime evidence.

---

## ## Constraints and Invariants

1. Do NOT merge to `main`.
2. Do NOT hardcode DGC or any other symbol.
3. Long-term analysis remains strictly FY-only (annual statements).
4. `NULL != 0`, `MISSING != SAFE`, `UNKNOWN != PASS`, `WATCH != FAIL`.
5. Maintain archetype boundaries (`BANK`, `SECURITIES`, `NORMAL`).

---

## ## Implementation Tasks

- [x] 1. Run diagnostic reproduction for `DGC`, `ACB`, `FPT`, `VIX` and create baseline report in `docs/QPORT_FORENSIC_MOS_CORRECTNESS_AUDIT.md`.
- [x] 2. Trace DGC raw SSI mapping to `BS.ASSETS.RECEIVABLES` to verify exact line codes, descriptions, mapping rules, and line aggregation.
- [x] 3. Audit and fix SSI canonical mapping for receivables if unsafe substring matching exists.
- [x] 4. Audit DGC annual financial series and evaluate forensic rule `RECEIVABLES_GROW_FASTER_THAN_REVENUE`.
- [x] 5. Refactor forensic rule severity (`WATCH` vs `FAIL`) and ValueTrap propagation (`WATCH` signal != `HIGH_RISK` ValueTrap).
- [x] 6. Ensure `BANK` and `SECURITIES` archetypes handle industrial forensic rules as `NOT_APPLICABLE`.
- [x] 7. Identify all MOS calculation/fallback locations and establish `munger_analyzer.py` / canonical valuation policy as the single MOS authority.
- [x] 8. Remove fallback MOS values (`|| 0.40`, `0.50` hardcodes) across python backend and frontend data pipeline.
- [x] 9. Add integration tests for MOS consistency and forensic correctness in `python/portfolio/tests/test_forensic_mos_correctness.py`.
- [x] 10. Run Python tests and frontend build; record final runtime evidence in `docs/QPORT_FORENSIC_MOS_CORRECTNESS_AUDIT.md`.

---

## ## Related Notes

- [docs/tasks/TASK-20260911-136-munger-financial-analysis-engine.md](file:///c:/workspace/shannon_allocation/docs/tasks/TASK-20260911-136-munger-financial-analysis-engine.md)
- [docs/tasks/TASK-20260911-137-munger-business-valuation-integration.md](file:///c:/workspace/shannon_allocation/docs/tasks/TASK-20260911-137-munger-business-valuation-integration.md)
- [docs/tasks/TASK-20260912-138-business-workspace-ai-export-button.md](file:///c:/workspace/shannon_allocation/docs/tasks/TASK-20260912-138-business-workspace-ai-export-button.md)

---

## ## Validation Evidence

- Created pre and post-implementation audit report in `docs/QPORT_FORENSIC_MOS_CORRECTNESS_AUDIT.md`.
- Ran `python/portfolio/tests/test_forensic_mos_correctness.py` (12/12 passed).
- Ran `test_munger_financial_analysis.py`, `test_munger_business_valuation_integration.py`, `test_runtime_valuation_propagation.py` (33/33 passed).
- Executed `npm run build` in `frontend/` (succeeded cleanly in 1.44s).

---

## ## Decisions

1. **Exact Normalized String Matching**: Preserved exact string alias mapping in `ssi_ingestion.py` without unsafe substring matching. Added missing exact aliases `"cac khoan phai thu"` and `"phai thu ngan han"` to map aggregate short-term receivables to `BS.ASSETS.RECEIVABLES`.
2. **Single Canonical MOS Authority**: Established `canonical_valuation.py` / `MarginOfSafetyEngine.calculate()` as the sole authority for required MOS. Downstream `munger_analyzer.py`, `context_builder.py`, API endpoints, and AI exports consume `val["required_mos_pct"]` directly.
3. **No Hardcoded Fallbacks**: Removed custom `base_req_mos + addons` overwrite inside `munger_analyzer.py` when canonical valuation payload is supplied. Missing MOS remains missing (`MOS_UNKNOWN`), preserving `NULL != DEFAULT`.

---

## ## Result

Task 139 successfully completed. DGC false-positive receivables warning repaired via accurate SSI canonical mapping (`BS.ASSETS.RECEIVABLES`), required Margin of Safety unified to 1 single authority across all runtime components, and full regression test suite verified.
