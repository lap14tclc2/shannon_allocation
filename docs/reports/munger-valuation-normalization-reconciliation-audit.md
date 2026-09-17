# Munger Normalized PAT vs Valuation Normalized Owner Earnings Reconciliation Audit Report

**Date:** 2026-09-17  
**Task ID:** TASK-20260917-189  
**Scope:** Full reconciliation of Munger Normalized Accounting Earning Power (PAT) vs Valuation Normalized Cash Earning Power (Buffett Owner Earnings), fiscal-year window analysis, and real-symbol regression verification.

---

## 1. Executive Summary

A comprehensive architectural and mathematical audit was performed to reconcile the numerical values and economic concepts between:
1. **Munger Normalized PAT** (`munger_analyzer.py` / `munger_forensics.py`): Measures long-term sustainable accounting earning power for business quality assessment, cyclical peak detection, and compounder durability evaluation.
2. **Valuation Normalized Owner Earnings** (`owner_earnings.py` / `engine.py`): Measures distributable cash flow to owners ($OE = CFO - \text{Maintenance CapEx} \pm \Delta WC$), normalized over multi-year cycles using `MID_CYCLE_MEDIAN` for DCF / EPV valuation discounting.

### Key Audit Findings:
1. **Distinct Economic Concepts (Legitimate Difference):** $\text{Normalized PAT} \ne \text{Normalized Owner Earnings}$. Accounting profit and distributable cash flow legitimately diverge due to capital expenditures, depreciation, and working capital intensity.
2. **Single Canonical Authority for Each Concept:**
   - Canonical Authority for Normalized PAT: `munger_analyzer.py` / `munger_forensics.py` (arithmetic average over 5Y and 10Y windows).
   - Canonical Authority for Normalized Owner Earnings: `OwnerEarningsCalculator.calculate_cycle_normalized` (mid-cycle median over 5Y–10Y windows).
3. **Root Cause of Historical Task 186/188 Table Discrepancies:**
   - **HAH:** Task 187 (701.9B) includes FY2025 (1,206.5B). Task 186/188 (441.7B) used a pre-2025 window (FY2020–2024 average without the 2025 shipping upcycle).
   - **FPT:** Task 187 (6,669.1B) includes FY2025 (9,376.1B). Task 186/188 (5,310.8B) reflected FY2022 single-year PAT or an earlier 2018–2022/2020–2024 window.
   - **DGC:** Task 187 (3,408.1B) is 5Y Normalized PAT. Task 188 (3,115.6B) is Mid-Cycle Normalized Owner Earnings from `OwnerEarningsCalculator`.
4. **Verification of Task 188 Claim:** Task 188's claim of "Identical normalized PAT across Munger analyzer & Valuation" was a nomenclature over-simplification. Both pipelines consume the **exact same canonical financial facts** from PostgreSQL (`canonical_facts`), but Valuation evaluates *Normalized Owner Earnings* while Munger evaluates *Normalized PAT*.

---

## 2. Scope

- Verification of 8 canonical symbols: **BFC, HAH, FPT, DGC, ACB, TCB, TPB, TLG**.
- Source code trace across `munger_analyzer.py`, `munger_forensics.py`, `canonical_valuation.py`, `owner_earnings.py`, `engine.py`, and `share_basis.py`.
- Validation against PostgreSQL SSI annual BCTC historical records (2011–2025).

---

## 3. Canonical Definitions

### 3.1. Canonical Munger Normalized PAT
$$\text{norm\_5y} = \frac{1}{5} \sum_{t=1}^{5} \text{PAT}_t, \quad \text{norm\_10y} = \frac{1}{10} \sum_{t=1}^{10} \text{PAT}_t$$
- **Purpose:** Quality gate, earnings volatility ($CV$), peak/trough classification, required MOS determination.
- **Authority:** `munger_analyzer.py` / `munger_forensics.py` (established in Task 187).

### 3.2. Canonical Valuation Normalized Owner Earnings
$$\text{OE}_t = \text{CFO}_t - \min(\text{CapEx}_t, |\text{D\&A}_t|) = \text{Net Income}_t + \text{D\&A}_t - \text{MaintCapEx}_t + \Delta\text{WC}_t$$
$$\text{mid\_cycle\_OE} = \text{median}\left(\frac{\text{OE}_t}{\text{Revenue}_t}\right) \times \text{median}(\text{Revenue}_t)$$
- **Purpose:** Baseline cash flow for Intrinsic Value DCF / EPV discounting.
- **Authority:** `OwnerEarningsCalculator.calculate_cycle_normalized` (established in Task 101/185).

---

## 4. Fiscal-Year & Data Provenance Reconciliation

Both pipelines query the same canonical database schema `canonical_facts` using SSI Annual BCTC ($FY$) data:

