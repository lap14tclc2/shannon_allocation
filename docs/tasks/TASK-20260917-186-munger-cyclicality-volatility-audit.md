# Munger Cyclicality & Earnings Volatility Integrity Audit (TASK-186)

`status: completed`
`created: 2026-09-17`

---

## Requirement
Audit whether QPort correctly distinguishes:
1. **Durable compounder** (`COMPOUNDER`)
2. **High-quality cyclical business** (`CYCLICAL_QUALITY`)
3. **Structurally deteriorating business** (`DETERIORATING_BUSINESS` / `WEAK_BUSINESS`)

Triggered by Task 185 regression observations:
- HAH: CV 105.4%, Peak earnings = YES, Quality PASS, CYCLICAL_QUALITY, BUY
- DGC: CV 115.2%, 5Y norm PAT 3,408B, 10Y norm PAT 1,975B, Quality PASS, CYCLICAL_QUALITY, BUY
- FPT: CV 64.1%, Forensic WATCH, Value Trap WATCH, Quality PASS, CYCLICAL_QUALITY, CONDITIONAL_BUY
- ACB: CV 88.2%, BANK, Quality PASS, CYCLICAL_QUALITY
- TCB: CV 83.2%, BANK, Quality PASS, CYCLICAL_QUALITY
- TPB: CV 99.2%, BANK, Quality PASS, CYCLICAL_QUALITY

Core Audit Objectives:
- Prove whether `QUALITY_PASS` is intentionally and economically compatible with `CYCLICAL_QUALITY` & high earnings volatility ($CV \ge 0.35$).
- Verify that `COMPOUNDER` is strictly gated by $CV < 0.35$, $\ge 5\text{Y}$ history, no loss years, solid growth, healthy cash conversion, and fortress capital.
- Verify that peak earnings is treated as a monitoring / required MOS markup signal, not an automatic business quality hard failure.
- Verify 5Y vs 10Y normalized earnings divergence traceability.
- Verify BANK and SECURITIES archetype isolation for volatility vs industrial rules.
- Verify Required MOS policy for `COMPOUNDER` vs `CYCLICAL_QUALITY` vs `AVERAGE_BUSINESS` vs `WEAK_BUSINESS`.
- Construct 10-point Deterministic Golden Matrix and run 8-symbol database regression (BFC, HAH, FPT, ACB, DGC, TCB, TPB, TLG).

---

## Context
In investment theory (Buffett/Munger), a good business is not always a steady, low-volatility compounder. Cyclical businesses with high returns on capital at mid-cycle (e.g. shipping liners like HAH, phosphorus chemicals like DGC, fertilizer like BFC) can possess strong moats and high quality, but their earnings fluctuate with macroeconomic/commodity cycles.
QPort architecture separates:
1. **Business Quality Gate**: Evaluates economic soundness, moat, balance sheet strength, and absence of structural deterioration or fraud.
2. **Compounder Classification**: Distinguishes steady secular compounders (`COMPOUNDER`) from cyclical compounders (`CYCLICAL_QUALITY`).
3. **Valuation & MOS Gate**: Quantifies cyclical risk by adding required MOS addons, demanding a much deeper margin of safety before recommending a purchase.

---

## Acceptance Criteria
- [x] **AC1**: Compounder Invariant Gating: $CV \ge 0.35$ or peak earnings or cyclical rebound strictly prevents `COMPOUNDER` classification.
- [x] **AC2**: Cyclical Quality Compatibility: `CYCLICAL_QUALITY` is economically sound and permitted to achieve `quality_gate == "PASS"` when balance sheet, normalized profitability, and forensics are healthy.
- [x] **AC3**: Peak Earnings Semantics: `is_peak_earnings` acts as a monitoring signal and required MOS addon trigger, not an automatic structural quality failure.
- [x] **AC4**: Normalized Earning Power Divergence Traceability: 5Y and 10Y normalized PAT correctly capture mid-cycle baseline vs long-term cycle without silent assumptions.
- [x] **AC5**: Archetype Isolation: Bank earnings volatility is evaluated in banking context; does not apply industrial CFO/working-capital rules.
- [x] **AC6**: Required MOS Markup: Cyclical businesses and earnings volatility trigger appropriate required MOS markups.
- [x] **AC7**: Investor-Facing Semantics: High volatility cyclical stocks are clearly labeled as `CYCLICAL_QUALITY` / "Doanh nghiệp có chất lượng tốt nhưng lợi nhuận mang tính chu kỳ", never mislabeled as steady compounders.
- [x] **AC8**: 10-point Deterministic Golden Matrix verified by automated tests.
- [x] **AC9**: Real Symbol DB Regression: 8 symbols verified against PostgreSQL data with explicit rationale.
- [x] **AC10**: Zero P0/P1 Integrity Defects; all test suites pass with 0 errors; frontend build succeeds.

