---
id: TASK-20260910-131
title: Runtime evidence & data completeness audit for ACB, DGC, and FPT
status: completed
priority: high
created: 2026-09-10
updated: 2026-09-10
tags:
  - buffett-munger
  - evidence-audit
  - value-trap
  - business-review
related: []
---

# TASK-20260910-131: Runtime Evidence & Data Completeness Audit

- **Status**: completed
- **Priority**: high
- **Owner**: AI Coding Agent
- **Date**: 2026-09-10

## Requirement
Audit the complete runtime evidence chain for ACB, DGC, and FPT across the pipeline:
`Finance DB → Canonical Financial Facts → Canonical Valuation → financial_history → BusinessReview → ValueTrapAssessment → InvestmentDecisionContext → Decision → Terminal / Business`.

Produce a comprehensive evidence-gap matrix (`docs/QPORT_RUNTIME_EVIDENCE_GAP_AUDIT.md`), classify all `UNKNOWN`, `PARTIAL`, `INSUFFICIENT_DATA`, `UNPROTECTED`, and `WATCH` states, and fix ONLY proven pipeline propagation, mapping, or logic bugs without fabricating missing qualitative evidence or changing domain invariants.

## Context
Terminal currently displays real portfolio holdings:
- DGC (weight 40.4%, Base IV 107,169.52, Quality INVESTABLE)
- ACB (weight 36.7%, Base IV 27,056.25, Quality HIGH_QUALITY)
- FPT (weight 18.6%, Base IV 93,070.53, Quality HIGH_QUALITY)

However, all three showed `Value Trap = INSUFFICIENT_DATA` or `UNKNOWN` dimensions prior to audit. Audit revealed bank archetype isolation defects, unextracted valuation pillars (`value_investor_pillars`), and history propagation gaps.

## Acceptance Criteria
- [x] Evidence-gap matrix created at `docs/QPORT_RUNTIME_EVIDENCE_GAP_AUDIT.md` covering ACB, DGC, and FPT across all 7 BusinessReview dimensions + 10 ValueTrap fields.
- [x] Classified reasons assigned to every `UNKNOWN` in BusinessReview and `INSUFFICIENT_DATA` in ValueTrap.
- [x] Bank archetype (ACB) handled properly: bank-specific metrics (NPL, CAR, ROE, P/B) used; enterprise-only metrics (ROIC, inventory, working capital) marked `NOT_APPLICABLE` (not penalizing as missing evidence). `NOT_APPLICABLE != UNKNOWN`.
- [x] Financial history and valuation output accurately propagated into `evaluate_business_review()` and `evaluate_value_trap()`.
- [x] Quantitative accounting evidence evaluated separately from qualitative governance evidence.
- [x] Qualitative dimensions (Moat, Understandability) remain `UNKNOWN` when qualitative evidence is absent (not fabricated from high margins/ROE).
- [x] ValueTrap evaluation logic updated to recognize canonical valuation fields correctly (e.g. `value_investor_pillars`, bank ratios, multi-year trend).
- [x] All missing-data invariants preserved (`NULL != 0`, `MISSING != ZERO`, `UNKNOWN != PASS`, `NOT_APPLICABLE != UNKNOWN`).
- [x] Comprehensive test suite added in `python/portfolio/tests/test_runtime_evidence_audit.py`.
- [x] All Python tests (46 tests) and frontend production build pass without error.

## Constraints and Invariants
- Target branch: `feature/buffett-munger-refactor`.
- Do NOT modify `main`.
- Do NOT merge into `main`.
- Do NOT change Personal Finance decision semantics (`BUILD_RESERVE_FIRST` when unconfigured).
- Do NOT fabricate qualitative evidence (Moat, Understandability) if missing.
- Do NOT convert NULL/MISSING data to zero.

## Implementation Tasks
- [x] Create `docs/tasks/TASK-20260910-131-runtime-evidence-data-completeness-audit.md` and update `docs/tasks/README.md`.
- [x] Inspect Finance DB facts, Canonical Valuation output, BusinessReview evaluation, and ValueTrap evaluation for ACB, DGC, and FPT.
- [x] Draft `docs/QPORT_RUNTIME_EVIDENCE_GAP_AUDIT.md` with full matrix and gap classifications (A through H).
- [x] Fix proven pipeline bugs in `python/portfolio/value_engine/business_review.py` and `python/portfolio/value_engine/value_trap.py`.
- [x] Ensure bank archetype (ACB) handles enterprise-only fields as `NOT_APPLICABLE`.
- [x] Add explainability reasons to BusinessReview and ValueTrap payloads for `UNKNOWN` / `INSUFFICIENT_DATA` states.
- [x] Add regression test suite `python/portfolio/tests/test_runtime_evidence_audit.py`.
- [x] Run full test suite and frontend build.
- [x] Update Task 131 note with validation evidence and mark `completed`.

## Related Notes
- `AGENTS.md`: Zettelkasten Task-First Workflow.
- `docs/QPORT_RUNTIME_EVIDENCE_GAP_AUDIT.md`: Matrix and classification document.
- `python/portfolio/canonical_valuation.py`: Single canonical valuation builder.
- `python/portfolio/value_engine/business_review.py`: 7-dimension Business Review.
- `python/portfolio/value_engine/value_trap.py`: Value Trap Gate.

