---
id: TASK-20260828-033
title: Fix bank valuation equity-first model, derive missing PB and ROE, enrich financial analyst narrative, and overhaul valuation card UI
status: completed
priority: high
created: 2026-08-28
updated: 2026-08-28
tags: [valuation, bank-model, pb, roe, financial-analysis, ui-ux, cards]
related: [TASK-20260828-031]
---

## Requirement

1. **Fix Negative Intrinsic Value for Banks / Financial Institutions**:
   - For banks (`entity_type == BANK`), customer deposits (`deposit`) and interbank obligations are raw operating liabilities, not enterprise debt subtracted from operating cash flows. In financial valuation, banks must use an **Equity-First Cash Flow / Dividend Discount / Net Income Model** with `net_debt = 0` (or `Equity Value = PV(Owner Earnings / Net Income to Equity)`), avoiding negative intrinsic value like `-63.471 ₫`.
2. **Missing Multiples (P/B, ROE, BVPS)**:
   - Extract `BS.EQUITY.TOTAL` from BCTC / Balance sheet `equity` or `capital + fund + unDistributedIncome`.
   - Calculate `bvps = equity / shares`, `pb = current_price / bvps`, and `roe = (net_profit / equity) * 100%` when not directly returned by provider ratios.
3. **Professional Financial Analysis Narrative**:
   - Replace generic boilerplate in `assessment.valuation_verdict`, `financial_resilience_diagnosis`, and `earnings_quality_diagnosis` with rich, professional financial analysis tailored to Vietnam equities (explaining intrinsic value vs market price, P/E & P/B multiples in context of ROE, safety margin, and risk invariants).
4. **Card UI/UX Overhaul**:
   - Redesign `ValuationCard` and `ValuationPage`:
     - Clean, equal-height, balanced grid columns (no broken or misaligned columns).
     - Clear visual hierarchy: Ticker header with badge pill, key valuation metrics (Market Price, Intrinsic Value, Margin of Safety badge), Valuation multiples ribbon (P/E, P/B, EPS, ROE).
     - Clean collapsible **"Phân tích & Khuyến nghị từ Chuyên gia"** card section with clear takeaways.
     - Move heavy technical calculation tables (Owner earnings breakdown, EPV math) into a compact, collapsed technical inspection panel for interested users.

## Context

User feedback on ACB:
- P/B and ROE are missing (`—`).
- Intrinsic value is negative (`-63.471 ₫`) due to deducting bank total customer liabilities as enterprise debt.
- Technical math section is overwhelming and redundant for normal investors.
- Need a clear, insightful expert financial explanation based on the company's real figures.
- Current card UI/UX is unaligned, broken, and unattractive.

## Acceptance Criteria

- [ ] Support bank-specific valuation logic in `ValuationEngine` and `finance_catalog`: `entity_type == BANK` uses equity-level cash flow projection (`net_debt = 0`), yielding positive, realistic intrinsic value.
- [ ] Map and extract `BS.EQUITY.TOTAL` from balance sheets to accurately derive `bvps`, `pb`, and `roe`.
- [ ] Enrich `ValueInvestingAssessment` with professional financial commentary explaining valuation status, quality of earnings, balance sheet strength, and fair value range.
- [ ] Redesign `ValuationPage.jsx` and `valuation-page.css` with a modern, beautifully balanced card layout, clear status badges, and collapsible technical math panel.
- [ ] Run test suite (`pytest`) and verify calculations for ACB, FPT, DGC, etc.

## Constraints and Invariants

- Follow `BUY_AND_HOLD_INFORMATION_SYSTEM` invariant: provide objective intrinsic value analysis, margin of safety, and risk factors without generating automated trade orders.
- Maintain deterministic valuation without arbitrary hard-coded stock prices or fake numbers.
- Maintain responsive desktop and mobile UX.

## Implementation Tasks

- [x] Update `finance_catalog.py` to map `BS.EQUITY.TOTAL` (`equity`, `owners_equity`, `von chu so huu`).
- [x] Update `python/portfolio/value_engine/engine.py` to handle `EntityType.BANK` (using equity-first model with `net_debt = 0`).
- [x] Derive `bvps`, `pb`, `roe` deterministically in `engine.py` and `app/main.py`.
- [x] Enhance financial analyst narrative generation in `engine.py` based on ROE, P/E, P/B, and Margin of Safety.
- [x] Redesign `frontend/src/pages/ValuationPage.jsx` and `frontend/src/valuation-page.css`.
- [x] Validate with test scripts and contract tests.

## Decisions

- **Bank Valuation Invariant**: For banks and financial institutions, customer deposits and interbank liabilities are operational operating float (not firm debt deducted from enterprise value). Equity-first DDM/Cash flow models discount directly to Equity Value (`net_debt = 0`), giving mathematically accurate, positive intrinsic value.
- **Derived Multiples**: When upstream provider does not populate separate ratio documents, `BVPS`, `P/B`, and `ROE` are computed from normalized balance sheet equity and net income.
- **Card UI & Information Hierarchy**: High-level investors need concise expert opinion, clear margin of safety, and multiple badges (P/E, P/B, EPS, ROE); in-depth technical mathematics (Owner earnings bridge, DCF scenarios, EPV) is placed into a clean, collapsible inspection drawer.

## Validation Evidence

- Tested valuation calculation for ACB:
  - Thị giá: `22.500 ₫`
  - Giá trị cơ sở (Base IV): `116.159 ₫` (thay vì âm `-63.471 ₫`)
  - Biên an toàn (MoS): `+80.6%` (Deep Value)
  - P/E: `7.4x`, P/B: `1.22x`, EPS: `3.042 ₫`, ROE: `16.5%`
  - Nhận định Chuyên gia: Đầy đủ đánh giá cơ sở định giá, đặc thù mô hình ngân hàng, hiệu suất sinh lời và sức chịu đựng vốn.
- Tested FPT:
  - Thị giá: `120.000 ₫`, Base IV: `69.946 ₫`, MoS: `-71.6%`, P/E: `18.2x`.
- Ran contract test suite:
  - `pytest python/portfolio/tests/test_valuation_page_contract.py python/portfolio/tests/test_value_engine.py python/portfolio/tests/test_dividend_source_and_ui_contract.py`: 15/15 passed.

## Result

- Bank valuation produces accurate equity-level intrinsic value without false negative debt distortion.
- P/B and ROE are fully populated and accurate.
- Card UI/UX is redesigned with balanced 3-box price hero, status pill tags, and clean collapsible technical math drawers.

