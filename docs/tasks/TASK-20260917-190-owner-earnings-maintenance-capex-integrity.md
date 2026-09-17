# Owner Earnings & Maintenance CapEx Integrity Audit (TASK-190)

`status: completed`
`created: 2026-09-17`

---

## Requirement
Perform an architectural, economic, and mathematical audit of the entire QPort Owner Earnings and Maintenance CapEx calculation pipeline:
$$\text{BCTC Facts} \to \text{CFO / PAT / D\&A / CapEx / Working Capital} \to \text{Owner Earnings} \to \text{Normalized Owner Earnings} \to \text{DCF / EPV / RIM Valuation} \to \text{MOS}$$

Key verification areas:
1. **Mathematical Integrity of Owner Earnings**: Verify exact formulas in `OwnerEarningsCalculator.calculate()` and `OwnerEarningsCalculator.calculate_cycle_normalized()`.
2. **CapEx Classification**: Verify whether CapEx is Total CapEx, Maintenance CapEx, or a bounded proxy ($\min(\text{CapEx}, |\text{D\&A}|)$), and verify confidence labeling (`LOW` vs `MEDIUM`).
3. **D&A & Working Capital Double-Count Check**: Prove mathematically and via tests that D&A and Working Capital changes are not double-counted ($OE = CFO - \text{MaintCapEx}$).
4. **Normalization Window & Methodology**: Document `MID_CYCLE_MEDIAN` ($\text{median}(\text{margin}) \times \text{median}(\text{Revenue})$) for cyclicals vs `LATEST_FY` for non-cyclicals.
5. **Archetype Isolation**: Ensure Banks and Securities remain strictly isolated from industrial Owner Earnings/CFO and continue using the Residual Income Model (RIM).
6. **Real Database Regression**: Run regression against PostgreSQL (`qport_finance.canonical_facts`) for BFC, HAH, FPT, DGC, TLG, ACB, TCB, TPB.
7. **Task 189 Fixture Value Reconciliation**: Explicitly differentiate synthetic test fixture outputs from real PostgreSQL calculated numbers.

---

## Context
Following Tasks 181–189 which audited share basis, Munger decision integrity, liquidity gates, business quality, and normalized earning power reconciliation, this task focuses on cash-flow economics: ensuring that free cash flow to owners is calculated conservatively, without false precision for unobservable maintenance CapEx, and without double-counting accounting line items.

---

## Acceptance Criteria
- [x] **AC1**: Actual Owner Earnings formula documented directly from source code.
- [x] **AC2**: Canonical CapEx source (`CF.CAPEX`) identified and validated.
- [x] **AC3**: Maintenance CapEx vs Total CapEx vs Proxy explicitly distinguished and documented.
- [x] **AC4**: No D&A double counting verified.
- [x] **AC5**: No working-capital double counting verified.
- [x] **AC6**: Bank and securities archetypes remain isolated from industrial Owner Earnings/CFO.
- [x] **AC7**: Missing data semantics strictly preserved (`UNKNOWN != PASS`, `MISSING != 0`, `PARTIAL != COMPLETE`).
- [x] **AC8**: Normalization methods (`MID_CYCLE_MEDIAN` vs `LATEST_FY`) explicitly documented.
- [x] **AC9**: Fiscal-year windows are deterministic and auditable.
- [x] **AC10**: Peak earnings cannot silently become sustainable Owner Earnings.
- [x] **AC11**: One-year CapEx spike does not corrupt multi-year normalized OE.
- [x] **AC12**: Permanent CapEx economics are preserved and not erroneously discarded as outliers.
- [x] **AC13**: Real PostgreSQL database regression executed and documented for all 8 canonical symbols.
- [x] **AC14**: Synthetic test fixture values are cleanly separated from real PostgreSQL calculated facts.
- [x] **AC15**: Task 189 HAH/FPT OE values independently reconciled and classified.
- [x] **AC16**: No false precision for maintenance CapEx (properly labeled as proxy with confidence level).
- [x] **AC17**: Single canonical valuation authority preserved.
- [x] **AC18**: Munger Normalized PAT and Valuation Normalized OE remain semantically distinct.
- [x] **AC19**: Existing canonical MOS and share-basis invariants remain intact.
- [x] **AC20**: Existing liquidity and decision gates remain unchanged.
- [x] **AC21**: All relevant tests pass (Scenarios A through W).
- [x] **AC22**: Frontend production build succeeds.
- [x] **AC23**: Zero investor-facing leakage (`null`, `NaN`, `undefined`).

---

## Constraints and Invariants
1. `BUY_AND_HOLD_INFORMATION_SYSTEM`: Information system only.
2. PostgreSQL SSI Annual BCTC is the primary canonical source.
3. No qualitative assumptions or analyst estimates used to manufacture maintenance CapEx.
4. No changes to canonical decision thresholds, liquidity gates, or MOS formulas.

---

## Implementation Tasks
- [x] **Task 1: Source Code Inspection & Mathematical Trace**
- [x] **Task 2: Build Deterministic Test Suite (Scenarios A through W)**
- [x] **Task 3: Execute Real PostgreSQL Database Regression**
- [x] **Task 4: Build Audit Report Document**
- [x] **Task 5: Frontend Build & Verification**
- [x] **Task 6: Update Task Status & Push**

---

## Validation Evidence

### 1. Deterministic Golden Test Suite (Scenarios A through W)
```powershell
.\.venv\Scripts\python.exe -m pytest python/portfolio/tests/test_owner_earnings_maintenance_capex_integrity.py -v
============================= 23 passed in 0.83s ==============================
```

### 2. Full Regression Test Matrix Across All 12 Test Suites (Tasks 181–190)
```powershell
.\.venv\Scripts\python.exe -m pytest \
    python/portfolio/tests/test_owner_earnings_maintenance_capex_integrity.py \
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
============================ 185 passed in 17.76s =============================
```

### 3. Frontend Production Build
```powershell
npm run build (in frontend/)
✓ 365 modules transformed.
✓ built in 4.98s
```

---

## Decisions
1. **Mathematical Validation:** Proved algebraically that `OwnerEarningsCalculator.calculate` reduces to $CFO - \min(\text{CapEx}, |\text{D\&A}|)$ without any D&A or working capital double counting.
2. **Honest Proxy Disclosure:** Maintenance CapEx is explicitly marked as `MIN_DEPRECIATION_CAPEX_PROXY` with confidence `LOW`.
3. **Synthetic vs DB Provenance:** Documented that Task 189 comparison values (FPT 4,000B, HAH 520B) were test fixture mock outputs, whereas real PostgreSQL values calculate FPT OE = 7,221.8B and HAH OE = 1,017.0B.

---

## Result
Completed Task 190. Owner Earnings and Maintenance CapEx integrity verified across all dimensions. Audit report published at `docs/reports/owner-earnings-maintenance-capex-integrity-audit.md`.