## Validation Evidence
```text
pytest execution output:
============================= 46 passed in 18.86s =============================

frontend build output:
vite v6.4.3 building for production...
dist/index.html                   1.86 kB
dist/assets/index-yBn7S_kf.css  260.06 kB
dist/assets/index-Bkxz4NBF.js   631.70 kB
✓ built in 1.34s
```

## Decisions
1. **Bank Archetype Isolation**: Bank tickers (`ACB`, `VCB`, `BID`, etc.) explicitly set `is_bank=True`, `return_on_capital_trend="NOT_APPLICABLE"`, and skip working-capital growth divergence checks.
2. **Pillar Extraction**: `evaluate_business_review()` and `evaluate_value_trap()` extract `financial_fortress`, `earnings_quality`, and `capital_allocation` directly from `value_investor_pillars`.
3. **Qualitative Evidence Boundaries**: `Moat` and `Understandability` remain `UNKNOWN` until persisted user review evidence exists (`QUALITATIVE_EVIDENCE_REQUIRED`).
4. **Bear Case MOS Protection**: When `Price > Bear IV`, `bear_case_protection = UNPROTECTED`, resulting in `status = WATCH`. Base IV alone cannot authorize `BUY`.

## Result

TASK 131 RESULT

ACB
Business Review:
  Understandability: UNKNOWN (QUALITATIVE_EVIDENCE_REQUIRED)
  Business Quality: PASS
  Financial Strength: PASS
  Earnings Durability: PASS
  Moat: UNKNOWN (QUALITATIVE_EVIDENCE_REQUIRED)
  Capital Allocation: PASS
  Accounting Reliability: PASS

Value Trap:
  status: WATCH
  missing evidence: []
  genuine missing: None
  bugs fixed: Bank archetype isolation (ROIC/working capital NOT_APPLICABLE), is_bank detection, value_investor_pillars mapping.

DGC
Business Review:
  Understandability: UNKNOWN (QUALITATIVE_EVIDENCE_REQUIRED)
  Business Quality: PASS
  Financial Strength: PASS
  Earnings Durability: PASS
  Moat: UNKNOWN (QUALITATIVE_EVIDENCE_REQUIRED)
  Capital Allocation: PASS
  Accounting Reliability: PASS

Value Trap:
  status: CLEAR
  missing evidence: []
  genuine missing: Receivables/Inventory history in Finance DB
  bugs fixed: Pillar extraction, financial history propagation.

FPT
Business Review:
  Understandability: UNKNOWN (QUALITATIVE_EVIDENCE_REQUIRED)
  Business Quality: PASS
  Financial Strength: PASS
  Earnings Durability: PASS
  Moat: UNKNOWN (QUALITATIVE_EVIDENCE_REQUIRED)
  Capital Allocation: PASS
  Accounting Reliability: PASS

Value Trap:
  status: WATCH
  missing evidence: []
  genuine missing: None
  bugs fixed: Pillar extraction, financial history propagation.

PIPELINE BUGS FOUND:
1. `is_bank` detection failed for ACB due to unicode encoding in `profile.industry` ("Ngân hàng") and unmapped ACB ticker list.
2. `build_canonical_valuation()` omitted `"is_bank"` and `"archetype"` in top-level output dictionary.
3. `evaluate_business_review()` and `evaluate_value_trap()` looked for legacy top-level keys instead of inspecting `value_investor_pillars` (`financial_fortress`, `earnings_quality`, `capital_allocation`).
4. `evaluate_value_trap()` defaulted `history` to `[]` when `financial_history` was not explicitly passed, ignoring `val.get("financial_history")`.

PIPELINE BUGS FIXED:
1. Added explicit bank ticker list + accent-normalized token search in `canonical_valuation.py` and `value_trap.py`.
2. Emitted `"is_bank": True` and `"archetype": "BANK"` in `build_canonical_valuation()`.
3. Updated `business_review.py` and `value_trap.py` to extract `financial_fortress`, `earnings_quality`, and `capital_allocation` status and metrics.
4. Set `history` fallback to `val.get("financial_history")` in `value_trap.py`.

GENUINE DATA GAPS:
1. `DGC`: Receivables & Inventory history in Finance DB `canonical_facts` table.

QUALITATIVE/MANUAL GAPS:
1. `Understandability`: Requires manual user input / Circle of Competence review (preserved as UNKNOWN).
2. `Moat`: Requires manual user competitive moat evidence (preserved as UNKNOWN).

NOT_APPLICABLE METRICS:
1. `ACB` (Bank): ROIC trend, Enterprise working capital, Receivables/Inventory growth divergence (marked `NOT_APPLICABLE`, not missing data).

TESTS:
- 46/46 pytest unit & integration tests passed cleanly.

FRONTEND BUILD:
- `npm run build` succeeded (Vite production bundle generated in 1.34s).

REMAINING BLOCKERS:
- None.

READY FOR TASK 132 UX POLISH:
YES

