# Complete Corporate Action Economic Classification Audit (TASK-181)

`status: completed`
`created: 2026-09-17`
`completed: 2026-09-17`

---

## Requirement
Audit and verify that QPort strictly distinguishes between:
1. **Non-economic share-basis events**: `STOCK_SPLIT`, `REVERSE_SPLIT`, `STOCK_DIVIDEND`, `BONUS_SHARES` (which preserve business value and maintain MOS invariance).
2. **Potentially economic share-count events**: `NEW_SHARE_ISSUANCE`, `ESOP`, `RIGHTS_ISSUE`, `MA_SHARE_ISSUANCE`, `OTHER_DILUTION` (which issue new claims against the company and cause economic dilution).

Verify that stock dividend normalization does NOT normalize actual dilution as a non-economic event, and missing corporate-action data does not silently assume no dilution.

---

## Acceptance Criteria
- [x] **AC1**: Explicit separation between 4 non-economic actions and 5+ economic dilution action types in `corporate_action_normalizer.py` and `dilution.py`.
- [x] **AC2**: Deterministic tests for Pure 1:10 split (Case A) and Multiple splits (Case B) showing MOS invariance.
- [x] **AC3**: Deterministic test for Actual new share issuance (Case C) showing it is not treated as a pure split.
- [x] **AC4**: Missing corporate-action classification (Case D) flagged as `UNEXPLAINED_SHARE_CHANGE` / `UNCERTAIN` instead of zero dilution.
- [x] **AC5**: Stock dividend normalization does NOT normalize economic dilution events.
- [x] **AC6**: Full IV/share and MOS provenance verified with single authority.
- [x] **AC7**: Regression tests for BFC and HAH passing.

---

## Implementation Summary

### What Was Already Proven
1. `STOCK_DIVIDEND` MOS invariance (Case B): Pure 1:10 split or stock dividend preserves identical MOS percentage (40.00%).
2. `CASH_DIVIDEND` no-double-counting: Dividends are cash distributions, not added on top of DCF/RIM intrinsic equity value.
3. Historical DPS economic preservation: Normalized DPS $\times$ Current Shares = Total Cash Paid.
4. EPS normalization: Eliminates artificial EPS collapse when share counts increase via non-economic events.
5. Portfolio position invariance: Lot cost basis and total invested capital are preserved across splits and stock dividends.

### What Was Missing
- Explicit automated test asserting `is_non_economic` vs `is_economic_dilution` across all 10 enum types.
- Explicit test proving that missing corporate action data produces `UNEXPLAINED_SHARE_CHANGE` instead of silently assuming 0% dilution.
- Explicit test proving that stock dividend forward multiplier ignores cash share issuances.

### What Was Changed
- Added `test_corporate_action_types_strictly_distinguished` in `python/portfolio/tests/test_canonical_share_basis_mos_integrity.py`.
- Added `test_missing_corporate_action_not_silently_ignored` in `python/portfolio/tests/test_canonical_share_basis_mos_integrity.py`.
- Added `test_stock_dividend_normalization_does_not_mask_actual_dilution` in `python/portfolio/tests/test_canonical_share_basis_mos_integrity.py`.

---

## Validation Evidence

### Test Suite Execution
```powershell
$env:DATABASE_URL="postgresql://qport:qport@127.0.0.1:5432/qport"; $env:PYTHONPATH=".;python"; $env:PYTHONIOENCODING="utf-8"; pytest python/portfolio/tests/test_canonical_share_basis_mos_integrity.py python/portfolio/tests/test_corporate_action_normalization.py -v
```
Output: **29 passed in 0.91s** (100% pass).

### Exact Authorities
- **Share-Basis Authority**: `resolve_canonical_share_basis()` in `python/portfolio/value_engine/share_basis.py`.
- **MOS Authority**: `calculate_canonical_mos()` in `python/portfolio/value_engine/share_basis.py`.
- **Frontend / API Consumers**: `build_canonical_valuation()` in `python/portfolio/canonical_valuation.py` consumed identically across `/api/portfolio/valuation/{symbol}`, `/api/portfolio/business/{symbol}`, Munger Candidate Screener, and AI Export.

### Remaining Limitations
- Rights issues with complex sub-market pricing require prospectus inputs for exact value-transfer calculation; in the absence of prospectus data, system conservatively caps confirmed dilution at the share-issuance ratio and marks unexplained residual as `UNCERTAIN`.
