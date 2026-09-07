# TASK-20260907-109: Audit and Fix Risk Data Integrity and Semantics

---
id: TASK-20260907-109
title: Audit and Fix Risk Data Integrity and Semantics
status: completed
priority: high
date: 2026-09-07
---

## Requirement

Audit and resolve data-integrity and semantic contradictions in `/risk` backend and frontend:
1. Normalize Weight Semantics: Explicitly distinguish `NAV_WEIGHT` (market value / total NAV including cash) from `EQUITY_WEIGHT` (market value / total equity value excluding cash). Label equity-normalized weights clearly as "Tỷ trọng trong phần cổ phiếu". Use `NAV_WEIGHT` as primary weight everywhere to align with `/allocation` and portfolio dashboard.
2. Risk Contribution Coverage Semantics: When coverage is partial, suppress or qualify portfolio-wide risk contribution. Add `risk_eligible_symbols`, `risk_total_symbols`, `risk_eligible_nav_weight`, `risk_coverage_status` (`COMPLETE`, `PARTIAL`, `INSUFFICIENT`).
3. No Fabricated Correlation: If pairwise correlation cannot be computed, return `null`. Remove synthetic default fallbacks (`0.35`). Display "Chưa đủ dữ liệu" in UI.
4. Volatility Summary with Partial Data: If coverage is INSUFFICIENT, report "Chưa đủ dữ liệu để ước tính đáng tin cậy biến động toàn danh mục". Label diagnostic volatility clearly as "Biến động ước tính trên phần danh mục có đủ dữ liệu".
5. Permanent-Loss Evidence Strength: Require explicit canonical evidence for strong conclusions (`CONFIRMED`, `INDICATIVE`, `INSUFFICIENT`). If moat evidence is missing, return `UNKNOWN` ("Chưa đủ bằng chứng đánh giá moat"), NOT `DETERIORATING`.
6. Bank-Specific Logic: Preserve bank-specific risk adapters for ACB/banks; do not apply industrial leverage rules to banks.
7. Permanent-Loss Summary Evidence Display: For each symbol, display compact reason evidence for Quality, Balance Sheet, Moat, Valuation, Thesis.
8. Consistency & Regression Tests: Add comprehensive tests covering weight reconciliation, risk coverage status, correlation nulls, partial coverage warnings, and evidence-backed permanent loss labels.

## Context

Audit revealed semantic/data-integrity contradictions on `/risk`:
- Weights displayed inconsistently (e.g. FPT 52.7% vs 82.41%; DGC 3.1% vs 4.84%) due to mixing NAV weight and equity weight without clear labels.
- Partial history (e.g., 1 of 3 symbols eligible) claiming 100% total portfolio risk contribution for DGC.
- Synthetic default fallback of 0.35 used in frontend matrix for missing pairwise correlation cells.
- Categorical warnings emitted without displaying supporting evidence.

## Acceptance Criteria

- [x] Single canonical weight denominator used consistently across `/risk` (NAV weight). Equity weight labeled explicitly as "Tỷ trọng trong phần cổ phiếu".
- [x] Risk contribution coverage explicitly tracked (`risk_eligible_symbols`, `risk_total_symbols`, `risk_eligible_nav_weight`, `risk_coverage_status`).
- [x] Partial coverage phrasing used for risk contribution ("Trong phần danh mục có đủ dữ liệu...").
- [x] Synthetic `0.35` correlation fallback eliminated from backend and frontend. Missing correlation stays `null` / "Chưa đủ dữ liệu".
- [x] Portfolio volatility summary suppressed or qualified when risk coverage is INSUFFICIENT/PARTIAL.
- [x] Evidence strength (`CONFIRMED`, `INDICATIVE`, `INSUFFICIENT`) introduced for permanent-loss risk dimensions.
- [x] Missing moat evidence returns `UNKNOWN` ("Chưa đủ bằng chứng đánh giá moat"), NOT `DETERIORATING`.
- [x] Permanent loss cards in UI display compact evidence for each fundamental dimension.
- [x] Bank-specific rules preserved for ACB / bank symbols.
- [x] Unit, integration, architecture, and frontend build tests pass.

## Constraints and Invariants

