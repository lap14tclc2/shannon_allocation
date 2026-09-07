# TASK-20260907-107: Fix Missing Risk Summary Metrics and Empty Portfolio Risk Card

---
id: TASK-20260907-107
title: Fix Missing Risk Summary Metrics and Empty Portfolio Risk Card
status: completed
priority: high
date: 2026-09-07
---

## Requirement

Audit and fix the entire data path for the Portfolio Risk Summary card across:
Canonical risk calculation → Backend risk API → Response mapping → Frontend state → Rendering & fallback semantics.

Fix ambiguous labeling (`RỦI RO DANH MỤC (252D)` → `Biến động danh mục (quy đổi năm)`), correlation formatting (correlation is decimal -1..1, not percentage), unavailable data semantics (`null` → `"Chưa đủ dữ liệu"` with clear reasoning instead of bare `'—'`), and missing summary fields (severity, effective positions, largest risk contribution).

## Context

The portfolio-risk summary card previously rendered as:
```
RỦI RO DANH MỤC (252D)
42.8%
Tương quan TB —
```
and the rest of the card was effectively empty.

User issues:
1. "42.8%" was ambiguous: users wondered if it was maximum loss or volatility.
2. "Tương quan TB —" showed a bare dash without explaining why data was unavailable (1 position vs <40 overlapping return days).
3. Formatting bug: `fmtCorr` incorrectly called `pct(value)` on correlation coefficient.
4. Summary card was missing essential context: overall severity, effective positions, largest risk driver, and plain-language interpretation.

## Root Cause Analysis Report

- **Category G (Combination of API contract mapping, formatting bug, ambiguous labeling, and missing fallback semantics)**:
  1. **Formatting Bug**: `fmtCorr` in frontend formatted correlation with `pct()` (46.0%) instead of decimal `num(val, 2)` (0.46).
  2. **Ambiguous Labeling**: Label `RỦI RO DANH MỤC (252D)` led users to confuse annualized volatility (`volatility_252`) with guaranteed loss.
  3. **Bare Em-Dash Fallback**: `average_correlation == null` (returned when `n_positions < 2` or <40 overlapping return days) rendered bare `'—'` without explanation.
  4. **Incomplete Summary Card**: Summary cards on `/risk` and `/allocation` only showed volatility and correlation note, ignoring `overall_severity`, `effective_positions`, `largest_risk_symbol`, and `largest_risk_contribution`.

## Acceptance Criteria

- [x] Rename ambiguous label `RỦI RO DANH MỤC (252D)` to `Biến động danh mục (quy đổi năm)` with clarifying helper note `"Ước tính từ 252 phiên gần nhất, không phải mức lỗ tối đa."`
- [x] Correlation coefficient correctly formatted as decimal between `-1.00` and `+1.00` (e.g. `0.46`), NOT percentage (`46.0%`).
- [x] `average_correlation == null` displays `"Chưa đủ dữ liệu"` with clear reason note (e.g. `"Cần ít nhất 2 cổ phiếu có dữ liệu lịch sử giá"`).
- [x] `UNKNOWN != SAFE` and `UNKNOWN != ZERO`: Missing correlation is NEVER converted or assumed as 0.
- [x] Portfolio risk summary card displays:
  - Annualized volatility: `42.8% / năm`
  - Severity badge: `CẢNH BÁO` / `CẦN CHÚ Ý` / `BÌNH THƯỜNG` / `NGUY CƠ CAO`
  - Tương quan TB: `0.46` (or `"Chưa đủ dữ liệu"`)
  - Vị thế hiệu quả: `2.4`
  - Nguồn rủi ro chính: `DGC · 48.0%`
  - Concise plain-language interpretation.
- [x] Complete data availability states supported: `VALID`, `PARTIAL`, `UNAVAILABLE`.
- [x] Backend API payload contract verified for all summary metrics (`volatility_252`, `average_correlation`, `effective_positions`, `largest_risk_symbol`, `largest_risk_contribution`, `risk_summary`).
- [x] Zero trade recommendations (`BUY`, `SELL`, `REDUCE`, `HOLD`, `BUY_MORE`) on `/risk`.
- [x] Mobile responsive layout verified.
- [x] All unit, contract, architecture, and UI tests pass (`npm run build`).

## Constraints and Invariants

1. `volatility_252` (0.428) MUST format as `42.8% / năm` or `42.8%`.
2. `average_correlation` (0.46) MUST format as decimal `0.46`, NOT `46.0%`.
3. Missing correlation MUST render `"Chưa đủ dữ liệu"`, NEVER `0` or silent `'—'`.
4. `/risk` explains & warns; `/allocation` decides capital actions.
5. No ledger mutation.

## Implementation Tasks

- [x] Audit backend payload keys in `python/portfolio/risk.py`, `risk_warnings.py`, and `service.py`.
- [x] Fix correlation formatter (`fmtCorr`) in `frontend/src/pages/AllocationPage.jsx` and `frontend/src/pages/RiskPage.jsx` to format decimal correlation and handle nulls with explicit `"Chưa đủ dữ liệu"`.
- [x] Update Risk Summary Card in `frontend/src/pages/RiskPage.jsx` and `frontend/src/pages/AllocationPage.jsx` to render complete 4-metric summary + severity pill + plain language note.
- [x] Add unit tests for risk summary data contract, correlation formatting, unavailable data semantics, and unit scaling in `python/portfolio/tests/test_risk_summary_contract.py`.
- [x] Verify unit tests and `npm run build`.

## Related Notes

- [docs/tasks/TASK-20260907-106-add-deterministic-risk-warnings-and-plain-language-risk-interpretation.md](file:///c:/workspace/shannon_allocation/docs/tasks/TASK-20260907-106-add-deterministic-risk-warnings-and-plain-language-risk-interpretation.md)
- [python/portfolio/risk.py](file:///c:/workspace/shannon_allocation/python/portfolio/risk.py)

## Validation Evidence

- Python Risk Test Suite:
  `python -m pytest -o pythonpath=python python/portfolio/tests/test_risk_summary_contract.py python/portfolio/tests/test_risk_warnings.py python/portfolio/tests/test_risk_architecture.py python/portfolio/tests/test_risk_performance_depth_contract.py`
  Output: `24 passed in 0.88s`
- Frontend Build:
  `npm run build`
  Output: `built in 1.28s` with 0 errors.

## Decisions

- **Correlation formatting:** Decimal `num(val, 2)` (e.g. `0.46`), never `pct()` (`46%`).
- **Unavailable fallback:** `"Chưa đủ dữ liệu"` with explanatory note.
- **Card design:** 4 key metrics + severity pill + 1-sentence interpretation.

## Result

- Created `python/portfolio/tests/test_risk_summary_contract.py` to verify backend risk contract and unit formatting.
- Updated `frontend/src/pages/AllocationPage.jsx` to fix correlation formatting and label ambiguity.
- Updated `frontend/src/pages/RiskPage.jsx` and `PortfolioAssessmentEnhancer.jsx` to handle null average correlation with explicit reasons and present complete risk summary cards.
