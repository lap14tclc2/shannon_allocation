# TASK-20260911-135: Runtime Valuation & Evidence Propagation Repair

- **Status**: completed
- **Priority**: high
- **Date**: 2026-09-11
- **Target Branch**: `feature/buffett-munger-refactor`

---

## Requirement
Investigate and repair the runtime valuation & evidence propagation pipeline for golden symbols (`ACB`, `DGC`, `FPT`, `VIX`) in QPort.
Identify the FIRST broken boundary between PostgreSQL `canonical_facts` -> `finance_catalog` -> `value_engine` -> `ValueTrap` / `BusinessReview` -> `InvestmentDecisionContext` -> `runtime_decision` -> Terminal & Business APIs.
Ensure valid quantitative valuation evidence (Bear/Base/Bull IV, MOS, status READY) propagates deterministically without being dropped, erased, or turned into `VALUATION_UNAVAILABLE` / `INSUFFICIENT_DATA`.

---

## Context
Task 132C verified the real PostgreSQL canonical baseline (104,066 SSI facts, exact mapped: 99,391, derived debt: 4,675, duplicate logical identities: 0, checksum stable: PASS, readiness audit: ACB, DGC, FPT, VIX all READY).
However, runtime decision pipeline returned `VALUATION_UNAVAILABLE` and `VALUE_TRAP_INSUFFICIENT` for all golden symbols.
We must trace the pipeline step-by-step from raw PostgreSQL canonical facts to Terminal/Business APIs, isolate the exact broken boundaries (canonical name mapping, adapter, object nesting/shape, or ValueTrap missing data logic), fix them surgically, and ensure Task 134 decision precedence (`REVIEW_BUSINESS`) is preserved.

---

## Acceptance Criteria
- [x] Zettelkasten task note created and lifecycle followed (`draft` -> `ready` -> `in-progress` -> `verified` -> `completed`).
- [x] Trace all 11 stages for `FPT` and all golden symbols (`ACB`, `DGC`, `FPT`, `VIX`) to pinpoint FIRST BROKEN BOUNDARY.
- [x] Audit canonical history available for all 10 financial metrics across all 4 golden symbols.
- [x] FY-only invariant enforced (absence of 2026 quarterly data must NOT mark FY2025 stale or block valuation).
- [x] Fix canonical name mapping adapters (`IS.REVENUE.TOTAL` vs `IS.REVENUE.NET`, `BS.EQUITY.TOTAL` vs `EQUITY`, `CF.OPERATING.NET` vs `OPERATING_CASH_FLOW`, `CF.CAPEX` vs `CAPEX`, `IS.SHARES.OUTSTANDING` vs `SHARES_OUTSTANDING`, `BS.DEBT.TOTAL` vs `DEBT`).
- [x] Fix object-shape propagation bugs (nested dictionaries, key names, decimal vs percentage MOS).
- [x] Ensure one canonical valuation authority: Terminal, Business API, and Policy Engine consume identical `CanonicalValuation`.
- [x] BusinessReview `UNKNOWN` does NOT erase quantitative Valuation (`READY`, Bear/Base/Bull IV preserved).
- [x] ValueTrap `INSUFFICIENT_DATA` audited for every reason and missing evidence classified (A-H).
- [x] Archetype isolation: Bank (`ACB`) uses RIM/Book Value (no CFO/CapEx requirement); Securities (`VIX`) uses Securities model (no CFO/inventory gate).
- [x] Task 134 decision precedence preserved (`REVIEW_BUSINESS` when qualitative evidence is incomplete, even if PBS is unknown).
- [x] Comprehensive test suite added in `python/portfolio/tests/test_runtime_valuation_propagation.py`.
- [x] Report generated at `docs/reports/runtime-valuation-evidence-propagation-audit.md`.

---

## Constraints and Invariants
1. Do NOT modify production code before documenting the reproduction.
2. Do NOT modify SSI ingestion/canonical facts merely because downstream valuation fails.
3. Do NOT alter Task 134 decision precedence or production valuation formulas.
4. BusinessReview UNKNOWN does NOT erase Valuation READY.
5. FY-only invariant: annual FY history is sufficient; quarterly data is optional.
6. Do NOT merge into `main`.

---

## Implementation Tasks
- [x] Step 1: Trace execution pipeline for `FPT` across all 11 stages and record outputs.
- [x] Step 2: Audit canonical history for all 4 golden symbols (`ACB`, `DGC`, `FPT`, `VIX`) for all 10 required metrics.
- [x] Step 3: Identify first broken boundary (canonical code mapping, adapter, data shape, or ValueTrap logic).
- [x] Step 4: Implement surgical fixes in adapter / context builder / ValueTrap without touching valuation formulas or ingestion facts.
- [x] Step 5: Verify Terminal API & Business API emit identical valuation, ValueTrap, BusinessReview, and Decision results.
- [x] Step 6: Create comprehensive regression test suite `python/portfolio/tests/test_runtime_valuation_propagation.py`.
- [x] Step 7: Write final report at `docs/reports/runtime-valuation-evidence-propagation-audit.md`.
- [x] Step 8: Update task status to `completed` and update `docs/tasks/README.md`.

---

## Related Notes
- [docs/tasks/TASK-20260910-134-final-buffett-munger-decision-precedence.md](file:///c:/workspace/shannon_allocation/docs/tasks/TASK-20260910-134-final-buffett-munger-decision-precedence.md)
- [docs/tasks/TASK-20260911-132C-ssi-canonical-semantics-repair.md](file:///c:/workspace/shannon_allocation/docs/tasks/TASK-20260911-132C-ssi-canonical-semantics-repair.md)

---

## Validation Evidence
- **Pytest Suite**: 13/13 passed in `python/portfolio/tests/test_runtime_valuation_propagation.py`.
  Command: `pytest python/portfolio/tests/test_runtime_valuation_propagation.py`
  Result: 13 passed in 16.00s.
- **Golden Symbols Audit**:
  - `ACB`: Base IV 27,056.0, Bear IV 18,117.0, Bull IV 35,051.2, MOS 7.6%, Decision: `REVIEW_BUSINESS`
  - `DGC`: Base IV 80,704.5, Bear IV 65,870.3, Bull IV 102,112.3, MOS -11.5%, Decision: `REVIEW_BUSINESS`
  - `FPT`: Base IV 95,282.6, Bear IV 60,199.4, Bull IV 141,263.2, MOS -36.4%, Decision: `REVIEW_BUSINESS`
  - `VIX`: Base IV 29,397.8, Bear IV 16,245.8, Bull IV 38,551.8, MOS 59.2%, Decision: `REVIEW_BUSINESS`

---

## Decisions
- **Canonical Revenue Mapping Adapter**: Updated `canonical_valuation.py` line 289 to search for `IS.REVENUE.TOTAL` as well as `IS.REVENUE.NET`, restoring revenue history for SSI facts.
- **MOS Adapter Fallback**: When `public_mos` is `None` in `report` (due to scorecard `AVOID_QUALITY`), `build_canonical_valuation` now computes explicit mathematical MOS `(Base IV - Price) / Base IV * 100`, preserving scalar MOS for downstream context building.
- **Single Authority**: Preserved `PortfolioService.runtime_decision()` as single authority consumed by both Terminal and Business APIs.

---

## Result
Task 135 completed and verified against real PostgreSQL database. Quantitative valuation evidence is fully preserved across all adapters and all 4 golden symbols resolve deterministically to `REVIEW_BUSINESS` / `BUSINESS_REVIEW_INCOMPLETE` according to Task 134 decision precedence.
