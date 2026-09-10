# QPort Runtime Evidence & Data Completeness Audit

**Date**: 2026-09-10  
**Target Branch**: `feature/buffett-munger-refactor`  
**Task**: `TASK-20260910-131`  

---

## 1. Executive Summary

This document performs a complete audit of the runtime evidence chain in QPort:
```text
Finance DB
    ↓
Canonical Financial Facts
    ↓
Canonical Valuation (`build_canonical_valuation`)
    ↓
financial_history
    ↓
BusinessReview (`evaluate_business_review`)
    ↓
ValueTrapAssessment (`evaluate_value_trap`)
    ↓
InvestmentDecisionContext
    ↓
Decision
    ↓
Terminal / Business Workspace
```

for the target portfolio holdings:
- **ACB** (Bank Archetype)
- **DGC** (Cyclical Enterprise)
- **FPT** (Growth Enterprise)

### Gap Classification Taxonomy
- **A. SOURCE_DATA_MISSING**: Financial facts not present in raw DB / provider.
- **B. CANONICAL_MAPPING_MISSING**: Raw DB facts exist but not mapped into `CanonicalFact` or `ValuationReport`.
- **C. PIPELINE_PROPAGATION_MISSING**: Data available in `build_canonical_valuation()` (e.g. `value_investor_pillars`) but not passed or extracted by `evaluate_business_review()` / `evaluate_value_trap()`.
- **D. DERIVED_METRIC_NOT_IMPLEMENTED**: Metric formula not implemented in engine.
- **E. QUALITATIVE_EVIDENCE_REQUIRED**: Manual/User qualitative review required (e.g. Moat, Understandability).
- **F. ARCHETYPE_NOT_APPLICABLE**: Enterprise metric not applicable to bank archetype (e.g. ROIC, Inventory, Working Capital). Must NOT count as missing/unknown.
- **G. GENUINELY_INSUFFICIENT_EVIDENCE**: Multi-year history or required facts genuinely incomplete.
- **H. BUG**: Code logic defect or wrong field name access.

---

## 2. Business Review Evidence Gap Matrix

