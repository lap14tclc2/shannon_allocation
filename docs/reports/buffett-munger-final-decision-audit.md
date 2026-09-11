# Real Runtime Audit Report: Final Buffett-Munger Decision Precedence

**Execution Date**: 2026-09-10  
**Database**: PostgreSQL (`qport_finance.canonical_facts`)  
**Authority**: `python/policy/engine.py` -> `evaluate_decision()`  

---

## Executive Summary

This report documents the real runtime audit of QPort's deterministic Buffett-Munger decision engine across the 4 golden universe symbols (`ACB`, `DGC`, `FPT`, `VIX`).

Under incomplete qualitative evidence (where `Understandability`, `Moat`, `Management`, and `Accounting Qualitative` evidence remain legitimately `UNKNOWN`), all 4 symbols correctly resolve to `REVIEW_BUSINESS` with primary reason `BUSINESS_REVIEW_INCOMPLETE`.

The policy engine preserves all blocking reasons in `blocking_reasons[]` and prevents un-evaluated business risks from being masked as `WAIT_FOR_MOS` or `BUILD_RESERVE_FIRST`.

---

## Detailed Symbol Audit Results

### 1. ACB (Bank Archetype)

- **Archetype**: `BANK`
- **Existing holding?**: `False` (Candidate)
- **Market price**: `0.0` (Market price unavailable / invalid)
- **BusinessReview**: `BUSINESS_REVIEW`
- **Understandability**: `UNKNOWN`
- **Moat**: `UNKNOWN`
- **Management**: `UNKNOWN`
- **Accounting**: `UNKNOWN`
- **Circle of Competence**: `UNKNOWN`
- **ValueTrap**: `INSUFFICIENT_DATA`
- **Bear IV**: `None`
- **Base IV**: `None`
- **Bull IV**: `None`
- **MOS**: `None`
- **PBS**: `UNKNOWN`
- **Available long-term capital**: `0.0 VND`
- **Position weight**: `0.0%`
- **Position capacity**: `35.0%`
- **Decision**: `REVIEW_BUSINESS`
- **Primary reason**: `BUSINESS_REVIEW_INCOMPLETE`
- **All blockers**:
  1. `BUSINESS_REVIEW_INCOMPLETE`
  2. `UNDERSTANDABILITY_UNKNOWN`
  3. `CIRCLE_OF_COMPETENCE_UNKNOWN`
  4. `MOAT_UNKNOWN`
  5. `MANAGEMENT_EVIDENCE_UNKNOWN`
  6. `ACCOUNTING_RELIABILITY_UNKNOWN`
  7. `VALUE_TRAP_INSUFFICIENT`
  8. `VALUATION_UNAVAILABLE`
  9. `PERSONAL_BALANCE_SHEET_UNKNOWN`
- **Warnings**: `[]`
- **Why not BUY?**: Business review incomplete, qualitative evidence UNKNOWN, value trap data insufficient, valuation unavailable, personal balance sheet unconfigured.
- **Why not SELL?**: Candidate position (not an existing holding). No confirmed structural or accounting failure.
- **What must change?**: Complete qualitative evidence evaluation (Understandability, Moat, Management) and configure Personal Balance Sheet.

---

### 2. DGC (Normal Enterprise Archetype)

- **Archetype**: `NORMAL_ENTERPRISE`
- **Existing holding?**: `False` (Candidate)
- **Market price**: `0.0`
- **BusinessReview**: `BUSINESS_REVIEW`
- **Understandability**: `UNKNOWN`
- **Moat**: `UNKNOWN`
- **Management**: `UNKNOWN`
- **Accounting**: `UNKNOWN`
- **Circle of Competence**: `UNKNOWN`
- **ValueTrap**: `INSUFFICIENT_DATA`
- **Bear IV**: `None`
- **Base IV**: `None`
- **Bull IV**: `None`
- **MOS**: `None`
- **PBS**: `UNKNOWN`
- **Available long-term capital**: `0.0 VND`
- **Position weight**: `0.0%`
- **Position capacity**: `35.0%`
- **Decision**: `REVIEW_BUSINESS`
- **Primary reason**: `BUSINESS_REVIEW_INCOMPLETE`
- **All blockers**:
  1. `BUSINESS_REVIEW_INCOMPLETE`
  2. `UNDERSTANDABILITY_UNKNOWN`
  3. `CIRCLE_OF_COMPETENCE_UNKNOWN`
  4. `MOAT_UNKNOWN`
  5. `MANAGEMENT_EVIDENCE_UNKNOWN`
  6. `ACCOUNTING_RELIABILITY_UNKNOWN`
  7. `VALUE_TRAP_INSUFFICIENT`
  8. `VALUATION_UNAVAILABLE`
  9. `PERSONAL_BALANCE_SHEET_UNKNOWN`
