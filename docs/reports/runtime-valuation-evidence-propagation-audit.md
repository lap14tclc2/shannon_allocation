# Task 135 — Runtime Valuation & Evidence Propagation Audit Report

## Executive Summary
Audit of the end-to-end fundamental valuation and decision pipeline for golden symbols (`ACB`, `DGC`, `FPT`, `VIX`) across PostgreSQL `canonical_facts`, `finance_catalog`, `value_engine`, `ValueTrap`, `BusinessReview`, `InvestmentDecisionContext`, `runtime_decision`, Terminal API, and Business API.

- **Baseline Ingested Facts**: 104,066 deduplicated SSI canonical facts verified against PostgreSQL.
- **Valuation Readiness**: 100% READY for all 4 golden symbols (`ACB`, `DGC`, `FPT`, `VIX`).
- **Idempotency & Checksum**: PASS (`f6fdb3e5fe51e8c488c2ef8b70c5872446dda0573f2ffe4e40c9cb902e5e818d`).
- **Regression Test Suite**: 13/13 tests PASSED in `python/portfolio/tests/test_runtime_valuation_propagation.py`.
- **Mandatory Suite Collection**: 56/56 tests PASSED across all Task 135 regression test files.

---

## Terminal vs Business Consistency Matrix

| Symbol | Metric / Field | Terminal API | Business API | Consistency |
| :--- | :--- | :--- | :--- | :--- |
| **ACB** | Market Price | `25,000.0` VND | `25,000.0` VND | **MATCH** |
| | Valuation Status | `MODEL_VERIFIED` | `MODEL_VERIFIED` | **MATCH** |
| | Bear IV | `18,117.0` VND | `18,117.0` VND | **MATCH** |
| | Base IV | `27,056.0` VND | `27,056.0` VND | **MATCH** |
| | Bull IV | `35,051.2` VND | `35,051.2` VND | **MATCH** |
| | Margin of Safety | `7.60%` | `7.60%` | **MATCH** |
| | ValueTrap Status | `WATCH` | `WATCH` | **MATCH** |
| | BusinessReview | `BUSINESS_REVIEW` | `BUSINESS_REVIEW` | **MATCH** |
| | Decision | `REVIEW_BUSINESS` | `REVIEW_BUSINESS` | **MATCH** |
| | Primary Reason | `BUSINESS_REVIEW_INCOMPLETE` | `BUSINESS_REVIEW_INCOMPLETE` | **MATCH** |
| **DGC** | Market Price | `90,000.0` VND | `90,000.0` VND | **MATCH** |
| | Valuation Status | `MODEL_VERIFIED` | `MODEL_VERIFIED` | **MATCH** |
| | Bear IV | `65,870.3` VND | `65,870.3` VND | **MATCH** |
| | Base IV | `80,704.5` VND | `80,704.5` VND | **MATCH** |
| | Bull IV | `102,112.3` VND | `102,112.3` VND | **MATCH** |
| | Margin of Safety | `-11.52%` | `-11.52%` | **MATCH** |
| | ValueTrap Status | `WATCH` | `WATCH` | **MATCH** |
| | BusinessReview | `BUSINESS_REVIEW` | `BUSINESS_REVIEW` | **MATCH** |
| | Decision | `REVIEW_BUSINESS` | `REVIEW_BUSINESS` | **MATCH** |
| | Primary Reason | `BUSINESS_REVIEW_INCOMPLETE` | `BUSINESS_REVIEW_INCOMPLETE` | **MATCH** |
| **FPT** | Market Price | `130,000.0` VND | `130,000.0` VND | **MATCH** |
| | Valuation Status | `MODEL_VERIFIED` | `MODEL_VERIFIED` | **MATCH** |
| | Bear IV | `60,199.4` VND | `60,199.4` VND | **MATCH** |
| | Base IV | `95,282.6` VND | `95,282.6` VND | **MATCH** |
| | Bull IV | `141,263.2` VND | `141,263.2` VND | **MATCH** |
| | Margin of Safety | `-36.44%` | `-36.44%` | **MATCH** |
| | ValueTrap Status | `WATCH` | `WATCH` | **MATCH** |
| | BusinessReview | `BUSINESS_REVIEW` | `BUSINESS_REVIEW` | **MATCH** |
| | Decision | `REVIEW_BUSINESS` | `REVIEW_BUSINESS` | **MATCH** |
| | Primary Reason | `BUSINESS_REVIEW_INCOMPLETE` | `BUSINESS_REVIEW_INCOMPLETE` | **MATCH** |
| **VIX** | Market Price | `12,000.0` VND | `12,000.0` VND | **MATCH** |
| | Valuation Status | `MODEL_VERIFIED` | `MODEL_VERIFIED` | **MATCH** |
| | Bear IV | `16,245.8` VND | `16,245.8` VND | **MATCH** |
| | Base IV | `29,397.8` VND | `29,397.8` VND | **MATCH** |
| | Bull IV | `38,551.8` VND | `38,551.8` VND | **MATCH** |
| | Margin of Safety | `59.18%` | `59.18%` | **MATCH** |
| | ValueTrap Status | `CLEAR` | `CLEAR` | **MATCH** |
| | BusinessReview | `BUSINESS_REVIEW` | `BUSINESS_REVIEW` | **MATCH** |
| | Decision | `REVIEW_BUSINESS` | `REVIEW_BUSINESS` | **MATCH** |
| | Primary Reason | `BUSINESS_REVIEW_INCOMPLETE` | `BUSINESS_REVIEW_INCOMPLETE` | **MATCH** |

