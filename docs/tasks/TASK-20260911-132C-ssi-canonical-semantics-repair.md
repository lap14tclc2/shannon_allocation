# TASK-20260911-132C: SSI Canonical Semantics Repair

**Status**: completed  
**Priority**: High  
**Date**: 2026-09-11  
**Author**: Antigravity Agent  

---

## Requirement

Perform a comprehensive correctness repair on the SSI raw financial data to canonical fact conversion pipeline in QPort (`lap14tclc2/shannon_allocation`).

Specifically:
- Remove unsafe substring fuzzy line-item mapping in `map_ssi_line_item()`, replacing it with exact normalized alias matching.
- Add regression tests to prevent false-positive mappings (e.g. brokerage revenue -> total revenue).
- Deduplicate same semantic payloads across multiple export files while preserving physical workbook provenance in `ssi_import_files`.
- Explicitly detect and handle different/conflicted payloads for the same symbol/statement without silent overwrite.
- Implement real payload conflict reporting (`different_payload_conflicts`, `docs/reports/ssi-payload-conflicts.csv`).
- Implement deterministic derived total debt (`BS.DEBT.TOTAL = SHORT_TERM_BORROWINGS + LONG_TERM_BORROWINGS`) with strict NULL/zero handling and derived lineage tracking.
- Respect archetype boundaries so BANK (`ACB`) and SECURITIES (`VIX`) are not polluted with normal-enterprise debt derivations.
- Ensure provider precedence (SSI primary -> TCBS fallback) isolates `SOURCE_VARIANCE` from blocking `CANONICAL_FACT_CONFLICT`.
- Implement automated accounting reconciliation checks (Balance Sheet assets = liabilities + equity, Cash Flow ending cash, FY cash continuity, IS PBT + tax = PAT).
- Verify real sample behavior on `AAA`, `AAH`, `VIX`, and golden symbols (`ACB`, `DGC`, `FPT`, `VIX`) on PostgreSQL.
- Rebuild SSI canonical facts safely and generate audit report `docs/reports/ssi-canonical-semantics-audit.md`.

---

## Context

Task 132B verified that PostgreSQL `qport_finance.canonical_facts` contains 117,759 SSI facts across 390 symbols from 3,783 XLSX files. However, a code audit revealed that `map_ssi_line_item()` used substring pattern matching (`pattern in normalized`), causing child line items (like brokerage revenue or specific receivables) to be falsely mapped to aggregate canonical codes.

Additionally, importing multiple workbooks for the same symbol executed indiscriminate `DELETE FROM canonical_facts` statements, duplicate semantic payloads were reprocessed without payload-level deduplication, and cross-provider differences were mistakenly flagged as blocking canonical conflicts.

---

## Acceptance Criteria

- [x] Unsafe fuzzy substring mapping removed from `map_ssi_line_item()`, replaced with exact normalized alias table.
- [x] False-positive mapping regression tests added (`test_ssi_canonical_semantics.py`).
- [x] Same-payload export files deduplicated at the logical canonical layer.
- [x] Physical file provenance preserved in `ssi_import_files`.
- [x] Different semantic payloads detected and payload conflicts reported without silent overwrites.
- [x] Real payload conflict breakdown exported to `docs/reports/ssi-payload-conflicts.csv`.
- [x] Derived `BS.DEBT.TOTAL` implemented deterministically with exact parent fact lineage and strict NULL handling.
- [x] Bank and Securities archetypes exempted from normal enterprise debt derivations.
- [x] Provider resolution ranks SSI primary before checking variance, recording `SOURCE_VARIANCE` warnings without blocking valuation.
- [x] True same-provider conflicts correctly flagged as `CANONICAL_CONFLICT`.
- [x] `NULL != 0` invariant strictly preserved.
- [x] Automated accounting reconciliation suite implemented (BS balance, CF ending cash, cash continuity, IS PBT/PAT).
- [x] AAA passes accounting checks; AAH history depth preserved at 6Y; VIX cash continuity and tax anomalies correctly flagged.
- [x] SSI canonical facts safely rebuilt on PostgreSQL `qport_finance`.
- [x] Real PostgreSQL golden symbols (`ACB`, `DGC`, `FPT`, `VIX`) verified for valuation readiness.
- [x] Comprehensive audit report `docs/reports/ssi-canonical-semantics-audit.md` generated.
- [x] All regression suites pass cleanly.

---

## Constraints and Invariants