1. Single canonical weight denominator (NAV weight).
2. `UNKNOWN` correlation is `null`, never `0.35` or `0`.
3. `UNKNOWN` moat is `UNKNOWN`, never `DETERIORATING` without multi-period evidence.
4. No ledger mutation.
5. `/risk` remains advisory only; capital actions remain in `/allocation`.

## Implementation Tasks

- [x] Audit weight calculations in `python/portfolio/risk.py`, `python/portfolio/risk_warnings.py`, `python/portfolio/permanent_loss_risk.py`, and `frontend/src/pages/RiskPage.jsx`.
- [x] Update `_pairwise_covariance` and `_correlation_metrics` in `python/portfolio/risk.py` to return `null` for missing correlation cells without synthetic fillna.
- [x] Update `generate_risk_warnings` and `portfolio_risk` to calculate `risk_coverage_status` (`COMPLETE`, `PARTIAL`, `INSUFFICIENT`) and qualify contribution/volatility language.
- [x] Update `python/portfolio/permanent_loss_risk.py` to require explicit evidence for moat, balance sheet, quality, valuation, thesis, and return evidence strength (`CONFIRMED`, `INDICATIVE`, `INSUFFICIENT`).
- [x] Redesign `frontend/src/pages/RiskPage.jsx` to render consistent NAV weights, explicit coverage status banner, null correlation cells as "Chưa đủ dữ liệu", and compact evidence strings for permanent loss dimensions.
- [x] Add unit & integration tests in `python/portfolio/tests/test_risk_data_integrity.py`.
- [x] Verify unit tests and frontend build (`npm run build`).

## Related Notes

- [AGENTS.md](file:///c:/workspace/shannon_allocation/AGENTS.md)
- [BUY_AND_HOLD_SYSTEM_SPEC.md](file:///c:/workspace/shannon_allocation/BUY_AND_HOLD_SYSTEM_SPEC.md)
- [python/portfolio/risk.py](file:///c:/workspace/shannon_allocation/python/portfolio/risk.py)
- [python/portfolio/permanent_loss_risk.py](file:///c:/workspace/shannon_allocation/python/portfolio/permanent_loss_risk.py)
- [frontend/src/pages/RiskPage.jsx](file:///c:/workspace/shannon_allocation/frontend/src/pages/RiskPage.jsx)
- [python/portfolio/tests/test_risk_data_integrity.py](file:///c:/workspace/shannon_allocation/python/portfolio/tests/test_risk_data_integrity.py)

## Validation Evidence

```powershell
# Python unit tests for risk data integrity, warnings, permanent loss, performance depth & summary contracts:
python -m pytest -o pythonpath=python python/portfolio/tests/test_risk_data_integrity.py python/portfolio/tests/test_permanent_loss_risk.py python/portfolio/tests/test_risk_warnings.py python/portfolio/tests/test_risk_architecture.py python/portfolio/tests/test_risk_performance_depth_contract.py python/portfolio/tests/test_risk_summary_contract.py
# Result: 46 passed in 1.00s

# Frontend build verification:
cd frontend && npm run build
# Result: ✓ built in 1.18s (dist/index.html, dist/assets/index--ucowbDC.css, dist/assets/index-Dtw6t-Fh.js)
```

## Decisions

- **NAV Weight as Primary:** Use NAV weight (`market_value / total_nav`) as canonical weight everywhere on `/risk`. Explicitly label `equity_weight` as `Tỷ trọng trong phần cổ phiếu`.
- **Zero Synthetic Fallbacks:** Remove all synthetic default fallbacks (`0.35`) in correlation matrix. Missing correlation must be `null` and rendered as "Chưa đủ dữ liệu".
- **Evidence-Gated Permanent Loss:** Permanent loss labels must be backed by explicit evidence attributes. Missing evidence results in `UNKNOWN` status, never `DETERIORATING`.

## Result

Fully audited and resolved all 10 semantic contradiction areas. Normalized weight semantics to canonical NAV weight, added `risk_coverage_status` gating (`COMPLETE`, `PARTIAL`, `INSUFFICIENT`), removed synthetic `0.35` correlation defaults, added compact evidence display for fundamental dimensions, preserved bank-specific rules for ACB, and created 6 comprehensive regression unit tests in `test_risk_data_integrity.py`. All tests and frontend build passed cleanly.