| Symbol | Dimension | Required Evidence | Finance DB Available? | Canonical Fact Available? | Valuation Output Available? | BusinessReview Receives It? | Current State | Expected State | Gap Classification | Action |
|---|---|---|---|---|---|---|---|---|---|---|
| **ACB** | Understandability | Manual qualitative review / Circle of Competence | No | No | No | No | UNKNOWN | UNKNOWN | E. QUALITATIVE_EVIDENCE_REQUIRED | Keep UNKNOWN, document reason |
| **ACB** | Business Quality | ROE, Quality Scorecard, Base MOS | Yes | Yes | Yes | Yes | PASS | PASS | None | Validated |
| **ACB** | Financial Strength | Capital Adequacy / `financial_fortress` pillar | Yes | Yes | Yes (`FORTRESS`) | No (unmapped key) | UNKNOWN | PASS | C. PIPELINE_PROPAGATION_MISSING | Map `financial_fortress` pillar into `financial_strength` |
| **ACB** | Earnings Durability | Multi-year ROE stability (5y avg 20.8%) | Yes | Yes | Yes | Partial | UNKNOWN | PASS | C. PIPELINE_PROPAGATION_MISSING | Read `financial_history` & `earnings_quality` pillar |
| **ACB** | Moat | Competitive moat / regulatory advantage | No | No | No | No | UNKNOWN | UNKNOWN | E. QUALITATIVE_EVIDENCE_REQUIRED | Keep UNKNOWN, document reason |
| **ACB** | Management / CapAlloc | Share dilution breakdown (`non_economic_share_change_5y_pct`) | Yes | Yes | Yes (`EXCELLENT`) | No (unmapped key) | UNKNOWN | PASS | C. PIPELINE_PROPAGATION_MISSING | Map `capital_allocation` pillar into `management_capital_allocation` |
| **ACB** | Accounting Reliability | Quantitative earnings quality / ROE consistency | Yes | Yes | Yes (`EXCELLENT`) | No (unmapped key) | UNKNOWN | PASS | C. PIPELINE_PROPAGATION_MISSING | Map quantitative accounting quality while preserving qualitative governance as UNKNOWN |
| **DGC** | Understandability | Manual qualitative review | No | No | No | No | UNKNOWN | UNKNOWN | E. QUALITATIVE_EVIDENCE_REQUIRED | Keep UNKNOWN, document reason |
| **DGC** | Business Quality | Quality Scorecard, Base MOS | Yes | Yes | Yes | Yes | PASS | PASS | None | Validated |
| **DGC** | Financial Strength | Net Debt / Equity, Cash, `financial_fortress` pillar | Yes | Yes | Yes (`FORTRESS`) | No | UNKNOWN | PASS | C. PIPELINE_PROPAGATION_MISSING | Map `financial_fortress` pillar |
| **DGC** | Earnings Durability | Multi-year earnings & CFO history (cyclicality aware) | Yes | Yes | Yes | Partial | UNKNOWN | WATCH | C. PIPELINE_PROPAGATION_MISSING | Read `financial_history` & evaluate cyclical durability |
| **DGC** | Moat | Chemical cost advantage / phosphate access evidence | No | No | No | No | UNKNOWN | UNKNOWN | E. QUALITATIVE_EVIDENCE_REQUIRED | Keep UNKNOWN, document reason |
| **DGC** | Management / CapAlloc | Share dilution, CapEx efficiency, retained earnings | Yes | Yes | Yes (`SAFE`) | No | UNKNOWN | PASS | C. PIPELINE_PROPAGATION_MISSING | Map `capital_allocation` pillar |
| **DGC** | Accounting Reliability | CFO vs Net Income, cash conversion ratio | Yes | Yes | Yes | No | UNKNOWN | PASS | C. PIPELINE_PROPAGATION_MISSING | Map `earnings_quality` pillar |
| **FPT** | Understandability | Manual qualitative review | No | No | No | No | UNKNOWN | UNKNOWN | E. QUALITATIVE_EVIDENCE_REQUIRED | Keep UNKNOWN, document reason |
| **FPT** | Business Quality | Quality Scorecard, Base MOS | Yes | Yes | Yes | Yes | PASS | PASS | None | Validated |
| **FPT** | Financial Strength | Net Debt, Cash, `financial_fortress` pillar | Yes | Yes | Yes (`FORTRESS`) | No | UNKNOWN | PASS | C. PIPELINE_PROPAGATION_MISSING | Map `financial_fortress` pillar |
| **FPT** | Earnings Durability | 5-10y net profit CAGR, ROIC trend | Yes | Yes | Yes | Partial | UNKNOWN | PASS | C. PIPELINE_PROPAGATION_MISSING | Read `financial_history` & `cagr_5y_net_profit` |
| **FPT** | Moat | Tech workforce / market leader advantage evidence | No | No | No | No | UNKNOWN | UNKNOWN | E. QUALITATIVE_EVIDENCE_REQUIRED | Keep UNKNOWN, document reason |
| **FPT** | Management / CapAlloc | Share dilution status, dividend record | Yes | Yes | Yes (`EXCELLENT`) | No | UNKNOWN | PASS | C. PIPELINE_PROPAGATION_MISSING | Map `capital_allocation` pillar |
| **FPT** | Accounting Reliability | CFO vs Net Income, receivables growth | Yes | Yes | Yes | No | UNKNOWN | PASS | C. PIPELINE_PROPAGATION_MISSING | Map `earnings_quality` pillar |

---

## 3. Value Trap Gate Evidence Gap Matrix

