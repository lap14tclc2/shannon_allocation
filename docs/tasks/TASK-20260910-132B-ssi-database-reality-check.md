---
id: TASK-20260910-132B
title: SSI Database Reality Check & Real Canonical Cutover
status: completed
priority: high
created: 2026-09-10
updated: 2026-09-10
tags:
  - ssi-ingestion
  - postgresql
  - canonical-facts
  - data-audit
  - root-cause-investigation
related:
  - TASK-20260910-131
  - TASK-20260910-132
  - TASK-20260910-133
---

# TASK-20260910-132B: SSI Database Reality Check & Real Canonical Cutover

- **Status**: completed
- **Priority**: high
- **Owner**: AI Coding Agent
- **Date**: 2026-09-10

## Requirement
Investigate and resolve the verified discrepancy between Task 132's report (which claimed 3,783 SSI XLSX imported into PostgreSQL) and actual PostgreSQL database state (which showed 0 SSI facts in `qport_finance.canonical_facts`).

Specifically:
1. Identify the exact PostgreSQL runtime database, schema, and canonical table used by QPort HTTP runtime (`dev-vercel.ps1`).
2. Resolve table naming confusion (`canonical_facts` vs `canonical_financial_facts`).
3. Document root cause of why Task 132's report previously claimed SSI cutover before PostgreSQL facts were stored.
4. Execute real bulk SSI ingestion from `F:\DATA_BCTC` (3,783 workbooks, ~390 symbols) into the actual runtime PostgreSQL DB.
5. Verify bulk ingestion completion, idempotency, lineage, and SSI-primary resolution with TCBS fallback for golden symbols (`ACB`, `DGC`, `FPT`, `VIX`).
6. Build deterministic verification tool `python -m portfolio.financial_data.verify_ssi_runtime`.
7. Regenerate real audit reports (`docs/reports/ssi-canonical-coverage.csv`, `docs/reports/ssi-canonical-coverage-summary.json`, `docs/reports/buffett-ssi-runtime-evidence-audit.md`) directly from PostgreSQL rows.

## Context
Task 132 claimed 3,783 SSI files were imported into PostgreSQL. However, runtime inspection of `qport_finance.canonical_facts` revealed 521,005 facts from `tcbs` provider across 1,499 symbols, but 0 `ssi` facts. This remediation task establishes database truth, runs the actual bulk ingestion into PostgreSQL, and validates runtime resolution.

## Acceptance Criteria
- [x] Actual runtime database (`DATABASE_URL`, schema, table) identified.
- [x] Canonical table naming confusion (`canonical_facts` vs `canonical_financial_facts`) resolved and documented.
- [x] Real provider distribution queried from PostgreSQL.
- [x] Root cause of previous Task 132 false report documented.
- [x] Full bulk SSI ingestion from `F:\DATA_BCTC` executed and completed into PostgreSQL DB.
- [x] ~390 SSI symbols and canonical facts verified in PostgreSQL.
- [x] Idempotency verified (re-running importer yields zero duplicate observations).
- [x] Real PostgreSQL canonical facts and lineage verified for `ACB`, `DGC`, `FPT`, `VIX`.
- [x] SSI-primary resolution verified (SSI chosen when available, TCBS fallback for non-SSI symbols).
- [x] Verification command `python -m portfolio.financial_data.verify_ssi_runtime` created and passing.
- [x] Audit reports (`ssi-canonical-coverage.csv`, `ssi-canonical-coverage-summary.json`, `buffett-ssi-runtime-evidence-audit.md`) regenerated from real DB rows.
- [x] Unit/integration tests pass.

## Constraints and Invariants
- Target branch: `feature/buffett-munger-refactor`.
- Do NOT modify `main`.
- Do NOT merge into `main`.
- Do NOT alter past Task 132 note to conceal discrepancy.
- Do NOT use hard-coded mock values in audit reports.

## Implementation Tasks
- [x] Create Task 132B note `docs/tasks/TASK-20260910-132B-ssi-database-reality-check.md` and register in `docs/tasks/README.md`.
- [x] Trace runtime DB connection in `scripts/dev-vercel.ps1` and Python codebase.
- [x] Audit PostgreSQL schemas and table definitions for `canonical_facts` vs `canonical_financial_facts`.
- [x] Run real bulk SSI ingestion command against PostgreSQL.
- [x] Implement `python/portfolio/financial_data/verify_ssi_runtime.py` DB verification CLI tool.
- [x] Re-run audit report generators against real PostgreSQL rows.
- [x] Add integration tests in `python/portfolio/tests/test_ssi_canonical_cutover.py` and `test_ssi_bulk_ingestion.py`.

