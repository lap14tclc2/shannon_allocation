# TASK-20260912-162 — Munger Stock Screening: Liquidity Gate + Full Semantic UI Audit

| Field | Value |
|---|---|
| status | verified |
| created | 2026-09-12 |
| task-id | TASK-20260912-162 |

---

## Requirement

Nâng cấp hệ thống lọc cổ phiếu theo triết lý Buffett–Munger để không chỉ đánh giá chất lượng BCTC và định giá, mà còn kiểm tra khả năng giao dịch thực tế của cổ phiếu (Liquidity Gate). Đồng thời rà soát toàn bộ UI để tuyệt đối không còn enum/internal key/code identifier hiển thị trực tiếp cho người dùng.

## Context

QPort đã có hệ thống lọc cổ phiếu theo Munger 12 chiều chất lượng tài chính, Value Trap forensics, và Canonical Valuation. Thiếu: đánh giá thanh khoản thực tế từ dữ liệu thị trường, và holistic conclusion tổng hợp Quality + MOS + Value Trap + Liquidity.

## Acceptance Criteria

- [x] Liquidity evaluator đọc `qport_finance.market_prices` PostgreSQL
- [x] 4 phân loại thanh khoản: STRONG, ACCEPTABLE, WEAK, INSUFFICIENT_DATA
- [x] Synthesis conclusion tổng hợp Quality + MOS + Value Trap + Liquidity
- [x] Liquidity filter trên BusinessPage candidates
- [x] Liquidity badge + metrics trên candidate cards (BusinessPage, TerminalPage)
- [x] Dedicated Liquidity Detail Card trên Business Detail view (`/business/{symbol}`)
- [x] ScreenerPage đã có liquidity filter (20D turnover filter)
- [x] TerminalPage candidates hiển thị liquidity badge
- [x] 100% Vietnamese semantic trên tất cả user-facing elements
- [x] N/A → "Chưa có" fallback
- [x] Automated tests pass (7/7)
- [x] Frontend build thành công

## Constraints and Invariants

- Liquidity KHÔNG overwrite financial quality (separable criteria)
- Không hard-code kết quả cho bất kỳ ticker nào
- Pure Vietnamese semantics trên tất cả UI elements
- Ưu tiên dữ liệu FY dài hạn, không phụ thuộc quarterly data

## Implementation Tasks

- [x] Create `python/portfolio/value_engine/liquidity_evaluator.py` — Pure deterministic liquidity assessment
- [x] Add `LIQUIDITY_CLASSIFICATION_VI` alias
- [x] Add `synthesize_munger_screening_conclusion_vi()` holistic conclusion
- [x] Update `munger_models.py` — Add `liquidity` field
- [x] Update `munger_analyzer.py` — Integrate liquidity evaluation
- [x] Update `vietnamese_presenter.py` — Add `LIQUIDITY_VIETNAMESE` + `get_vietnamese_liquidity()`
- [x] Update `munger_candidates.py` — Liquidity metrics + synthesis + filtering
- [x] Extract `_evaluate_candidate_symbol()` to top-level for testability
- [x] Update `app/main.py` — Add `liquidity` query parameter
- [x] Update `frontend/src/lib/api.js` — `getMungerCandidates(tier, liquidity, search, limit)`
- [x] Update `frontend/src/utils/vietnameseSemantics.js` — `LIQUIDITY_MAP` + `formatLiquidity()`
- [x] Update `BusinessPage.jsx` — Liquidity filter, candidate badges, detail card
- [x] Update `TerminalPage.jsx` — Candidate liquidity badges
- [x] Fix JSX syntax error (stray closing tags)
- [x] Create `python/portfolio/tests/test_munger_liquidity_gate.py` — 7 tests
- [x] Run pytest — 7/7 passed
- [x] Run frontend build — ✓ built

## Related Notes

- TASK-20260912-148 (Enum Leakage Audit)
- TASK-20260912-155 (Munger Deep Financial Analysis)

## Validation Evidence

```
$ pytest python/portfolio/tests/test_munger_liquidity_gate.py -v
7 passed in 0.71s

$ npm --prefix frontend run build
✓ built in 1.59s
```

## Decisions

1. Liquidity thresholds: STRONG ≥ 10B VND/day or ≥ 500k cp/day (coverage ≥ 85%), ACCEPTABLE ≥ 1B or ≥ 50k cp (coverage ≥ 60%), WEAK < 1B.
2. `_evaluate_candidate_symbol` extracted to module-level for independent testing.
3. Synthesis conclusion is a single Vietnamese sentence combining all 4 axes.

## Result

Hệ thống Munger Stock Screening đã được nâng cấp với Liquidity Gate đầy đủ. Tất cả candidates và detail views hiển thị thông tin thanh khoản thực tế từ dữ liệu thị trường PostgreSQL. UI audit đảm bảo 100% Vietnamese semantics.
