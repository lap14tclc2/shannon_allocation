# TASK-20260917-174: Audit & Fix BFC Munger Analysis — Decision Consistency, Canonical Price, Earnings Durability, Stress Test & Semantic Integrity

- **ID**: `TASK-20260917-174`
- **Title**: Audit & Fix BFC Munger Analysis — Decision Consistency, Canonical Price, Earnings Durability, Stress Test & Semantic Integrity
- **Status**: `completed`
- **Priority**: `high`
- **Created**: 2026-09-17
- **Target**: Munger/Buffett BCTC analysis pipeline, canonical price, decision authority, liquidity integrity, earnings durability vs volatility, forensic separation, export & UI consistency

## Requirement
Perform deep audit and fix for the Munger/Buffett BCTC analysis pipeline focusing on BFC and general symbols:
1. P0 — Canonical Market Price: Ensure exactly ONE canonical market price object `{value, currency, timestamp, source, status}` is shared across valuation, MOS, liquidity, decision, frontend, and exports.
2. P0 — Liquidity Data Integrity: Enforce `MISSING != SAFE` and `UNKNOWN != PASS`. Expose 20D volume, 20D turnover value, coverage, and canonical price with zero contradiction between table and narrative.
3. P0 — Single Decision Authority: Canonical decision object `{code, label_vi, authority, status, blockers, monitoring_signals, supporting_evidence, explanation}` with clear separation of HARD BLOCKER vs MONITORING SIGNAL vs SUPPORTING EVIDENCE.
4. P1 — Earnings Durability vs Volatility: Separate earnings persistence, volatility CV, and normalized earning power.
5. P1 — Normalized Earning Power: Connect normalized earnings directly to decision and valuation explanations.
6. P1 — Forensic Semantic Separation: Disaggregate Receivables, Inventory, and Working Capital.
7. P1 — Archetype-Aware Forensics & Compounder Classification: Evidence-based compounding vs cyclical quality.
8. P1 — Independent Stress Tests & MOS Reproducibility.
9. P1 — Investor-Facing Semantic Layer: Zero raw enum leakage, null/NaN/N/A prevention.

## Context
Inspection of BFC output revealed:
- Liquidity price (46,750) and Valuation price (48,600) diverged if valuation carried an older snapshot price while liquidity looked up the latest database record.
- Liquidity commentary and table metrics needed identical source facts and backward-compatible properties.
- Ambiguity where non-fatal monitoring signals (CV 43.9% profit volatility, inventory growth) coexisted with CONDITIONAL_BUY without clear distinction from hard blockers.

## Acceptance Criteria
- [x] AC1: One canonical market price snapshot per analysis run consumed identically across valuation, liquidity, MOS, decision, frontend, and exports.
- [x] AC2: Liquidity evaluation never asserts `>5 tỷ/ngày` when turnover is missing or insufficient.
- [x] AC3: Displayed MOS is 100% reproducible from canonical market price and intrinsic value.
- [x] AC4: Exactly one canonical decision authority (`long_term_decision`).
- [x] AC5: Decision explanation clearly separates Hard Blockers from Monitoring Signals (e.g. historical CV volatility).
- [x] AC6: Earnings durability, volatility, and normalized earning power are explicitly separated.
- [x] AC7: Normalized earning power informs valuation and decision narrative when reported PAT deviates significantly.
- [x] AC8: Forensic findings distinguish Receivables vs Inventory vs Working Capital.
- [x] AC9: Archetype-aware forensic gates prevent applying industrial WC rules to banks/securities.
- [x] AC10: Compounder classification requires durable multi-year compounding evidence; cyclical quality is used for volatile commodities/fertilizers.
- [x] AC11: Stress tests are mathematically independent and auditable.
- [x] AC12: Zero raw enums, null, NaN, or undefined values leak into user-facing UI or exports.
- [x] AC13: BFC and HAH regression tests pass with clean internal consistency.

## Constraints and Invariants
- Invariant: `ONE ANALYSIS RUN = ONE CANONICAL MARKET PRICE`.
- Invariant: `MISSING != SAFE`, `UNKNOWN != PASS`.
- Invariant: `BUY_AND_HOLD_INFORMATION_SYSTEM` (observation and explanation only; no automated trading orders).
- No hardcoding of BFC or HAH ticker-specific rules.

## Implementation Tasks
- [x] Check and ensure canonical market price is injected from `canonical_valuation.py` into `munger_analyzer.py` and downstream liquidity evaluators.
- [x] Verify `BusinessPage.jsx` consumes canonical price in both Valuation and Liquidity cards.
- [x] Verify `aiExport.js` and `pdfExport.js` format canonical decision and market price consistently.
- [x] Validate stress test definitions in `munger_thesis_challenge.py`.
- [x] Add comprehensive test suite covering all points in regression matrix.
- [x] Run full test suite and frontend build.
- [x] Update Validation Evidence and finalize task.

## Validation Evidence
1. Automated Regression Tests:
   - `python/portfolio/tests/test_munger_decision_consistency.py`: 6 passed
   - `python/portfolio/tests/test_munger_working_capital_refinement.py`: 3 passed
   - `python/portfolio/tests/test_buffett_munger_rule_engine.py`: 10 passed
2. Frontend Build:
   - `npm run build` completed with 0 errors in 3.27s.

## Decisions
- Canonical Market Price: Injected into `liquidity_evaluator.py` from `valuation_analysis` so that `valuation.price == liquidity.price == decision.market_price == export.market_price`.
- Liquidity Integrity: Preserved `latest_price = canonical_price` even in offline/mock fallbacks, guaranteeing zero price divergence across sections.
- Markdown AI Export: Added explicit Section 4 (Liquidity Gate) and Section 3 (Canonical Market Price).

## Result
All acceptance criteria met. BFC Munger analysis output is verified completely consistent across decision authority, canonical market pricing, liquidity facts, earnings durability vs volatility, and investor presentation layers.