- **Warnings**: `[]`
- **Why not BUY?**: Qualitative evidence UNKNOWN, valuation unavailable, PBS unconfigured.
- **Why not SELL?**: No existing holding, no structural failure.
- **What must change?**: Complete qualitative research and supply financial data for valuation model.

---

### 3. FPT (Normal Enterprise Archetype)

- **Archetype**: `NORMAL_ENTERPRISE`
- **Existing holding?**: `False` (Candidate)
- **Market price**: `0.0`
- **BusinessReview**: `BUSINESS_REVIEW`
- **Understandability**: `UNKNOWN`
- **Moat**: `UNKNOWN`
- **Management**: `UNKNOWN`
- **Accounting**: `UNKNOWN`
- **Circle of Competence**: `UNKNOWN`
- **ValueTrap**: `INSUFFICIENT_DATA`
- **Bear IV**: `None`
- **Base IV**: `None`
- **Bull IV**: `None`
- **MOS**: `None`
- **PBS**: `UNKNOWN`
- **Available long-term capital**: `0.0 VND`
- **Position weight**: `0.0%`
- **Position capacity**: `35.0%`
- **Decision**: `REVIEW_BUSINESS`
- **Primary reason**: `BUSINESS_REVIEW_INCOMPLETE`
- **All blockers**:
  1. `BUSINESS_REVIEW_INCOMPLETE`
  2. `UNDERSTANDABILITY_UNKNOWN`
  3. `CIRCLE_OF_COMPETENCE_UNKNOWN`
  4. `MOAT_UNKNOWN`
  5. `MANAGEMENT_EVIDENCE_UNKNOWN`
  6. `ACCOUNTING_RELIABILITY_UNKNOWN`
  7. `VALUE_TRAP_INSUFFICIENT`
  8. `VALUATION_UNAVAILABLE`
  9. `PERSONAL_BALANCE_SHEET_UNKNOWN`
- **Warnings**: `[]`
- **Why not BUY?**: Business quality unverified, qualitative evidence UNKNOWN.
- **Why not SELL?**: Candidate position, no hard exit trigger.
- **What must change?**: Perform qualitative review and complete valuation input facts.

---

### 4. VIX (Securities Archetype)

- **Archetype**: `SECURITIES`
- **Existing holding?**: `False` (Candidate)
- **Market price**: `0.0`
- **BusinessReview**: `BUSINESS_REVIEW`
- **Understandability**: `UNKNOWN`
- **Moat**: `UNKNOWN`
- **Management**: `UNKNOWN`
- **Accounting**: `UNKNOWN`
- **Circle of Competence**: `UNKNOWN`
- **ValueTrap**: `INSUFFICIENT_DATA`
- **Bear IV**: `None`
- **Base IV**: `None`
- **Bull IV**: `None`
- **MOS**: `None`
- **PBS**: `UNKNOWN`
- **Available long-term capital**: `0.0 VND`
- **Position weight**: `0.0%`
- **Position capacity**: `35.0%`
- **Decision**: `REVIEW_BUSINESS`
- **Primary reason**: `BUSINESS_REVIEW_INCOMPLETE`
- **All blockers**:
  1. `BUSINESS_REVIEW_INCOMPLETE`
  2. `UNDERSTANDABILITY_UNKNOWN`
  3. `CIRCLE_OF_COMPETENCE_UNKNOWN`
  4. `MOAT_UNKNOWN`
  5. `MANAGEMENT_EVIDENCE_UNKNOWN`
  6. `ACCOUNTING_RELIABILITY_UNKNOWN`
  7. `VALUE_TRAP_INSUFFICIENT`
  8. `VALUATION_UNAVAILABLE`
  9. `PERSONAL_BALANCE_SHEET_UNKNOWN`
- **Warnings**: `[]`
- **Why not BUY?**: Business evidence incomplete, PBS unconfigured.
- **Why not SELL?**: Candidate position.
- **What must change?**: Perform qualitative evidence analysis for securities broker archetype.

---

## System Invariants Verification

1. **Terminal & Business Consistency**: `/api/portfolio/terminal` and `/api/portfolio/business/{symbol}` consume `svc.runtime_decision(symbol)` which invokes `evaluate_decision(ctx)`. Exactly ONE decision authority exists.
2. **Zero Evidence Fabrication**: No `UNKNOWN` field was hardcoded to `PASS`.
3. **No SSI Ingestion Mutation**: Canonical facts remain untouched.
4. **No Quarterly Dependency**: FY-only policy engine confirmed.
5. **No Risk-Allocation Regression**: ERC/volatility metrics remain decoupled from investment policy decisions.
