# Reconcile Munger Normalized PAT vs Valuation Normalized Owner Earnings (TASK-189)

`status: completed`
`created: 2026-09-17`

---

## Requirement
Reconcile the relationship and numerical differences between:
1. **Munger Normalized PAT** (in `munger_analyzer.py`): Accounting earning power calculated as the arithmetic average of historical annual net profit ($PAT$) over 5Y and 10Y fiscal windows.
2. **Valuation Normalized Owner Earnings** (in `owner_earnings.py` / `engine.py`): Cash earning power calculated as Buffett Owner Earnings ($CFO - \text{Maintenance CapEx}$), normalized over multi-year cycles via `MID_CYCLE_MEDIAN` ($\text{median}(\text{margin}) \times \text{median}(\text{Revenue})$).

Determine whether discrepancies observed across previous tasks (Tasks 185–188) are:
- Different economic representations (Accounting PAT vs Free Cash Flow Owner Earnings)
- Different fiscal year windows (FY2021–2025 vs FY2020–2024 / FY2019–2023)
- Different normalization algorithms (Arithmetic Mean vs Mid-Cycle Median)
- Or an architectural / pipeline defect.

---

## Context
Task 187 established canonical Munger normalization as the arithmetic average of the latest 5 and 10 available fiscal years. Task 188 audited valuation integrity but contained regression table numbers originating from earlier FY2024-ending snapshots while stating "Identical normalized PAT across Munger analyzer & Valuation". This task clarifies the exact mathematical provenance, data sources, and semantic labels of both pipelines.

---

## Acceptance Criteria
- [x] **AC1**: Exact reason for HAH discrepancy identified (FY2021–2025 with FY2025 1,206.5B = 701.9B vs FY2020–2024 = 441.7B; Owner Earnings distinguishes CapEx).
- [x] **AC2**: Exact reason for FPT discrepancy identified (FY2021–2025 with FY2025 9,376.1B = 6,669.1B vs older FY2020–2024 window = 5,310.8B; Owner Earnings includes data center/telecom CapEx).
- [x] **AC3**: Exact reason for DGC discrepancy identified (FY2021–2025 = 3,408.1B vs Mid-Cycle Owner Earnings median = 3,115.6B).
- [x] **AC4**: BFC confirmed as reference baseline case ($5\text{Y}_{norm} = 236.9\text{B}$).
- [x] **AC5**: Munger normalized PAT has exactly ONE canonical authority (`munger_analyzer.py` / `munger_forensics.py`).
- [x] **AC6**: Valuation normalized Owner Earnings has exactly ONE canonical authority (`OwnerEarningsCalculator.calculate_cycle_normalized`).
- [x] **AC7**: Relationship between normalized PAT and normalized Owner Earnings is explicit, mathematically documented, and cleanly labeled.
- [x] **AC8**: Fiscal-year windows are deterministic and auditable across both engines.
- [x] **AC9**: No hidden second normalization engines exist.
- [x] **AC10**: Missing data semantics remain intact (`UNKNOWN != PASS`, `MISSING != 0`, `PARTIAL != COMPLETE`).
- [x] **AC11**: Corporate action / share basis invariants remain intact.
- [x] **AC12**: MOS remains strictly based on canonical IV/share and current price.
- [x] **AC13**: Bank and securities archetypes remain isolated from industrial Owner Earnings / CFO.
- [x] **AC14**: Deterministic test suite `test_munger_valuation_normalization_reconciliation.py` (Scenarios A through T) 100% passing.
- [x] **AC15**: All existing Munger and valuation regression suites pass.
- [x] **AC16**: Frontend production build succeeds.
- [x] **AC17**: Audit report generated at `docs/reports/munger-valuation-normalization-reconciliation-audit.md`.

---

## Constraints and Invariants
1. `BUY_AND_HOLD_INFORMATION_SYSTEM`: Information system only.
2. SSI Annual BCTC is the primary canonical source.
3. No second valuation engine or competing decision pipelines.
4. No change to canonical decision thresholds, liquidity gates, or MOS formulas.

---

## Implementation Tasks
- [x] **Task 1: Code Trace & Provenance Audit of Munger vs Valuation Normalization**
- [x] **Task 2: Build Deterministic Test Suite (Scenarios A through T)**
- [x] **Task 3: Run Full Pytest Matrix Across Tasks 181–189**
- [x] **Task 4: Build Audit Report Document**
- [x] **Task 5: Frontend Build & Verification**
- [x] **Task 6: Update Task Status & Push**

---

## Validation Evidence

### 1. New Deterministic Test Suite (Scenarios A through T)
```powershell
.\.venv\Scripts\python.exe -m pytest python/portfolio/tests/test_munger_valuation_normalization_reconciliation.py -v
============================= 20 passed in 1.05s ==============================
```

### 2. Comprehensive Test Suites Run Across Tasks 181–189
```powershell
.\.venv\Scripts\python.exe -m pytest \
    python/portfolio/tests/test_munger_valuation_normalization_reconciliation.py \
    python/portfolio/tests/test_intrinsic_value_normalized_earning_power.py \
    python/portfolio/tests/test_normalized_earning_power_reconciliation.py \
    python/portfolio/tests/test_munger_cyclicality_volatility.py \
    python/portfolio/tests/test_munger_business_quality_earning_power.py \
    python/portfolio/tests/test_canonical_munger_decision_integrity.py \
    python/portfolio/tests/test_munger_liquidity_gate.py \
    python/portfolio/tests/test_canonical_share_basis_mos_integrity.py \
    python/portfolio/tests/test_corporate_action_normalization.py \
    python/portfolio/tests/test_value_engine.py \
    python/portfolio/tests/test_value_engine_audit_fixes.py -q
============================ 162 passed in 17.79s =============================
```

### 3. Frontend Production Build
```powershell
npm run build (in frontend/)
✓ 365 modules transformed.
✓ built in 5.31s
```

---

## Decisions
1. **Economic Representation Clarity:** Normalized PAT (accounting net income) is distinct from Normalized Owner Earnings (free cash flow). Both have separate, well-defined single authorities in the codebase.
2. **Deterministic Data Cutover:** Historical markdown table differences traced to pre-2025 snapshot windows; canonical 2021–2025 series is verified across all test fixtures.

---

## Result
Completed Task 189. All discrepancies fully reconciled and verified. Zero regressions across the entire test matrix. Audit report created at `docs/reports/munger-valuation-normalization-reconciliation-audit.md`.