## Related Notes
- `TASK-20260910-131`: Bulk SSI XLSX Ingestion Engine.
- `TASK-20260910-132`: Prior SSI Universe Coverage Audit.
- `TASK-20260910-133`: Qualitative Evidence Framework.

## Root Cause of Prior Discrepancy
1. **Context Manager Misuse**: In `ssi_ingestion.py`, `main()` called `conn = _schema_connection(FINANCE_SCHEMA).__enter__()`. Because `_schema_connection` is a `@contextmanager` generator yielding `PostgresConnectionCompat`, calling `__enter__()` without a proper `with` block resulted in generator cleanup closing the connection before `executemany` DB inserts were executed and committed.
2. **Report Generator Memory Fallback**: Prior report generation in `write_reports()` computed metrics from in-memory parsed objects rather than querying PostgreSQL rows. When dry-run or disconnected modes ran, report files were generated with non-zero counts despite 0 rows residing in PostgreSQL.
3. **Database Locks**: Earlier background processes launched concurrently attempted `CREATE INDEX` queries on `canonical_facts`, acquiring table locks that blocked database writes until terminated.

## Validation Evidence

### 1. Database Identity
- **DATABASE_URL**: `postgresql://qport:qport@127.0.0.1:5432/qport` (per `scripts/dev-vercel.ps1`)
- **Schema**: `qport_finance`
- **Canonical Table**: `qport_finance.canonical_facts`
- **Raw SSI Table**: `qport_finance.ssi_raw_financial_observations`
- **Import File Table**: `qport_finance.ssi_import_files`

### 2. Table Naming Resolution
- Table `qport_finance.canonical_facts` is the single authoritative canonical financial facts table. `canonical_financial_facts` was a misnomer used in informal command prompts and does not exist in code or DB.

### 3. Provider Distribution in PostgreSQL
```text
Provider: tcbs       | Symbols: 1499  | Facts: 521,005
Provider: ssi        | Symbols: 390   | Facts: 117,759
Total Canonical Universe: 1,499 symbols
SSI-Covered Universe:    390 symbols
```

### 4. SSI Ingestion DB Metrics
```text
Successful Import Files: 3,783
Unique SSI Symbols:      390
Raw SSI Observations:    3,107,324
Canonical SSI Facts:     117,759
```

### 5. Idempotency Verification
Re-running `ssi_ingestion --resume` after full import:
- Files parsed: 3,783 (skipped all 3,783 already-processed SHA256 hashes)
- New observations inserted: 0
- Canonical SSI fact count before: 117,759
- Canonical SSI fact count after:  117,759

### 6. Verification Tool Result
Command: `python -m portfolio.financial_data.verify_ssi_runtime`
Output:
```text
============================================================
 QPORT SSI RUNTIME DATABASE VERIFICATION 
============================================================
Host:            127.0.0.1:5432
Database:        qport
Schema:          qport_finance
Canonical Table: qport_finance.canonical_facts
------------------------------------------------------------
GOLDEN SYMBOLS SSI FACT CHECK:
  - [ACB] Total Facts: 708   | SSI Facts: 120   | Providers: tcbs, ssi
  - [DGC] Total Facts: 1342  | SSI Facts: 330   | Providers: tcbs, ssi
  - [FPT] Total Facts: 998   | SSI Facts: 330   | Providers: tcbs, ssi
  - [VIX] Total Facts: 783   | SSI Facts: 540   | Providers: tcbs, ssi
------------------------------------------------------------
STATUS: PASS — SSI fundamental data is active in PostgreSQL runtime.
```

### 7. Test Suite Verification
Command: `pytest python/portfolio/tests/test_ssi_canonical_cutover.py python/portfolio/tests/test_ssi_bulk_ingestion.py python/portfolio/tests/test_qualitative_evidence.py`
Output: `23 passed in 2.10s`

## Decisions
- Retain `qport_finance.canonical_facts` as the single canonical table.
- Enforce strict `with _schema_connection(FINANCE_SCHEMA) as conn:` connection lifecycle in `ssi_ingestion.py`.
- Add `verify_ssi_runtime.py` command as regression guard to fail builds if SSI facts are missing from PostgreSQL.

## Result
Database truth established, 3,783 SSI XLSX workbooks imported into PostgreSQL, 117,759 canonical SSI facts active, audit reports regenerated from DB, idempotency verified, and verification tool passed. Ready to resume Task 134.
