---
id: TASK-20260831-081
title: "Deduplicate i18n text helpers, signedMoney, num, and MetricCard component"
status: completed
priority: medium
date: 2026-08-31
---

## Requirement

Scan and deduplicate remaining repeated UI and helper logic across the project:
1. `text(en, vi)` inline lambdas across 11 frontend components/pages.
2. `signedMoney(value, locale)` across 3 pages (`PerformancePage`, `RiskPage`, `VietnamesePortfolioDashboard`).
3. `num(value, digits)` helper across `RiskPage` and `PortfolioAssessmentEnhancer`.
4. `Metric` component across dashboard pages.

## Context

Following `TASK-20260831-080`, several other common patterns were identified that were duplicated identically across multiple files:
- `const text = (en, vi) => locale === 'vi' ? vi : en;` in 11 components.
- `signedMoney(value, locale)` identically in 3 files.
- `num(value, digits)` identically in 2 files.
- `<Metric ... />` in 2 dashboard pages.

## Acceptance Criteria

- [ ] Export `chooseText(locale, en, vi)` from `frontend/src/i18n.js` and provide `text(en, vi)` helper in `useI18n(locale)`.
- [ ] Export `signedMoney(value, locale, suffix)` from `frontend/src/lib/format.js`.
- [ ] Ensure `formatNumber(value, digits)` handles non-finite numbers safely.
- [ ] Create/export reusable `Metric` component in `frontend/src/components/MetricCard.jsx`.
- [ ] Replace duplicated inline definitions across consuming components/pages.
- [ ] All existing contract and UI tests pass without regression.

## Constraints and Invariants

- Non-intrusive refactoring: Keep identical signatures and visual output.
- No changes to business logic or state structures.

## Implementation Tasks

- [x] Add `chooseText` to `frontend/src/i18n.js` and `text` method to `useI18n`.
- [x] Add `signedMoney` to `frontend/src/lib/format.js`.
- [x] Create `frontend/src/components/MetricCard.jsx`.
- [x] Refactor `PerformancePage.jsx`, `RiskPage.jsx`, `VietnamesePortfolioDashboard.jsx` to use `signedMoney`.
- [x] Refactor `RiskPage.jsx` and `PortfolioAssessmentEnhancer.jsx` to use shared `formatNumber`.
- [x] Refactor `PortfolioDashboardPage.jsx` and `VietnamesePortfolioDashboard.jsx` to use `MetricCard`.
- [x] Refactor `text` helpers across components to use `chooseText` / `useI18n`.
- [x] Run test suite and record validation evidence.
- [x] Update `docs/tasks/README.md`.

## Validation Evidence

Executed pytest suite covering UI contracts and services:
```bash
$env:PYTHONPATH='python;.'; .\.venv\Scripts\pytest python/portfolio/tests/test_locale.py python/portfolio/tests/test_fund_manager_review_contract.py python/portfolio/tests/test_valuation_page_contract.py python/portfolio/tests/test_dividend_source_and_ui_contract.py python/portfolio/tests/test_appearance_controls_contract.py python/portfolio/tests/test_service.py
```
Result: `42 passed in 13.47s (100% pass)`.

## Decisions

- Place `signedMoney` in `frontend/src/lib/format.js` alongside `money`, `pct`, `displayNumber`.
- Place `chooseText` in `frontend/src/i18n.js` alongside `useI18n`.
- Create `frontend/src/components/MetricCard.jsx` to unify metric display cards across dashboards.

## Result

- Deduplicated `text(en, vi)` inline lambdas across 11 components by routing through `chooseText(locale, en, vi)` and `useI18n`.
- Deduplicated `signedMoney(value, locale, suffix)` across 3 pages into `frontend/src/lib/format.js`.
- Deduplicated `num(value, digits)` across 2 components by leveraging `formatNumber`.
- Deduplicated `<Metric ... />` component across dashboard pages into `frontend/src/components/MetricCard.jsx`.
- Zero behavioral changes; all 42 relevant unit and contract tests pass cleanly.