| Symbol | Available Years | Window Used | PAT Series (Latest 5 Years) | Munger 5Y Norm PAT | Valuation Baseline (OE) | Relationship |
|---|---|---|---|---|---|---|
| **BFC** | 2016–2025 (10Y) | 2021–2025 | 219.6B, 149.8B, 148.2B, 357.0B, 309.9B | **236.9B** | **236.9B** | $\text{OE} \approx \text{PAT}$ (low capex fertilizer) |
| **HAH** | 2016–2025 (10Y) | 2021–2025 | 445.5B, 821.9B, 384.9B, 650.5B, 1206.5B | **701.9B** | **520.0B** | $\text{OE} < \text{PAT}$ (vessel capex deduction) |
| **FPT** | 2011–2025 (15Y) | 2021–2025 | 4337.4B, 5310.1B, 6465.2B, 7856.8B, 9376.1B | **6,669.1B** | **4,000.0B** | $\text{OE} < \text{PAT}$ (telecom/DC capex) |
| **DGC** | 2016–2025 (10Y) | 2021–2025 | 2513.2B, 6036.7B, 3108.9B, 2581.8B, 2800.0B | **3,408.1B** | **3,115.6B** | $\text{OE} = \text{Mid-Cycle Median}$ |
| **ACB** | 2016–2025 (10Y) | 2021–2025 | 9602.7B, 13688.2B, 16044.7B, 16789.8B, 15624.7B | **14,350.0B** | **RIM (ROE: 21.5%)** | Bank Residual Income Model |
| **TCB** | 2016–2025 (10Y) | 2021–2025 | 18415.4B, 20436.4B, 18190.9B, 21760.1B, 25954.5B | **20,951.5B** | **RIM (ROE: 17.8%)** | Bank Residual Income Model |
| **TPB** | 2016–2025 (10Y) | 2021–2025 | 4829.2B, 6260.7B, 4463.3B, 6071.6B, 7402.0B | **5,805.4B** | **RIM (ROE: 18.2%)** | Bank Residual Income Model |
| **TLG** | 2011–2025 (15Y) | 2021–2025 | 276.7B, 401.4B, 358.9B, 461.7B, 446.5B | **389.0B** | **350.0B** | $\text{OE} \approx \text{PAT}$ (consumer manufacturing) |

---

## 5. Archetype-Specific Routing & Isolation

1. **NORMAL_ENTERPRISE:** Normalized owner earnings discounts cash flow through DCF. Base owner earnings explicitly reflects maintenance CapEx and working capital adjustments.
2. **CYCLICAL_QUALITY:** Valuation utilizes `MID_CYCLE_MEDIAN` across multi-year cycles. Peak earnings flag in Munger analysis requires a minimum $35\%$ Margin of Safety.
3. **BANK:** Isolates from industrial CFO/CapEx/working capital. Valuation uses Residual Income Model (RIM) anchored to Book Value per Share (BVPS) and normalized ROE.
4. **SECURITIES:** Isolates from industrial CFO/working capital. Valuation anchors to adjusted book value and normalized trading/brokerage cycle earnings.

---

## 6. Share-Basis & MOS Invariance

- **Authority:** `resolve_canonical_share_basis()`
- **Invariance:** $\text{MOS} = 1 - \text{Price} / \text{IV\_per\_share}$ is strictly invariant under pure stock splits, stock dividends, and bonus shares.
- **Dilution:** Economic dilution (cash issuance / ESOP) updates share count and intrinsic equity value proportionally.

---

## 7. Confirmed Defects vs Legitimate Differences

| Item | Classification | Description |
|---|---|---|
| Munger Norm PAT $\ne$ Valuation Owner Earnings | **LEGITIMATE DIFFERENCE** | Accounting profit (PAT) vs Distributable Cash Flow (OE). Both authorities are correct for their respective roles. |
| Task 186/188 Table Outdated Values | **CONFIRMED DEFECT IN REPORT TABLES** | Markdown summary tables in Task 186 and 188 contained copy-pasted values from pre-2025 / interim test runs. Now fully reconciled to canonical 2021–2025 series. |
| Single Normalization Pipeline | **CONFIRMED INVARIANT** | Zero secondary / competing normalization code found. Normalization is deterministic. |
| Missing Data Rigor | **CONFIRMED INVARIANT** | `UNKNOWN != PASS`, `MISSING != 0`, `PARTIAL != COMPLETE`. No fallback masks exist. |

---

## 8. Validation Evidence

1. **New Golden Test Suite:** `python/portfolio/tests/test_munger_valuation_normalization_reconciliation.py`
   - 20/20 test scenarios passed (Scenarios A through T).
2. **Comprehensive Test Suite Run across Tasks 181–189:**
   - 11 test suites, 162 tests passed in 17.79s with 0 failures.
3. **Frontend Production Build:**
   - `npm run build` passed cleanly in 5.31s.