---

## Detailed Golden Symbol Audit

### 1. FPT (High-Quality Normal Enterprise Archetype)

- **CANONICAL DATA**
  - status: `READY`
  - provider: `ssi` (primary canonical)
  - latest FY: `2025`
- **FINANCIAL HISTORY**
  - status: `READY`
  - years: `2016`, `2017`, `2018`, `2019`, `2020`, `2021`, `2022`, `2023`, `2024`, `2025` (10 FYs available)
- **VALUATION SNAPSHOT**
  - status: `READY`
- **CANONICAL VALUATION**
  - status: `MODEL_VERIFIED`
  - Bear IV: `60,199.4`
  - Base IV: `95,282.6`
  - Bull IV: `141,263.2`
  - MOS: `-36.44%` (Market price 130,000 VND)
  - Recomputed MOS: `(95282.61 - 130000) / 95282.61 * 100 = -36.4362%` (Diff: 7.11e-15)
- **VALUE TRAP**
  - status: `WATCH` (Price > Bear IV)
  - missing evidence: `[]`
- **BUSINESS REVIEW**
  - status: `BUSINESS_REVIEW`
  - unknown dimensions: `UNDERSTANDABILITY`, `BUSINESS_QUALITY`, `MOAT`, `MANAGEMENT_CAPITAL_ALLOCATION`, `ACCOUNTING_RELIABILITY`
- **DECISION CONTEXT**
  - valuation preserved: `True` (Base IV: 95,282.6, Bear IV: 60,199.4)
  - value trap preserved: `True` (`WATCH`)
  - business review preserved: `True` (`BUSINESS_REVIEW`)
- **RUNTIME DECISION**
  - decision: `REVIEW_BUSINESS`
  - primary reason: `BUSINESS_REVIEW_INCOMPLETE`
  - blockers: `BUSINESS_REVIEW_INCOMPLETE`, `UNDERSTANDABILITY_UNKNOWN`, `MOAT_UNKNOWN`, `MANAGEMENT_EVIDENCE_UNKNOWN`, `ACCOUNTING_RELIABILITY_UNKNOWN`
- **FIRST BROKEN BOUNDARY**:
  `canonical_valuation.py` historically looked only for `IS.REVENUE.NET` instead of `IS.REVENUE.TOTAL`, causing `REVENUE_HISTORY` to register as missing in `ValueTrap`. Fixed by checking `IS.REVENUE.TOTAL` or `IS.REVENUE.NET`.
- **ROOT CAUSE**:
  Canonical code naming mismatch between raw SSI ingestion facts (`IS.REVENUE.TOTAL`) and adapter lookup (`IS.REVENUE.NET`).

---

### 2. ACB (Bank Archetype)

- **CANONICAL DATA**
  - status: `READY`
  - provider: `ssi` (primary canonical)
  - latest FY: `2025`
- **FINANCIAL HISTORY**
  - status: `READY`
  - years: `2011`–`2025` (15 FYs available)
- **VALUATION SNAPSHOT**
  - status: `READY`
- **CANONICAL VALUATION**
  - status: `MODEL_VERIFIED`
  - Bear IV: `18,117.0`
  - Base IV: `27,056.0`
  - Bull IV: `35,051.2`
  - MOS: `7.60%` (Market price 25,000 VND)
  - Recomputed MOS: `(27055.99 - 25000) / 27055.99 * 100 = 7.5990%` (Diff: 2.66e-15)
- **VALUE TRAP**
  - status: `WATCH` (Price > Bear IV)
  - missing evidence: `[]` (Bank archetype isolates CFO/CapEx/Inventory requirements as `NOT_APPLICABLE`)
- **BUSINESS REVIEW**
  - status: `BUSINESS_REVIEW`
  - unknown dimensions: `UNDERSTANDABILITY`, `MOAT`, `MANAGEMENT_CAPITAL_ALLOCATION`
- **DECISION CONTEXT**
  - valuation preserved: `True` (Base IV: 27,056.0, Bear IV: 18,117.0)
  - value trap preserved: `True` (`WATCH`)
  - business review preserved: `True` (`BUSINESS_REVIEW`)
- **RUNTIME DECISION**
  - decision: `REVIEW_BUSINESS`
  - primary reason: `BUSINESS_REVIEW_INCOMPLETE`
  - blockers: `BUSINESS_REVIEW_INCOMPLETE`, `UNDERSTANDABILITY_UNKNOWN`, `MOAT_UNKNOWN`, `MANAGEMENT_EVIDENCE_UNKNOWN`
- **FIRST BROKEN BOUNDARY**:
  None. Bank RIM model correctly processed book value and ROE without industrial cash-flow gates.
