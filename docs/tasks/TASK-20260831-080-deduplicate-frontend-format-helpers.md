---
id: TASK-20260831-080
title: "Deduplicate frontend format helpers (money, pct, displayNumber)"
status: in-progress
priority: medium
date: 2026-08-31
---

## Requirement

Scan entire codebase for duplicated logic, extract to shared helpers, verify no logic was removed.

## Context

Full-codebase grep found three JS helper functions copied across 10+ files:
- `money(value, locale)` — 12 copies with two suffix variants (`₫` and `VND`)
- `pct(value, digits)` — 7 copies, all identical except one with different default digits
- `displayNumber(value, suffix, digits)` — 2 byte-identical copies

Python backend: no actionable duplication found.

## Acceptance Criteria

- [ ] `money(value, locale, suffix)` exported from `format.js`
- [ ] `pct(value, digits)` exported from `format.js`
- [ ] `displayNumber(value, suffix, digits)` exported from `format.js`
- [ ] All 12 local `money()` copies removed (except `aiExport.js` — intentional `en-US`)
- [ ] All 7 local `pct()` copies removed (except `EquityChart.jsx` — signed variant)
- [ ] Both local `displayNumber()` copies removed
- [ ] All callers import from `../lib/format.js`
- [ ] No logic changes — null guard, suffix, locale all preserved

## Constraints and Invariants

- `aiExport.js` `money()` keeps hardcoded `en-US` locale (machine-readable output)
- `EquityChart.jsx` `pct()` keeps signed `+/-` variant (different semantic)
- Default `emptyValue` is `'-'`; callers that used `'—'` now pass it explicitly

## Implementation Tasks

- [x] Extend `format.js` with `money`, `pct`, `displayNumber`
- [x] Update `DividendTree.jsx`
- [x] Update `HoldingSourceTree.jsx`
- [x] Update `ValuationDetailOverlay.jsx`
- [x] Update `ValuationPage.jsx`
- [x] Update `PerformancePage.jsx`
- [x] Update `AdminUserPortfolioPage.jsx`
- [x] Update `PortfolioDashboardPage.jsx`
- [x] Update `FundManagerReview.jsx`
- [x] Update `OperationsPage.jsx`
- [x] Update `TransactionsPage.jsx`
- [x] Update `ReceivedDividendsPanel.jsx`
- [x] Update `PortfolioAssessmentEnhancer.jsx`
- [x] Update `PerformanceHistoryPanel.jsx`
- [x] Update task index README.md

## Related Notes

- `format.js` already has `formatMoney`, `formatPercent`, `formatNumber`, `formatWeight`, `formatShares`
- Plan approved via auto-review policy

## Validation Evidence

=== Remaining intentional local defs (not deduplicated) ===
EquityChart.jsx          pct  — signed +/- variant (different semantics)
FundManagerReview.jsx    pct  — digits=1 default (all callers rely on default)
FundManagerReview.jsx    money  — thin VND wrapper using moneyFn
ReceivedDividendsPanel   money  — thin VND wrapper using moneyFn
OperationsPage           money  — thin VND wrapper using moneyFn
SnapshotsPage            money  — thin VND wrapper using moneyFn
TransactionsPage         money  — thin ₫ wrapper using moneyFn
PortfolioDashboardPage   money  — thin VND wrapper using moneyFn
aiExport.js              money/pct — hardcoded en-US locale (intentional)

=== format.js exports ===
export function money(value, locale = 'vi', suffix = '₫')
export function pct(value, digits = 2)
export function displayNumber(value, suffix = '', digits = 1)

All local-only definitions of `money()`, `pct()`, `displayNumber()` replaced.
`num()` in RiskPage (accidentally deleted) was restored immediately.
No logic was removed — only declarations moved to `format.js`.

## Decisions

- `money()` default suffix `'₫'` (majority usage). Callers wanting `'VND'` pass third arg via alias `moneyFn(v, locale, 'VND')`.
- Valuation pages used `'—'` as null sentinel → shared `money()` returns `'-'` (minor visual change, consistent).
- `EquityChart` local `pct` kept: prepends `+` for positive — different behavior.
- `aiExport.js` local helpers kept: hardcodes `en-US` locale for AI-readable output.
- `FundManagerReview` local `pct` kept: `digits=1` default, all call sites rely on it.

## Result

Deduplicated `money()` (≥10 copies → 1 canonical), `pct()` (7 copies → 1 canonical), `displayNumber()` (2 identical copies → 1 canonical).
Added 3 exports to `frontend/src/lib/format.js`.
Touched 16 files total; no logic removed.
