# TASK-20260912-142: Vietnamese Financial Semantics Overhaul & Editable Portfolio Positions & Cash

## Status: completed
- Date: 2026-09-12
- Priority: High
- Ticker / Domain: Business Page & Portfolio Management Layer

---

## Requirement

Implement two unified QPort improvements:
1. **Part A - Vietnamese Financial Semantics Overhaul**: Ensure no internal machine terminology (`POTENTIAL_COMPOUNDER`, `NO_DETERIORATION`, `CLEAR`, `HIGH_RISK`, `NORMAL_ENTERPRISE`, `SECURITIES`, `BANK`) leaks into the investor-facing UI. Translate all classifications, ValueTrap, deterioration states, archetypes, dimension statuses, and metrics into natural Vietnamese via centralized presentation helper (`vietnameseSemantics.js` & `vietnamese_presenter.py`), eliminating redundant machine text.
2. **Part B - Editable Portfolio Stock Positions & Cash**: Enable direct addition and editing/correction of stock positions and cash (deposit, withdrawal, balance adjustment) from the portfolio interface. Preserve ledger accounting invariants (transactions as single source of truth, cost basis, TWR/XIRR calculation integrity, multi-portfolio isolation, and immediate state updates).

---

## Context

Previous UI rendered raw internal enums (e.g. `POTENTIAL_COMPOUNDER`, `NO_DETERIORATION`) alongside human labels. Additionally, investors needed a clean, ledger-safe way to add/edit stock positions and deposit/withdraw cash directly in the portfolio UI without bypassing transaction ledger rules.

---

## Acceptance Criteria

- [x] Centralized Vietnamese presentation layer maps all classifications:
  - `COMPOUNDER` → "Doanh nghiệp tích lũy giá trị dài hạn"
  - `POTENTIAL_COMPOUNDER` → "Doanh nghiệp có tiềm năng tăng trưởng giá trị dài hạn"
  - `AVERAGE_BUSINESS` → "Doanh nghiệp có chất lượng trung bình"
  - `CYCLICAL_QUALITY` → "Doanh nghiệp chất lượng mang tính chu kỳ"
  - `WEAK_BUSINESS` → "Chất lượng doanh nghiệp còn yếu"
  - `DETERIORATING_BUSINESS` → "Nền tảng kinh doanh đang suy yếu"
  - `INSUFFICIENT_DATA` → "Chưa đủ dữ liệu để đánh giá"
- [x] ValueTrap states mapped:
  - `CLEAR` → "Chưa phát hiện dấu hiệu bẫy giá trị đáng kể"
  - `WATCH` → "Có dấu hiệu cần theo dõi"
  - `HIGH_RISK` → "Nguy cơ bẫy giá trị cao"
  - `INSUFFICIENT_DATA` → "Chưa đủ dữ liệu để đánh giá"
- [x] Deterioration states mapped:
  - `NO_DETERIORATION` → "Chưa phát hiện xu hướng suy giảm đáng kể"
  - `LIKELY_CYCLICAL` → "Suy giảm có khả năng mang tính chu kỳ"
  - `POSSIBLY_CYCLICAL` → "Có dấu hiệu suy giảm mang tính chu kỳ"
  - `POSSIBLY_STRUCTURAL` → "Có dấu hiệu suy giảm có thể mang tính cấu trúc"
  - `STRUCTURAL` → "Đã phát hiện suy giảm mang tính cấu trúc"
  - `UNKNOWN` → "Chưa đủ dữ liệu để xác định"
- [x] Economic archetypes mapped:
  - `NORMAL_ENTERPRISE` → "Doanh nghiệp sản xuất / thương mại thông thường"
  - `BANK` → "Ngân hàng thương mại"
  - `SECURITIES` → "Công ty chứng khoán"
  - `REAL_ESTATE` → "Bất động sản"
- [x] Dimension status & missing states differentiated: missing data ("Chưa đủ dữ liệu"), not applicable ("Không áp dụng"), not calculated ("Chưa tính được").
- [x] Metric names translated into natural Vietnamese financial terms.
- [x] Redundant machine labels (e.g., repeating CLEAR/NO_DETERIORATION) removed from UI cards.
- [x] Portfolio UI exposes "+ Thêm vị thế", "Chỉnh sửa vị thế", "+ Nạp tiền", "Rút tiền", "Điều chỉnh số dư".
- [x] Portfolio position/cash mutations route strictly through ledger transactions (no direct holdings table mutation).
- [x] Active portfolio isolation enforced; multi-portfolio state updates immediately without full browser reload.
- [x] Validations enforce positive numbers, valid tickers, valid dates, and prevent invalid transactions.
- [x] Backend & frontend tests pass.
- [x] Production build (`npm run build`) passes cleanly.

---

## Constraints and Invariants

1. **Ledger Invariant**: Single source of truth is the transaction ledger. Editing or adding positions/cash creates or corrects transaction events.
2. **Formula Integrity**: Do NOT alter underlying financial valuation or forensic formulas merely to improve display text.
3. **Multi-Portfolio Isolation**: Mutations must be scoped strictly to the selected portfolio ID.

---

## Implementation Tasks

- [x] Expand `python/portfolio/value_engine/vietnamese_presenter.py` and `frontend/src/utils/vietnameseSemantics.js` to cover all classifications, ValueTrap, deterioration, archetypes, and metrics.
- [x] Update `BusinessPage.jsx` and UI components to remove raw internal enums and redundant text.
- [x] Verify portfolio/transaction backend API endpoints (`/api/portfolio/transactions`, `/api/portfolio/cash`, `/api/portfolio/holdings`) for adding/editing positions and cash adjustments.
- [x] Build modal/UI controls in Portfolio/Terminal components for adding/editing positions and managing cash (`PortfolioEditModal.jsx`).
- [x] Add tests in `python/portfolio/tests/test_vietnamese_semantics.py` and `python/portfolio/tests/test_editable_portfolio_and_semantics.py`.
- [x] Run test suite and `npm run build`.

---

## Related Notes

- `python/portfolio/value_engine/vietnamese_presenter.py`
- `frontend/src/utils/vietnameseSemantics.js`
- `frontend/src/pages/BusinessPage.jsx`
- `frontend/src/components/PortfolioEditModal.jsx`
- `TASK-20260912-140-vietnamese-semantic-presentation-layer.md`
- `TASK-20260912-141-automated-investment-thesis-challenge.md`

---

## Decisions

- Decision 1: `formatClassification`, `formatValueTrap`, `formatDeterioration`, and `formatArchetype` in `vietnameseSemantics.js` provide human Vietnamese text as primary labels while hiding raw machine codes in collapsible developer details.
- Decision 2: Adding/editing stock positions or depositing/withdrawing cash creates canonical ledger transactions in `PostgresPortfolioStore` / FastAPI router to maintain cost basis, XIRR, and transaction history consistency.

---

## Validation Evidence

- Unit tests: `python/portfolio/tests/test_vietnamese_semantics.py` and `python/portfolio/tests/test_editable_portfolio_and_semantics.py` (33 + 11 = 44 tests passed in 1.45s and 6.78s).
- Real runtime validation: `scratch/verify_task142_runtime.py` verified FPT, DGC, ACB, VIX semantics and isolated portfolio deposit, stock addition, position edit, and cash withdrawal mutations.
- Frontend build: `npm run build` in `frontend/` passed in 1.35s with 0 errors.

---

## Result

Task completed successfully. All acceptance criteria satisfied.
