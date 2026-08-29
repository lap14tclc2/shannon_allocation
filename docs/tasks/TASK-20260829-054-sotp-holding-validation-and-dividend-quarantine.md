# TASK-20260829-054: SOTP Holding Validation, Data Quality Quarantine & Model-Specific Analytics

- **ID**: `TASK-20260829-054`
- **Title**: SOTP Holding Validation, Stock Dividend Quarantine (>200%) & Holding Company Analytics
- **Status**: `completed`
- **Priority**: `high`
- **Date**: `2026-08-29`

## Requirement

### P0 DATA QUALITY
1. **Quarantine stock dividend >200%**:
   - Outlier filter in dividend canonicalization & observation parser: any stock dividend ratio > 2.0 (200%) must be quarantined / rejected as parsing noise.
   - Fix MBB 9237% / downstream 19460% calculation.

### P0 MODEL VALIDATION
2. **IDC validation gate**:
   - When `actual_model == "LEASE_CASHFLOW_DCF"` and `kcn_lease_parameters` is missing/null, `model_status` must be `MODEL_INCOMPLETE` (cannot be `MODEL_VERIFIED`).
3. **Material SOTP component**:
   - Unknown material components return `null` instead of `0 ₫`.
4. **`MODEL_VERIFIED` strict criteria**:
   - All material components valued (`!= null`), component source facts present, and component formula trace present.
5. **VEA ownership semantics**:
   - `gross_value * ownership_pct = net_value` (e.g. Honda VN 20% of 140k tỷ = 28k tỷ).
6. **Auditable source trace**:
   - Expose `source_fact_ids` and `formula_trace` on all SOTP components.

### P1 MODEL-SPECIFIC ANALYTICS
7. **HOLDING_COMPANY (VEA, etc.)**:
   - Remove generic EPV, Reverse DCF, DCF sensitivity from holding company output.
   - Add SOTP Component Sensitivity matrix (Associate multiple variation vs Holding discount).
   - Compute Holding cash quality = `dividends_received / associate_earnings`.
   - Use parent-only debt/cash for holdco net debt adjustments.

### P1 NORMALIZATION
8. **DGC / HPG cyclical normalization**:
   - Full 7–10Y historical cycle median.
   - Latest FY explicitly flagged as point-in-time, never normalized.
   - Proxy maintenance CapEx labeled `LOW` confidence.

### P2 UX
9. **Overview Table**:
   - Fill Base IV / MOS in overview table.
   - Rename DCF columns -> IV columns.
   - Display `archetype`, `valuation_model`, `model_status` badges.

## Acceptance Criteria
- [x] Stock dividends > 200% quarantined; MBB doesn't show 9237% / 19460%.
- [x] IDC without `kcn_lease_parameters` fails `MODEL_VERIFIED` gate with `MODEL_INCOMPLETE`.
- [x] Material SOTP unknown components return `null` (not 0) and carry source trace.
- [x] VEA ownership math is consistent (`gross * pct = net`).
- [x] Holding company report strips generic EPV / Reverse DCF and displays SOTP sensitivity + holding cash quality.
- [x] All unit and contract tests pass (`pytest`).
- [x] Frontend build succeeds (`npm run build`).

## Constraints and Invariants
- `BUY_AND_HOLD_INFORMATION_SYSTEM`.
- Ledger invariant preserved.

## Implementation Tasks
- [x] 1. Update dividend parser / canonicalizer to quarantine stock dividends > 200%.
- [x] 2. Update `ModelValidationGate` in `model_validation_gate.py` and `engine.py` for `LEASE_CASHFLOW_DCF` and SOTP component completeness.
- [x] 3. Update `SOTPComponent` with `source_fact_ids`, `formula_trace`, and correct `ownership_pct` math.
- [x] 4. Update `ValuationEngine` for `HOLDING_COMPANY` archetype (omit generic EPV/Reverse DCF, add SOTP sensitivity and holding cash quality).
- [x] 5. Update frontend `ValuationPage.jsx` and `OverviewTable` accordingly.
- [x] 6. Run pytest and frontend build to verify.

## Validation Evidence
1. **Pytest suite (30 passed in 0.79s)**:
   - `python/portfolio/tests/test_buffett_munger_rule_engine.py`
   - `python/portfolio/tests/test_value_engine.py`
   - `python/portfolio/tests/test_value_engine_audit_fixes.py`
   - `python/portfolio/tests/test_vi_labels.py`
   - `python/portfolio/tests/test_valuation_page_contract.py`
2. **Frontend build (`npm run build`)**:
   - `vite v6.4.3 building for production... ✓ built in 1.06s`
3. **Database dividend cleanup**:
   - Cleaned 22 symbols in PostgreSQL `qport_finance.dividend_observations` & `dividend_canonical` with stock dividend > 200%.
   - `MBB` 2021-01-06 raw artifact fixed; zero remaining canonical stock dividends > 200%.
4. **Live Valuation API Verification**:
   - `VEA`: `model_status: MODEL_VERIFIED`, `epv_result: None`, `reverse_dcf_result: None`, `holding_cash_quality.cash_conversion_rate_pct: 97.2%`, `sotp_sensitivity_matrix: Present`, Base IV: `36,891 ₫`.
   - `IDC`: `model_status: MODEL_INCOMPLETE`, `valuation_pill: MODEL_INCOMPLETE`, `verdict: Thiếu dữ liệu mô hình đặc thù...`

## Decisions
- Any stock dividend `> 2.0` (200%) in Vietnam is guaranteed to be a data parser artifact (e.g. share count / raw percentage). Outlier rule auto-quarantines observation with `status = 'REJECTED'`.
- Holding companies (like VEA) derive earnings from associate cash dividends rather than consolidated operating earnings; thus generic DCF, EPV and Reverse DCF are suppressed and replaced by SOTP Component Sensitivity & Cash Conversion metrics.

## Result
Completed all P0 Data Quality quarantine, P0 Model Validation gates, P1 Holding Analytics, and P2 UX enhancements. All 30 tests passing and frontend bundle verified.
