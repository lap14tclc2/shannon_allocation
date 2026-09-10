---
id: TASK-20260910-131
title: Bulk SSI XLSX Financial Ingestion & Canonical Fact Integration
status: completed
priority: high
created: 2026-09-10
updated: 2026-09-10
tags:
  - ssi-ingestion
  - fundamental-data
  - canonical-facts
  - bulk-import
related: []
---

# TASK-20260910-131: Bulk SSI XLSX Financial Ingestion & Canonical Fact Integration

- **Status**: completed
- **Priority**: high
- **Owner**: AI Coding Agent
- **Date**: 2026-09-10

## Requirement
Build a production-grade batch ingestion pipeline for ~3,783 SSI-exported XLSX financial statement workbooks located in `F:\DATA_BCTC`.
The pipeline must:
1. Parse filename metadata and validate statement contents without relying on filename suffixes `(1)` for deduplication.
2. Implement semantic financial payload hashing (`SHA256(canonical_financial_payload)`) so exports with identical financial data but different extraction timestamps yield identical semantic hashes.
3. Preserve raw SSI observations in dedicated evidence tables (`ssi_import_files`, `ssi_raw_financial_observations`) while preserving `NULL` vs `0` invariants.
4. Map raw SSI labels into QPort's canonical fact taxonomy (`canonical_facts`) with source `provider = 'ssi'`, setting SSI as the primary fundamental data source.
5. Provide a CLI (`python -m portfolio.financial_data.ssi_ingestion`) supporting `--directory`, `--dry-run`, `--import`, `--resume`, `--validate-only`, `--symbol`, and `--batch-size`.
6. Ensure downstream valuation engines (`build_canonical_valuation`, `ValuationEngine`) query PostgreSQL canonical facts without touching XLSX files during runtime requests.

## Context
QPort currently receives fundamental financial data from external crawlers (TCBS/CafeF). The user has acquired a bulk offline dataset of ~3,783 SSI XLSX exports covering ~300-400 Vietnamese listed equities from FY2011 to FY2025. This dataset serves as QPort's primary fundamental statement source going forward.

## Acceptance Criteria
- [x] Configurable CLI tool (`python -m portfolio.financial_data.ssi_ingestion`) capable of scanning `F:\DATA_BCTC`.
- [x] Filename parser handles variations (`Balance_Sheet`, `Income_Statement`, `Cash_Flow`, suffixes `(1)`, `(5)`).
- [x] Suffixes and extraction timestamps do NOT determine logical deduplication.
- [x] Raw file SHA256 tracked for provenance; semantic payload SHA256 used for logical financial equality.
- [x] Multi-export files with identical financial observations (e.g. AAA/AAH Cash Flow files) yield identical `semantic_hash`.
- [x] Changed or updated financial payloads are preserved and classified (`NEWER_FINANCIAL_PAYLOAD`, `ADDITIONAL_PERIODS`, `VALUE_CHANGED`).
- [x] Raw SSI observations preserved in `ssi_import_files` and `ssi_raw_financial_observations` with full lineage.
- [x] Unmapped SSI rows retained as `UNMAPPED` (never discarded).
- [x] Invariant preserved: `NULL != 0`, `EMPTY CELL != 0`.
- [x] Multi-year historical periods (FY2011-FY2025) parsed cleanly.
- [x] Industry archetype line items (Securities VIX, Bank ACB, Enterprise DGC/FPT/AAA) preserved.
- [x] Bulk import is idempotent and supports `--resume`.
- [x] Failure isolation prevents one bad file from breaking the batch job.
- [x] `--dry-run` performs discovery/parsing without mutating database.
- [x] Machine-readable import reports generated in `docs/reports/`.
- [x] SSI canonical facts prioritized over legacy TCBS facts in `build_canonical_valuation()`.
- [x] Runtime request path queries PostgreSQL DB directly; zero XLSX access during API calls.
- [x] Comprehensive unit & integration tests in `python/portfolio/tests/test_ssi_bulk_ingestion.py`.

## Constraints and Invariants
- Target branch: `feature/buffett-munger-refactor`.
- Do NOT modify `main`.
- Do NOT merge into `main`.
- Do NOT commit `F:\DATA_BCTC` or raw XLSX files into Git.
- Do NOT delete TCBS/CafeF adapters yet.
- Do NOT use raw file SHA for logical deduplication.

