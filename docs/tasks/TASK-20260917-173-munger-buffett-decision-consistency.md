# TASK-20260917-173: Final consistency audit and fix for Munger/Buffett decision output

- **ID**: `TASK-20260917-173`
- **Title**: Final consistency audit and fix for Munger/Buffett decision output
- **Status**: `completed`
- **Priority**: `high`
- **Created**: 2026-09-17
- **Target**: Munger/Buffett BCTC analysis engine + decision authority + liquidity + canonical market price + semantic presentation

## Requirement
Perform final consistency audit and fix for Munger/Buffett analysis engine, decision authority, liquidity pipeline, canonical market price snapshots, and frontend/export semantic presentation layer across all tickers (with BFC/HAH regression verification).
1. Fix Liquidity Data Integrity: Enforce invariant `MISSING != SAFE`. Never assert trading value > 5B/day if trading value data is missing. Align frontend property bindings with backend payload.
2. Canonical Market Price: Single authoritative `market_price` object (`value`, `currency`, `timestamp`, `source`, `data_status`) consumed identically across valuation, MOS, liquidity, decision, frontend summary, AI export, and PDF export. Displayed MOS must be perfectly reproducible from canonical price and IV.
3. Single Decision Authority: One authoritative canonical decision object (`long_term_decision`) with explicit trace (`decision_trace`, `watch_coexistence_rationale`, `monitoring_reasons`, `blocking_reasons`). Zero conflicting/secondary decision overrides.
4. Explain "CÓ THỂ MUA CÓ ĐIỀU KIỆN": Explicitly separate Hard Blockers from Monitoring Signals (e.g. historical earnings volatility CV 43.9%, working capital inventory watch).
5. Separate Earnings Persistence vs Volatility vs Normalized Earning Power and inform valuation uncertainty if reported PAT is materially above normalized earnings.
6. Semantic separation for Working Capital (Receivables vs Inventory vs Aggregate WC).
7. Compounder classification based on durable compounding evidence vs cyclical peak.
8. Metric-backed Thesis-break conditions and independent stress test validation.

## Context
Regression testing on BFC revealed discrepancies:
- Trading value displayed "Chưa đủ dữ liệu" while commentary asserted ">5 tỷ/ngày" due to UI property mismatch (`avg_trading_value_20d` vs `avg_trading_value_20d_billion`) and fallback rule in evaluator.
- Multiple prices existed between live market catalog and valuation report snapshots.
- Ambiguity in CONDITIONAL_BUY explanation where non-fatal monitoring signals were phrased as blocking risks.

## Acceptance Criteria
- [x] AC1: No unsupported liquidity claim when trading value is missing.
- [x] AC2: One canonical market-price snapshot per analysis run.
- [x] AC3: Displayed MOS is reproducible from displayed canonical price and IV.
- [x] AC4: Exactly one authoritative long-term decision.
- [x] AC5: Every CONDITIONAL_BUY condition is explicitly traceable.
- [x] AC6: Monitoring signals are separated from blockers.
- [x] AC7: Earnings persistence is separated from earnings volatility.
- [x] AC8: Normalized earning power is visible and incorporated into the explanation of valuation uncertainty.
- [x] AC9: Receivables, inventory and working-capital findings are semantically separated.
- [x] AC10: Compounder classification is evidence-based and not merely PAT CAGR + ROE.
- [x] AC11: Thesis-break conditions are generated from actual available evidence.
- [x] AC12: Stress tests are mathematically independent and auditable.
- [x] AC13: No violation of missing-data invariants (`NULL != 0`, `MISSING != SAFE`, `UNKNOWN != PASS`).
- [x] AC14: No HAH/BFC-specific hard-coded rules.
- [x] AC15: No unnecessary valuation-model changes.
- [x] AC16: Frontend/API/export/PDF use the same canonical decision.
- [x] AC17: HAH regression passes.
- [x] AC18: BFC regression passes.
- [x] AC19: Relevant test suite passes.

## Constraints and Invariants
- BUY_AND_HOLD_INFORMATION_SYSTEM: Observation and explanation only; no automated trading orders.
- Zero raw enum leakage to frontend or export.
- Generic engine fixes only; no ticker-specific hardcoding.

## Implementation Tasks
- [x] Fix liquidity evaluator contract and classification logic (`liquidity_evaluator.py`).
- [x] Fix frontend liquidity property mapping (`BusinessPage.jsx`).
- [x] Standardize canonical market price snapshot in `munger_analyzer.py` and `canonical_valuation.py`.
- [x] Enrich canonical decision object with `monitoring_reasons`, `watch_coexistence_rationale`, and normalized earnings context.
- [x] Audit thesis challenge and stress tests (`munger_thesis_challenge.py`).
- [x] Verify frontend (`BusinessPage.jsx`), `aiExport.js`, `pdfExport.js` consume canonical fields.
- [x] Run pytest suite and frontend build.
- [x] Verify HAH and BFC analysis outputs.

## Related Notes
- `TASK-20260916-170`: Audit and Fix Munger/Buffett Financial-Analysis Engine Based on HAH Output
- `TASK-20260917-171`: Fix ReferenceError formatDecision in aiExport.js
- `TASK-20260917-172`: Refine Munger forensic semantics, decision trace, and compounder classification

## Validation Evidence
1. Unit & Regression Tests:
   - `test_munger_decision_consistency.py`: 4 passed (100%)
   - `test_munger_working_capital_refinement.py`: 3 passed (100%)
   - `test_buffett_munger_rule_engine.py` & `test_forensic_mos_correctness.py`: 19 passed, 2 skipped
2. Frontend Build:
   - `npm run build` in `frontend/` succeeded with 0 errors (built in 3.40s).

## Decisions
- Liquidity Evaluation: Never assert `>5B/day` when trading value is missing or < 5.0. Added backward-compatible aliases (`avg_trading_value_20d`, `avg_trading_value_20d_billion`, `trading_day_coverage`, `trading_day_coverage_pct`, `trading_days_found`).
- Canonical Market Price: `canonical_valuation.py` packages authoritative `market_price: {value, currency, timestamp, source, data_status}` consumed identically by all downstream consumers.
- CONDITIONAL_BUY Trace: Decision explanation clearly states core gates (MOS, business quality) have passed while distinguishing monitoring signals (earnings volatility CV, working capital pressure, peak earnings vs normalized earning power) without misrepresenting them as hard blockers.
- Thesis Break: Generated dynamically from BCTC metrics (ROE/ROIC decay, CFO/PAT deterioration, dilution, debt leverage).

## Result
All acceptance criteria met. Canonical decision authority, market price lineage, liquidity integrity, and forensic presentation are verified consistent across Python value engine, frontend views, and export artifacts.