---

## Constraints and Invariants
1. `BUY_AND_HOLD_INFORMATION_SYSTEM`: Information system only.
2. No new investment features, no redesign of valuation models, no arbitrary threshold invention.
3. Surgical edits only if a real defect is discovered.

---

## Implementation Tasks
- [x] **Task 1: Deep Code Inspection of Cyclicality, Volatility & Compounder Gating**
- [x] **Task 2: Archetype Volatility & Required MOS Verification**
- [x] **Task 3: Deterministic Golden Matrix Test Suite (10 Scenarios A-J)**
- [x] **Task 4: Real Symbol Database Regression & Classification Rationales**
- [x] **Task 5: Test Verification & Frontend Build**
- [x] **Task 6: Complete Task Note & Push**

---

## Related Notes
- [TASK-20260917-184-canonical-munger-end-to-end-audit.md](file:///c:/workspace/shannon_allocation/docs/tasks/TASK-20260917-184-canonical-munger-end-to-end-audit.md)
- [TASK-20260917-185-munger-business-quality-earning-power-audit.md](file:///c:/workspace/shannon_allocation/docs/tasks/TASK-20260917-185-munger-business-quality-earning-power-audit.md)

---

## Validation Evidence

### 1. Deterministic Golden Matrix Test Results
`python/portfolio/tests/test_munger_cyclicality_volatility.py`:
- **Scenario A**: Low Volatility Compounder Eligible ($CV < 35\%$, no losses, $CFO/PAT \ge 0.70$, 5Y) $\to$ `is_compounder=True`, `classification="COMPOUNDER"`, `quality_gate="PASS"`, `required_mos=0.20`. **PASSED**
- **Scenario B**: High Volatility Prevents Compounder ($CV = 45\%$) $\to$ `is_compounder=False`, `classification="CYCLICAL_QUALITY"`, `quality_gate="PASS"`. **PASSED**
- **Scenario C**: Cyclical Quality Remains Quality Pass (sound balance sheet, normalized ROE 22%) $\to$ `quality_gate="PASS"`, `is_compounder=False`, `classification="CYCLICAL_QUALITY"`. **PASSED**
- **Scenario D**: Peak Earnings is Monitoring Signal ($PAT_{latest} \ge 1.5\times 5\text{Y}_{norm}$) $\to$ `is_peak_earnings=True`, `quality_gate="PASS"`, monitoring reason logged, required MOS markup $+10\%$. **PASSED**
- **Scenario E**: Peak Earnings with Weak Normalized Earnings $\to$ `is_peak_earnings=True`, requires deeper MOS (0.50), avoids ungrounded buy. **PASSED**
- **Scenario F**: High Volatility + Structural Deterioration ($ROE_{norm} = 4\%$, high debt) $\to$ `quality_gate="FAIL"`, `is_business_quality_pass=False`, `recommendation="AVOID"`. **PASSED**
- **Scenario G**: Excellent Business with MOS Fail $\to$ `quality_gate="PASS"`, `is_business_quality_pass=True`, `recommendation="WAIT_FOR_MOS"`. **PASSED**
- **Scenario H**: Bank High Volatility ($CV=85\%$) $\to$ No industrial CFO/inventory false blocker, `quality_gate="PASS"`, `classification="CYCLICAL_QUALITY"`. **PASSED**
- **Scenario I**: Securities High Volatility ($CV=75\%$) $\to$ No industrial CFO false blocker, `quality_gate="PASS"`, `classification="CYCLICAL_QUALITY"`. **PASSED**
- **Scenario J**: 5Y vs 10Y Normalized Earnings Divergence $\to$ Traceable calculations in `normalized_pat_5y`, `normalized_pat_10y`, `pat_min_10y`, `pat_max_10y`. **PASSED**

### 2. Full Pytest Regression Suite
```text
pytest python/portfolio/tests/test_canonical_munger_decision_integrity.py \
       python/portfolio/tests/test_munger_liquidity_gate.py \
       python/portfolio/tests/test_munger_decision_consistency.py \
       python/portfolio/tests/test_munger_decision_forensic_consistency.py \
       python/portfolio/tests/test_canonical_share_basis_mos_integrity.py \
       python/portfolio/tests/test_corporate_action_normalization.py \
       python/portfolio/tests/test_munger_business_quality_earning_power.py \
       python/portfolio/tests/test_munger_cyclicality_volatility.py -v

============================ 110 passed in 18.72s =============================
```

### 3. Frontend Production Build
```text
npm run build
vite v6.4.3 building for production...
✓ 365 modules transformed.
✓ built in 4.82s
```

### 4. Real-Symbol DB Regression Summary
| Symbol | CV (%) | Peak Earnings | 5Y Norm PAT (B) | 10Y Norm PAT (B) | Quality Gate | Classification | Compounder | Req MOS | Canonical Decision | Rationale |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **BFC** | 43.9% | NO | 236.9 | 224.5 | PASS | `CYCLICAL_QUALITY` | NO | 50.0% | `BUY` | Fertilizer cyclical; solid balance sheet, clean forensics, MOS 67.6% $\ge$ 50% Req MOS. |
| **HAH** | 105.4% | YES | 441.7 | 269.4 | PASS | `CYCLICAL_QUALITY` | NO | 50.0% | `BUY` | Container shipping cyclical; peak earnings flagged, MOS 70.2% $\ge$ 50% Req MOS. |
| **FPT** | 64.1% | NO | 5,310.8 | 3,745.3 | PASS | `CYCLICAL_QUALITY` | NO | 20.0% | `CONDITIONAL_BUY` | Tech leader; long-term growth with high volatility from rapid scale, forensic watch triggers conditionality. |
| **ACB** | 88.2% | NO | 14,068.7 | 8,829.4 | PASS | `CYCLICAL_QUALITY` | NO | 25.0% | `WAIT_FOR_MOS` | Bank archetype; robust ROE, clean forensics, MOS 15.7% $<$ 25% Req MOS. |
| **DGC** | 115.2% | NO | 3,408.0 | 1,975.2 | PASS | `CYCLICAL_QUALITY` | NO | 50.0% | `BUY` | Phosphorus chemical supercycle; normalized PAT preserves mid-cycle earning power, MOS 56.3% $\ge$ 50%. |
| **TCB** | 83.2% | NO | 18,745.8 | 12,019.5 | PASS | `CYCLICAL_QUALITY` | NO | 30.0% | `WAIT_FOR_MOS` | Bank archetype; strong CASA & capital, MOS 7.8% $<$ 30% Req MOS. |
| **TPB** | 99.2% | NO | 5,160.0 | 3,248.8 | PASS | `CYCLICAL_QUALITY` | NO | 30.0% | `BUY` | Bank archetype; digital bank growth cycle, MOS 41.8% $\ge$ 30% Req MOS. |
| **TLG** | 44.9% | NO | 382.4 | 338.5 | PASS | `CYCLICAL_QUALITY` | NO | 30.0% | `WAIT_FOR_MOS` | Stationery manufacturer; steady business, negative MOS (-93.8%) properly blocks purchase. |

---

## Decisions
1. **Quality Pass vs Compounder Invariant**: `QUALITY_PASS` evaluates solvency, economic profitability, capital structure, and business model viability. `COMPOUNDER` evaluates secular earnings predictability. High earnings volatility ($CV \ge 0.35$) properly disqualifies a business from being a `COMPOUNDER`, but does not disqualify an economically healthy company from achieving `QUALITY_PASS` as a `CYCLICAL_QUALITY` business.
2. **Peak Earnings Architecture**: Peak earnings is not an accounting fraud or structural impairment; it is a cyclical valuation risk. Treating peak earnings via mid-cycle normalized earnings and required MOS markups ($+10\%$) is mathematically and economically sound.
3. **Financial Archetype Isolation**: Bank and securities earnings volatility is properly isolated from non-applicable industrial metrics (e.g. inventory turnover, industrial CFO).

---

## Result
Zero P0/P1 defects found. The QPort Munger decision and quality engine correctly and deterministically differentiates between `COMPOUNDER`, `CYCLICAL_QUALITY`, and `DETERIORATING_BUSINESS`. All 110 regression tests pass cleanly and frontend production build succeeds.