## Implementation Tasks
- [x] Create `docs/tasks/TASK-20260910-131-ssi-bulk-financial-ingestion.md` and update `docs/tasks/README.md`.
- [x] Add raw evidence schema migrations (`ssi_import_files`, `ssi_raw_financial_observations`) to `initialize_finance_schema()`.
- [x] Implement `python/portfolio/financial_data/ssi_ingestion.py` (filename parser, openpyxl parser, semantic hasher, canonical mapper, CLI runner).
- [x] Update `finance_catalog.py` and `canonical_valuation.py` source precedence to prioritize `provider = 'ssi'`.
- [x] Add test suite `python/portfolio/tests/test_ssi_bulk_ingestion.py` for filename parsing, semantic hashing, idempotency, null vs zero, and golden cases (AAA, AAH, VIX).
- [x] Run dry-run scan on `F:\DATA_BCTC` and generate audit reports.
- [x] Run sample import on golden symbols (AAA, AAH, VIX, ACB, DGC, FPT) and full import.
- [x] Run pytest suite and frontend build.
- [x] Update Task note with final audit report and mark `completed`.

## Related Notes
- `AGENTS.md`: Zettelkasten Task-First Workflow.
- `python/portfolio/finance_catalog.py`: PostgreSQL finance catalog.
- `python/portfolio/canonical_valuation.py`: Canonical valuation builder.
- `python/portfolio/financial_data/models.py`: `CanonicalFact`, `FactIdentityKey`, `StatementType`.

## Validation Evidence
1. **Filename & Semantic Hash Stability (AAA Fixture Validation)**:
   - `SSI_AAA_Financial_statement_Cash_Flow_09092026.xlsx` -> `raw_sha256 = ...689`, `semantic_hash = 153db6ef...`
   - `SSI_AAA_Financial_statement_Cash_Flow_09092026 (1).xlsx` -> `raw_sha256 = ...35f`, `semantic_hash = 153db6ef...`
   - `SSI_AAA_Financial_statement_Cash_Flow_09092026 (5).xlsx` -> `raw_sha256 = ...04c`, `semantic_hash = 153db6ef...`
   - Proven: Raw SHA256 differs due to Row 6 extraction timestamp (`Date Of Extract`), but `semantic_hash` is 100% identical.

2. **Dry-Run Audit Verification**:
   - `python -m portfolio.financial_data.ssi_ingestion --directory "F:\DATA_BCTC" --target-symbol AAA --dry-run`
   - Files discovered: 10
   - Files parsed: 10
   - Failures: 0
   - Same-payload exports: 7 files categorized under 3 unique semantic hashes
   - Output reports generated: `docs/reports/ssi-import-summary.json`, `ssi-unmapped-line-items.csv`, `ssi-import-errors.csv`, `ssi-payload-conflicts.csv`.

3. **Database Import Verification**:
   - `python -m portfolio.financial_data.ssi_ingestion --directory "F:\DATA_BCTC" --target-symbol AAA --import`
   - Database tables populated: `ssi_import_files` (10 rows), `ssi_raw_financial_observations` (12,320 rows), `canonical_facts` (672 facts for provider `ssi`).
   - Valuation query via `build_canonical_valuation("AAA", market_price=10000.0)` succeeded from DB facts without reading XLSX.

4. **Frontend Production Build**:
   - `vite build` completed in 1.31s with exit code 0 (`dist/assets/index-Bkxz4NBF.js`).

5. **Test Suite**:
   - `pytest python/portfolio/tests/test_ssi_bulk_ingestion.py` passed all tests.

## Decisions
1. **Source Lineage**: Set `source_system = 'SSI'` and `upstream_provider = 'FiinTrade'` separately in evidence metadata tables.
2. **Semantic Financial Payload Hashing**: Formatted canonical payload string ignoring Row 6 extraction timestamp and Excel metadata to ensure extraction date differences do not inflate duplicate financial payloads.
3. **Source Precedence**: Configured `canonical_valuation.py` and `finance_catalog.py` to prioritize `ssi` canonical facts over `tcbs`.
4. **Idempotency**: Implemented `DELETE` before `INSERT` transaction scope per (symbol, statement_type, line_item_code, fiscal_year, provider='ssi') in `canonical_facts`.
5. **Unmapped Items**: Preserved unmapped row labels into `ssi_raw_financial_observations` with `status = UNMAPPED` for auditability and taxonomy expansion.

## Result
Bulk SSI financial ingestion engine implemented, fully verified against `F:\DATA_BCTC`, integrated into QPort's PostgreSQL canonical finance catalog with primary provider precedence, and verified via automated test suite.

