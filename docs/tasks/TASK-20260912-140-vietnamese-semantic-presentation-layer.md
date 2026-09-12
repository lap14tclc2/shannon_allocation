# TASK-20260912-140: Vietnamese Semantic Presentation Layer

## Status: completed
- Date: 2026-09-12
- Priority: High
- Ticker / Domain: Universe-Wide / Value Engine & Presentation Layer

---

## Requirement

Separate machine calculation semantics from investor-facing Vietnamese explanations across QPort:
1. Retain mathematical precision, raw values, formulas, thresholds, comparison operators, and calculation evidence for audit/tests/debugging.
2. Build a centralized Vietnamese Presentation Layer (`vietnamese_presenter.py` & `vietnameseSemantics.js`) so the investor-facing UI never exposes raw programming operators (`>=`, `<`, `ratio_cagr_diff`) as primary text.
3. Map internal statuses, decisions, comparison findings, and system invariants (`NULL != 0`, `UNKNOWN != PASS`, `WATCH != FAIL`, `NOT_APPLICABLE != UNKNOWN`) to clear investor-focused Vietnamese financial language.
4. Each financial finding must expose answers to 6 core investor questions:
   - Điều gì đang xảy ra?
   - Xu hướng kéo dài bao lâu?
   - Vì sao điều đó quan trọng?
   - Mức độ nghiêm trọng?
   - Dữ liệu nào chứng minh?
   - Điều này ảnh hưởng thế nào đến đánh giá dài hạn?

---

## Context

Task 139 established universe-wide forensic correctness and single canonical MOS authority.
However, financial findings and decisions in API payloads and UI views currently display raw code keys (`RECEIVABLES_GROW_FASTER_THAN_REVENUE`, `receivables_cagr > revenue_cagr`, `WAIT_FOR_MOS`) or technical comparison strings directly to users.
Investors require clean financial Vietnamese explanations ("Khoản phải thu tăng nhanh hơn doanh thu", "Chờ mức giá có biên an toàn tốt hơn") while preserving raw math expressions in audit drill-downs.

---

## Acceptance Criteria

- [x] Centralized Vietnamese presenter module created in backend (`vietnamese_presenter.py`) and frontend (`vietnameseSemantics.js`).
- [x] All internal statuses translated:
  - `PASS` → "Đạt" / "Tốt"
  - `WATCH` → "Cần theo dõi"
  - `FAIL` → "Không đạt"
  - `UNKNOWN` → "Chưa đủ dữ liệu"
  - `NOT_APPLICABLE` → "Không áp dụng"
  - `CLEAR` → "Chưa phát hiện rủi ro đáng kể"
  - `HIGH_RISK` → "Rủi ro cao"
- [x] All internal investment decisions translated:
  - `BUY` → "Có thể mua"
  - `BUY_MORE` → "Có thể mua thêm"
  - `HOLD` → "Tiếp tục nắm giữ"
  - `HOLD_NO_NEW_CAPITAL` → "Tiếp tục nắm giữ, chưa phân bổ thêm vốn"
  - `WAIT_FOR_MOS` → "Chờ mức giá có biên an toàn tốt hơn"
  - `BUILD_RESERVE_FIRST` → "Ưu tiên củng cố quỹ dự phòng trước"
  - `REVIEW_BUSINESS` → "Cần xem xét thêm dữ liệu doanh nghiệp"
  - `AVOID` → "Chưa phù hợp để đầu tư"
  - `SELL_REVIEW` → "Cần xem xét lại luận điểm nắm giữ"
  - `SELL` → "Cân nhắc thoái vốn"
- [x] Financial findings structured with 6 investor-focused Vietnamese narrative components while maintaining raw mathematical evidence.
- [x] System semantic invariants clearly documented and exposed in investor UI semantics (`NULL != 0`, `UNKNOWN != PASS`, `WATCH != FAIL`, `NOT_APPLICABLE != UNKNOWN`).
- [x] Frontend UI components updated to consume centralized presenter.
- [x] Unit & integration tests created and passed.
- [x] Frontend build passes without errors.

---

## Constraints and Invariants

1. **Precision Invariant**: Engine calculations, thresholds, comparison operators, and raw numbers MUST NOT be removed or altered.
2. **Centralization Invariant**: Do NOT scatter inline Vietnamese translation dicts across individual React components. Use the centralized presentation helper module.
3. **Audit Invariant**: Raw mathematical formulas and calculation evidence must remain accessible in expandable technical details/export formats.

---

## Implementation Tasks

- [x] Create `python/portfolio/value_engine/vietnamese_presenter.py` with finding and decision translation dictionaries and 6-answer narrative generator.
- [x] Update Munger models & API endpoints (`munger_models.py`, `munger_analyzer.py`, `munger_forensics.py`) to expose structured presentation dictionaries.
- [x] Create `frontend/src/utils/vietnameseSemantics.js` providing centralized status, decision, and finding explanation formatters.
- [x] Update `BusinessPage.jsx` and related UI views to display natural investor Vietnamese narrative first, numbers second, and formulas in audit drill-downs.
- [x] Add tests in `python/portfolio/tests/test_vietnamese_semantics.py`.
- [x] Run full test suite & frontend build verification.

---

## Related Notes

- `python/portfolio/value_engine/munger_analyzer.py`
- `python/portfolio/value_engine/munger_forensics.py`
- `frontend/src/pages/BusinessPage.jsx`
- `TASK-20260912-139-forensic-correctness-and-canonical-mos-authority.md`

---

## Decisions

- Decision 1: Backend exposes `presentation` sub-object in `StructuredFinding` alongside raw `comparison` and `evidence` to allow zero-delay frontend rendering and consistent AI export text.
- Decision 2: Centralized `vietnameseSemantics.js` fallback handles any newly introduced finding code by converting snake_case/UPPERCASE codes into humanized titles if an explicit translation is missing.

---

## Validation Evidence

- Unit tests: `python/portfolio/tests/test_vietnamese_semantics.py` (6/6 passed)
- Integration tests: `pytest` suite 49/49 passed
- Frontend build: `npm run build` in `frontend/` (0 errors, built in 1.39s)

---

## Result

Pending execution.