| Symbol | Field / Gate | Required Evidence | Finance DB Available? | Canonical Fact Available? | Valuation Output Available? | ValueTrap Receives It? | Current State | Expected State | Gap Classification | Action |
|---|---|---|---|---|---|---|---|---|---|---|
| **ACB** | `is_bank` / Archetype | Bank sector token / ticker ACB | Yes | Yes | Yes (DB) | No (`is_bank=None`) | `False` | `True` | H. BUG / C. PIPELINE_PROPAGATION_MISSING | Add ACB ticker to bank list & pass `"is_bank"` in `build_canonical_valuation` |
| **ACB** | `return_on_capital_trend` | ROIC series | N/A | N/A | N/A | Evaluated as missing | UNKNOWN | NOT_APPLICABLE | F. ARCHETYPE_NOT_APPLICABLE | Exclude ROIC from bank missing_data |
| **ACB** | Inventory / Receivables | Working capital divergence | N/A | N/A | N/A | Evaluated as missing | UNKNOWN | NOT_APPLICABLE | F. ARCHETYPE_NOT_APPLICABLE | Exclude inventory/receivables from bank missing_data |
| **ACB** | `balance_sheet_status` | Solvency / `financial_fortress` pillar | Yes | Yes | Yes (`FORTRESS`) | No (unmapped) | UNKNOWN | SAFE | C. PIPELINE_PROPAGATION_MISSING | Map `value_investor_pillars.financial_fortress` |
| **ACB** | `accounting_status` | Accounting reliability / `earnings_quality` pillar | Yes | Yes | Yes (`EXCELLENT`) | No (unmapped) | UNKNOWN | PASS | C. PIPELINE_PROPAGATION_MISSING | Map `value_investor_pillars.earnings_quality` |
| **ACB** | `dilution_status` | Share dilution classification | Yes | Yes | Yes (`NON_ECONOMIC`) | No (unmapped) | UNKNOWN | OK | C. PIPELINE_PROPAGATION_MISSING | Map `value_investor_pillars.capital_allocation` |
| **ACB** | `bear_case_protection` | Market price vs Bear IV | Yes (px: 22,250) | Yes (Bear IV: 18,117) | Yes | Yes | UNPROTECTED | UNPROTECTED | None | Validated (Price > Bear IV => WATCH) |
| **ACB** | Overall Status | All gate checks combined | Yes | Yes | Yes | Partial | INSUFFICIENT_DATA | WATCH | C. PIPELINE_PROPAGATION_MISSING | Correct pipeline propagation => status becomes WATCH |
| **DGC** | `normalized_earnings_trend` | Multi-year earnings trend | Yes (10y hist) | Yes | Yes | No (`financial_history` not read from `val`) | UNKNOWN | GROWING | C. PIPELINE_PROPAGATION_MISSING | Fallback `history` to `val.get("financial_history")` |
| **DGC** | `cash_conversion_status` | Multi-year CFO / Net Income ratio | Yes (10y hist) | Yes | Yes | No (`financial_history` not read from `val`) | UNKNOWN | CONFIRMED | C. PIPELINE_PROPAGATION_MISSING | Read `financial_history` from `val` |
| **DGC** | `bear_case_protection` | Market price vs Bear IV | Yes (px: 47,000) | Yes (Bear IV: 107,169) | Yes | Yes | PROTECTED | PROTECTED | None | Validated (Price < Bear IV) |
| **DGC** | Deterioration Classification | Peak cycle earnings drop vs structural impairment | Yes | Yes | Yes | Partial | LIKELY_CYCLICAL | LIKELY_CYCLICAL | None | Validated (Cyclical, not structural) |
| **DGC** | Overall Status | All gate checks combined | Yes | Yes | Yes | Partial | INSUFFICIENT_DATA | CLEAR | C. PIPELINE_PROPAGATION_MISSING | Correct pipeline propagation => status becomes CLEAR |
| **FPT** | `normalized_earnings_trend` | Multi-year earnings trend | Yes (10y hist) | Yes | Yes | No (`financial_history` not read from `val`) | UNKNOWN | GROWING | C. PIPELINE_PROPAGATION_MISSING | Fallback `history` to `val.get("financial_history")` |
| **FPT** | `cash_conversion_status` | Multi-year CFO / Net Income ratio | Yes (10y hist) | Yes | Yes | No (`financial_history` not read from `val`) | UNKNOWN | CONFIRMED | C. PIPELINE_PROPAGATION_MISSING | Read `financial_history` from `val` |
| **FPT** | `bear_case_protection` | Market price vs Bear IV | Yes (px: 72,400) | Yes (Bear IV: 93,070) | Yes | Yes | PROTECTED | PROTECTED | None | Validated (Price < Bear IV) |
| **FPT** | Overall Status | All gate checks combined | Yes | Yes | Yes | Partial | INSUFFICIENT_DATA | CLEAR | C. PIPELINE_PROPAGATION_MISSING | Correct pipeline propagation => status becomes CLEAR |