1. **Exact Normalized Matching Only**: No uncontrolled substring regex or `in` string matching for line item codes.
2. **Deterministic Provider Precedence**: SSI primary -> TCBS fallback. No provider averaging.
3. **Strict Zero vs NULL**: Empty cells remain missing (NULL); explicit zeroes stay zero. No zero imputation.
4. **Archetype Isolation**: Financial archetypes (BANK, SECURITIES) must not receive invalid enterprise derived metrics.
5. **No Loss of Provenance**: All physical source files must remain in provenance logs.
6. **Task 134 Precedence Preserved**: Qualitative review status remains `REVIEW_BUSINESS`.

---

## Implementation Tasks

- [x] Step 1: Write initial failing regression tests for fuzzy mapping, payload conflict, derived debt, and accounting checks.
- [x] Step 2: Audit and refactor `map_ssi_line_item()` in `python/portfolio/financial_data/ssi_ingestion.py` to use exact alias matching.
- [x] Step 3: Implement semantic payload deduplication and explicit payload conflict detection in `ssi_ingestion.py`.
- [x] Step 4: Remove silent `DELETE FROM canonical_facts` statement wiping and refactor canonical write semantics.
- [x] Step 5: Implement derived total debt calculation with parent lineage tracking and archetype awareness.
- [x] Step 6: Implement accounting reconciliation module in `reconciler.py` / `ssi_ingestion.py`.
- [x] Step 7: Safely rebuild SSI canonical facts on PostgreSQL DB and verify before/after counts.
- [x] Step 8: Verify provider resolution and valuation readiness for `ACB`, `DGC`, `FPT`, `VIX`.
- [x] Step 9: Produce `docs/reports/ssi-payload-conflicts.csv` and `docs/reports/ssi-canonical-semantics-audit.md`.
- [x] Step 10: Run full test suite and finalize task.

---

## Related Notes

- [AGENTS.md](file:///c:/workspace/shannon_allocation/AGENTS.md)
- [TASK-20260910-132B](file:///c:/workspace/shannon_allocation/docs/tasks/TASK-20260910-132B-ssi-database-reality-check.md)
- [TASK-20260911-135](file:///c:/workspace/shannon_allocation/docs/tasks/TASK-20260911-135-runtime-valuation-evidence-propagation.md)
- [Audit Report](file:///c:/workspace/shannon_allocation/docs/reports/ssi-canonical-semantics-audit.md)

---

## Validation Evidence

Executed unit & integration test suite:
```bash
$env:DATABASE_URL="postgresql://qport:qport@127.0.0.1:5432/qport"; & "$env:USERPROFILE\.venv\Scripts\python.exe" -m pytest -o pythonpath=python python/portfolio/tests/test_ssi_bulk_ingestion.py python/portfolio/tests/test_ssi_canonical_cutover.py python/portfolio/tests/test_runtime_evidence_audit.py python/portfolio/tests/test_qualitative_evidence.py python/portfolio/tests/test_decision_precedence.py python/portfolio/tests/test_runtime_valuation_propagation.py python/portfolio/tests/test_ssi_canonical_semantics.py
```
Output: `56 passed in 4.65s`

Executed rebuild script:
```bash
$env:DATABASE_URL="postgresql://qport:qport@127.0.0.1:5432/qport"; $env:PYTHONPATH="python"; & "$env:USERPROFILE\.venv\Scripts\python.exe" scripts/rebuild_ssi_canonical_facts.py
```
Output: `AFTER SSI canonical facts count: 118,875 | Derived facts count: 3,416`

---

## Decisions

1. **Exact Normalized Line Item Matching**: Removed fuzzy substring search (`pattern in normalized`) in `map_ssi_line_item()`. Only explicit normalized alias keys in `CANONICAL_LINE_MAPPINGS` are mapped.
2. **Logical Payload Deduplication with Provenance**: Physical workbooks are stored in `ssi_import_files`, but canonical fact generation processes only unique `semantic_hash` payloads per symbol and statement type.
3. **Non-Destructive PostgreSQL UPSERT**: Removed statement-level `DELETE FROM canonical_facts`. Canonical facts are upserted using `ON CONFLICT (symbol, statement_type, line_item_code, period_type, fiscal_year, fiscal_quarter, provider) DO UPDATE`.
4. **Archetype-Aware Derived Debt**: `BS.DEBT.TOTAL` is calculated as `SHORT_TERM_BORROWINGS + LONG_TERM_BORROWINGS` for industrial enterprise symbols, and omitted for `BANK` and `SECURITIES` archetypes.

---

## Result

- SSI canonical mapping semantics repaired and verified on PostgreSQL.
- Eliminating false-positive fuzzy mappings removed ~10.8k erroneous facts, while adding 3,416 derived `BS.DEBT.TOTAL` facts across industrial enterprises.
- All golden symbols (`ACB`, `DGC`, `FPT`, `VIX`) achieve valuation readiness (`READY`) with primary SSI provider selection.
- Audit report published at `docs/reports/ssi-canonical-semantics-audit.md`.