- **ROOT CAUSE**:
  N/A. Pipeline works deterministically.

---

### 3. DGC (Cyclical Enterprise Archetype)

- **CANONICAL DATA**
  - status: `READY`
  - provider: `ssi` (primary canonical)
  - latest FY: `2025`
- **FINANCIAL HISTORY**
  - status: `READY`
  - years: `2016`–`2025` (10 FYs available)
- **VALUATION SNAPSHOT**
  - status: `READY`
- **CANONICAL VALUATION**
  - status: `MODEL_VERIFIED`
  - Bear IV: `65,870.3`
  - Base IV: `80,704.5`
  - Bull IV: `102,112.3`
  - MOS: `-11.52%` (Market price 90,000 VND)
  - Recomputed MOS: `(80704.5 - 90000) / 80704.5 * 100 = -11.5180%` (Diff: 1.78e-15)
- **VALUE TRAP**
  - status: `WATCH` (Price > Bear IV)
  - missing evidence: `[]`
- **BUSINESS REVIEW**
  - status: `BUSINESS_REVIEW`
  - unknown dimensions: `UNDERSTANDABILITY`, `MOAT`, `MANAGEMENT_CAPITAL_ALLOCATION`
- **DECISION CONTEXT**
  - valuation preserved: `True` (Base IV: 80,704.5, Bear IV: 65,870.3)
  - value trap preserved: `True` (`WATCH`)
  - business review preserved: `True` (`BUSINESS_REVIEW`)
- **RUNTIME DECISION**
  - decision: `REVIEW_BUSINESS`
  - primary reason: `BUSINESS_REVIEW_INCOMPLETE`
  - blockers: `BUSINESS_REVIEW_INCOMPLETE`
- **FIRST BROKEN BOUNDARY**:
  None. Full-cycle normalization correctly evaluated Owner Earnings across 10 FYs.
- **ROOT CAUSE**:
  N/A. Pipeline works deterministically.

---

### 4. VIX (Securities Archetype)

- **CANONICAL DATA**
  - status: `READY`
  - provider: `ssi` (primary canonical)
  - latest FY: `2025`
- **FINANCIAL HISTORY**
  - status: `READY`
  - years: `2011`–`2025` (15 FYs available)
- **VALUATION SNAPSHOT**
  - status: `READY`
- **CANONICAL VALUATION**
  - status: `MODEL_VERIFIED`
  - Bear IV: `16,245.8`
  - Base IV: `29,397.8`
  - Bull IV: `38,551.8`
  - MOS: `59.18%` (Market price 12,000 VND)
  - Recomputed MOS: `(29397.75 - 12000) / 29397.75 * 100 = 59.1806%` (Diff: 7.11e-15)
- **VALUE TRAP**
  - status: `CLEAR`
  - missing evidence: `[]` (Securities archetype isolates CFO/NI cash conversion and inventory gates as `NOT_APPLICABLE`)
- **BUSINESS REVIEW**
  - status: `BUSINESS_REVIEW`
  - unknown dimensions: `UNDERSTANDABILITY`, `MOAT`, `MANAGEMENT_CAPITAL_ALLOCATION`
- **DECISION CONTEXT**
  - valuation preserved: `True` (Base IV: 29,397.8, Bear IV: 16,245.8, MOS: 59.18%)
  - value trap preserved: `True` (`CLEAR`)
  - business review preserved: `True` (`BUSINESS_REVIEW`)
- **RUNTIME DECISION**
  - decision: `REVIEW_BUSINESS`
  - primary reason: `BUSINESS_REVIEW_INCOMPLETE`
  - blockers: `BUSINESS_REVIEW_INCOMPLETE`
- **FIRST BROKEN BOUNDARY**:
  When `report.public_mos` is `None` (due to `verdict_status == AVOID_QUALITY`), `build_canonical_valuation` dropped `actual_mos_pct` to `None`. Fixed by adding explicit mathematical MOS fallback `(Base IV - Price) / Base IV * 100`.
- **ROOT CAUSE**:
  `public_mos` suppression in ValuationEngine scorecard omitted calculating scalar MOS in adapter output.

---

## Summary of Pipeline Invariants Verified
1. **Decision Precedence (Task 134)**: Preserved. `REVIEW_BUSINESS` is output when qualitative evidence is incomplete, taking precedence over `BUILD_RESERVE_FIRST` or `WAIT_FOR_MOS`.
2. **Quantitative Evidence Protection**: Quantitative valuation (Base/Bear/Bull IVs & MOS) remains intact and available even when qualitative evidence is `UNKNOWN`.
3. **Archetype Isolation**: Bank (`ACB`) and Securities (`VIX`) bypass industrial CFO/CapEx/Inventory gates without generating spurious `INSUFFICIENT_DATA` flags.
4. **Terminal vs Business API Single Authority**: Terminal and Business APIs consume identical `CanonicalValuation` and `runtime_decision` evidence payload.
5. **Units Invariant**:
   - Market prices and Intrinsic Values are both in `VND/share`.
   - Shares outstanding are represented as actual share count (e.g., `5,136,700,000` for ACB).