---

## 4. Root Causes & Action Plan

1. **Bank Archetype Bug (`H. BUG` / `F. ARCHETYPE_NOT_APPLICABLE`)**:
   - `build_canonical_valuation()` failed to detect ACB as a bank due to accent encoding in `profile.industry` ("Ngân hàng").
   - `build_canonical_valuation()` did not emit `"is_bank": True` or `"archetype": "BANK"` in the top-level output dict.
   - `evaluate_value_trap()` penalized ACB by treating ROIC, Inventory, and Receivables histories as missing data (`ROIC_HISTORICAL_SERIES`, `INVENTORY_HISTORY`, `RECEIVABLES_HISTORY`).
   - **Fix**: Add explicit bank ticker fallback (`ACB`, `VCB`, `BID`, `CTG`, `MBB`, `TCB`, `VPB`, `STB`, `HDB`, `TPB`, `VIB`, `MSB`, `LPB`, `EIB`, `OCB`, `SSB`, `BAB`, `NAB`) and normalize search tokens (`ngn hng`, `ngan hang`). Explicitly include `"is_bank": is_bank` in the returned dictionary. In `evaluate_value_trap()`, treat ROIC, Inventory, and Receivables as `NOT_APPLICABLE` for banks.

2. **Unextracted Valuation Pillars (`C. PIPELINE_PROPAGATION_MISSING`)**:
   - `build_canonical_valuation()` constructs `value_investor_pillars` containing `financial_fortress`, `earnings_quality`, and `capital_allocation`.
   - `evaluate_business_review()` and `evaluate_value_trap()` looked for legacy top-level keys like `val["financial_strength"]` or `val["dilution_status"]` instead of inspecting `value_investor_pillars`.
   - **Fix**: Update `evaluate_business_review()` and `evaluate_value_trap()` to extract status, metrics, and evidence from `value_investor_pillars` (e.g. `financial_fortress.status`, `capital_allocation.status`, `earnings_quality.status`).

3. **Financial History Defaulting (`C. PIPELINE_PROPAGATION_MISSING`)**:
   - When callers invoked `evaluate_value_trap(symbol, valuation_report)` without explicitly passing `financial_history`, `history` defaulted to `[]`, ignoring `valuation_report.get("financial_history")`.
   - **Fix**: Fallback `history = financial_history or val.get("financial_history") or []`.

4. **Qualitative Evidence Boundaries (`E. QUALITATIVE_EVIDENCE_REQUIRED`)**:
   - `Moat` and `Understandability` lack persisted qualitative evidence records.
   - **Fix**: Preserve `UNKNOWN` state for Moat and Understandability. Add diagnostic `reasons` explaining that qualitative review evidence has not been submitted by the user, adhering to the invariant `QUALITATIVE_EVIDENCE_REQUIRED`.

5. **Diagnostic Explainability (`Explainability Contract`)**:
   - Add detailed `reasons` to `BusinessReviewResult` and `ValueTrapAssessment` payloads so that every `UNKNOWN` or `INSUFFICIENT_DATA` state is clearly explained to the UI and callers.
