# Owner Earnings & Maintenance CapEx Integrity Audit Report

**Date:** 2026-09-17  
**Task ID:** TASK-20260917-190  
**Scope:** Full architectural, economic, and mathematical audit of Owner Earnings, Maintenance CapEx classification, D&A/Working Capital double-count verification, and real PostgreSQL database regression.

---

## 1. Executive Summary

A thorough source-code and mathematical audit was conducted on `OwnerEarningsCalculator`, `ValuationEngine`, `canonical_valuation.py`, and `munger_analyzer.py`.

### Key Audit Verdicts:
1. **Owner Earnings Formula & Algebraic Integrity:**
   - Source Code Formula:
     $$\text{Owner Earnings} = \text{Net Income} + \text{D\&A} - \text{MaintCapEx} + \Delta\text{Working Capital}$$
     Where:
     $$\Delta\text{Working Capital} = \text{CFO} - (\text{Net Income} + \text{D\&A})$$
   - Algebraic Simplification:
     $$\text{Owner Earnings} = \text{CFO} - \text{MaintCapEx}$$
   - **No Double Counting:** D&A is added and removed identically; working capital adjustments are exact bridges.
2. **CapEx & Maintenance CapEx Classification:**
   - Canonical Fact Source: `CF.CAPEX` (cash outflows for fixed assets and intangibles from cash flow statement).
   - Maintenance CapEx Heuristic: $\text{MaintCapEx} = \min(\text{Total CapEx}, |\text{D\&A}|)$.
   - Growth CapEx Estimate: $\text{GrowthCapEx} = \max(0, \text{Total CapEx} - \text{MaintCapEx})$.
   - **Explicit Proxy Labeling:** Documented as `MIN_DEPRECIATION_CAPEX_PROXY` with confidence level `LOW` (Audit P1-5 rule), never misleadingly reported as an unassailable known fact.
3. **Normalization Methodologies:**
   - **`MID_CYCLE_MEDIAN` (for Cyclical / Commodity Archetypes):**
     $$\text{margin}_t = \frac{\text{OE}_t}{\text{Revenue}_t}, \quad \text{mid\_cycle\_OE} = \text{median}(\text{margin}_t) \times \text{median}(\text{Revenue}_t)$$
     Dampens outlier CapEx spikes and commodity boom/bust swings across 5–10 years.
   - **`LATEST_FY` / `LATEST_FY_CORE_ADJUSTED` (for Normal Growth Enterprises):**
     Anchors to latest FY owner earnings with core earning power floor ($50\% \times (\text{Net Income} + \text{D\&A} - \text{MaintCapEx})$) when single-year working capital buildup temporarily depresses CFO.
4. **Archetype Isolation:**
   - **Bank & Securities:** Strictly isolated from industrial CFO/CapEx/working capital. Bank valuation is executed exclusively via the Residual Income Model (RIM) based on BVPS and normalized ROE.

---

## 2. Real PostgreSQL Database Regression

Direct query execution against `qport_finance.canonical_facts` (286,120 facts in PostgreSQL at `127.0.0.1:5432`):

| Symbol | Archetype | Fiscal Window | 5Y Norm PAT | Latest CFO | Reported CapEx | Maint CapEx | Owner Earnings | OE/PAT Ratio | Normalization Method | Confidence | Model Status |
|---|---|---|---:|---:|---:|---:|---:|---:|---|---|---|
| **BFC** | ENTERPRISE | 2016–2024 (9Y) | 236.9B | 320.5B | 45.2B | 40.0B | **432.3B** | 182.5% | `MID_CYCLE_MEDIAN` | MEDIUM | `MODEL_VERIFIED` |
| **HAH** | ENTERPRISE | 2022–2024 (3Y) | 701.9B | 980.2B | 520.0B | 150.0B | **1,017.0B** | 144.9% | `MID_CYCLE_MEDIAN` | LOW | `MODEL_INCOMPLETE` |
| **FPT** | ENTERPRISE | 2025 (1Y) | 6,669.1B | 10,136.0B | 5,098.0B | 2,914.2B | **7,221.8B** | 108.3% | `LATEST_FY` | MEDIUM | `MODEL_VERIFIED` |
| **DGC** | ENTERPRISE | 2018–2024 (7Y) | 3,408.1B | 2,850.0B | 600.0B | 400.0B | **2,367.0B** | 69.4% | `MID_CYCLE_MEDIAN` | MEDIUM | `MODEL_VERIFIED` |
| **TLG** | ENTERPRISE | 2025 (1Y) | 389.0B | 220.0B | 125.0B | 93.0B | **127.0B** | 32.6% | `LATEST_FY` | MEDIUM | `MODEL_VERIFIED` |
| **ACB** | BANK | 2016–2025 (10Y) | 14,350.0B | *N/A (RIM)* | *N/A* | *N/A* | **RIM Valuation** | *N/A* | `RESIDUAL_INCOME` | MEDIUM | `MODEL_VERIFIED` |
| **TCB** | BANK | 2016–2025 (10Y) | 20,951.5B | *N/A (RIM)* | *N/A* | *N/A* | **RIM Valuation** | *N/A* | `RESIDUAL_INCOME` | MEDIUM | `MODEL_VERIFIED` |
| **TPB** | BANK | 2016–2025 (10Y) | 5,805.4B | *N/A (RIM)* | *N/A* | *N/A* | **RIM Valuation** | *N/A* | `RESIDUAL_INCOME` | MEDIUM | `MODEL_VERIFIED` |

---

## 3. Investigation of Task 189 HAH & FPT Figures

- **FPT 4,000.0B (Task 189):** Classified as **`SYNTHETIC_FIXTURE`** generated in unit test scenario comparisons. Real PostgreSQL 2025 valuation calculates $OE = 7,221.8\text{B}$ ($CFO = 10,136.0\text{B} - \text{MaintCapEx} = 2,914.2\text{B}$).
- **HAH 520.0B (Task 189):** Classified as **`SYNTHETIC_FIXTURE`** from test mock data. Real PostgreSQL calculates $OE = 1,017.0\text{B}$ under `MID_CYCLE_MEDIAN` (flagged `MODEL_INCOMPLETE` due to shallow 3-year history for shipping archetype).

---

## 4. Confirmed Invariants & Non-Defects

1. **No Double Counting:** D&A and Working Capital changes are algebraically sound and verified by Scenario I and Scenario J.
2. **Conservative CapEx Modeling:** $\min(\text{CapEx}, |\text{D\&A}|)$ accurately bounds maintenance CapEx and protects against over-penalizing compounders for massive growth CapEx investments.
3. **Archetype Routing:** Banks and Securities remain 100% isolated from industrial Owner Earnings formulas.
4. **Missing-Data Semantics:** Single-year calculation strictly raises `ValueError("OWNER_EARNINGS_INCOMPLETE")` when mandatory line items are missing; multi-year calculations transparently report confidence and input years.

---

## 5. Validation Evidence

- **New Test Suite Created:** `python/portfolio/tests/test_owner_earnings_maintenance_capex_integrity.py` (23/23 passed).
- **All 12 Munger & Valuation Test Suites:** 185/185 passed in 17.76s.
- **Frontend Production Build:** `npm run build` passed cleanly in 4.98s.
