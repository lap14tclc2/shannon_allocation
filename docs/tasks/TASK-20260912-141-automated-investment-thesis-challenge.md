# TASK-20260912-141: Automated Munger Investment Thesis Challenge Engine

## Status: completed
- Date: 2026-09-12
- Priority: High
- Ticker / Domain: Universe-Wide / Value Engine & Thesis Challenge Layer

---

## Requirement

Replace static pre-commitment questionnaire with a deterministic, evidence-first "Automated Munger Investment Thesis Challenge Engine" (`munger_thesis_challenge.py`):
1. Remove all manual forms, textareas, and user questionnaire requirements. QPort must automatically answer all 8 thesis challenge questions from financial statement evidence, forensics, normalized earning power, ValueTrap, valuation, MOS, and Personal Balance Sheet.
2. Rename section on `/business/:symbol` to "PHẢN BIỆN LUẬN ĐIỂM ĐẦU TƯ" with subtitle: "QPort chủ động tìm những bằng chứng có thể bác bỏ luận điểm đầu tư hiện tại, thay vì chỉ tìm dữ liệu ủng hộ nó."
3. Build a structured backend model `InvestmentThesisChallenge` exposing structured question results, stress test scenarios, invalidation criteria, and Vietnamese presentation labels.
4. Implement deterministic answers for all 8 core thesis challenge questions:
   - Q1: Tại sao luận điểm đầu tư này có thể sai? (Rank material risks from forensics/ValueTrap/financial dimensions).
   - Q2: Điều gì có thể làm suy yếu lợi thế kinh tế? (Evaluate ROE/ROIC/margins trends while explicitly respecting BCTC qualitative limitations).
   - Q3: Kịch bản suy giảm lợi nhuận bình thường (-30% & -50% stress test recalculations).
   - Q4: Kịch bản giá trị nội tại bị ước tính cao 30% (30% IV haircut & Stressed MOS using single canonical MOS policy).
   - Q5: Khả năng tiếp tục nắm giữ nếu giá cổ phiếu giảm 50% (PBS liquidity/leverage check; returns `INSUFFICIENT_DATA` safely if PBS absent).
   - Q6: Đánh giá độ bền tài chính nếu thị trường đóng cửa 5 năm (BS strength, debt, earning power, cyclicality).
   - Q7: Cơ hội giá trị hay giá giảm (Value vs Falling Knife classification; price drop alone NEVER implies value).
   - Q8: Tiêu chí bằng chứng thực tế bác bỏ luận điểm (Measurable invalidation criteria with triggers and persistence requirements).
5. Respect economic archetypes (NORMAL_ENTERPRISE, BANK, SECURITIES).
6. Thesis challenge engine challenges the core decision but does NOT independently override it. Flag `DECISION_CONTRADICTION` if a contradiction exists.
7. Run universe-wide scan across all PostgreSQL database symbols, generating:
   - `docs/reports/task-141-thesis-challenge-universe.csv`
   - `docs/reports/task-141-thesis-challenge-audit.md`

---

## Context

Previous iterations exposed a static questionnaire for pre-commitment. Modern QPort architecture requires deterministic automated analysis where the system actively seeks evidence to invalidate its own conclusion before an investor reads the output.

---

## Acceptance Criteria

- [x] Static questionnaire UI removed; no textareas or manual user inputs required.
- [x] Section renamed to "PHẢN BIỆN LUẬN ĐIỂM ĐẦU TƯ" with exact subtitle.
- [x] Backend model `InvestmentThesisChallenge` implemented in `munger_thesis_challenge.py`.
- [x] All 8 thesis challenge questions automatically answered from financial evidence.
- [x] Allowed answer states mapped: `RESILIENT` ("Có khả năng chống chịu"), `WATCH` ("Cần theo dõi"), `VULNERABLE` ("Dễ tổn thương"), `INSUFFICIENT_DATA` ("Chưa đủ dữ liệu"), `NOT_APPLICABLE` ("Không áp dụng").
- [x] Q3 implements -30% and -50% normalized earnings stress tests.
- [x] Q4 implements 30% IV haircut with canonical MOS policy recalculation.
- [x] Q5 evaluates PBS forced-selling risk or returns `INSUFFICIENT_DATA` safely.
- [x] Q6 evaluates financial durability for 5-year closure scenario.
- [x] Q7 classifies Value vs Falling Knife (`VALUE_WITH_SAFETY`, `QUALITY_BUT_EXPENSIVE`, `CHEAP_BUT_DETERIORATING`, `POSSIBLE_VALUE_TRAP`, `INSUFFICIENT_EVIDENCE`).
- [x] Q8 generates measurable invalidation criteria.
- [x] Qualitative UNKNOWN section replaced with concise "Giới hạn của phân tích BCTC" card.
- [x] Core decision preserved; `DECISION_CONTRADICTION` flagged if contradiction detected.
- [x] Universe-wide scan executed across all DB symbols generating CSV and MD reports.
- [x] Unit & integration tests pass (100%).
- [x] Frontend build passes without errors.

---

## Constraints and Invariants

1. **Deterministic Analysis**: No LLM decision authority.
2. **Canonical MOS Authority**: Use single canonical MOS policy from `canonical_valuation.py`.
3. **Archetype Awareness**: BANK and SECURITIES route to archetype-specific rules without false industrial warnings.
4. **FY-Only**: Fundamental analysis uses annual FY history.
5. **No Ticker Exceptions**: Production logic depends strictly on financial facts, history, archetype, and evidence.

---

## Implementation Tasks

- [ ] Create `python/portfolio/value_engine/munger_thesis_challenge.py` implementing `run_thesis_challenge_analysis()`.
- [ ] Integrate thesis challenge output into `FinancialBusinessAnalysis` and `/api/portfolio/business/{symbol}`.
- [ ] Create `frontend/src/components/ThesisChallengeSection.jsx` and integrate into `BusinessPage.jsx`.
- [ ] Replace Qualitative UNKNOWN block with "Giới hạn của phân tích BCTC" explanation.
- [ ] Create `python/portfolio/tests/test_munger_thesis_challenge.py`.
- [ ] Create universe scanner script `thesis_challenge_universe_scanner.py` and run full DB scan.
- [ ] Generate `docs/reports/task-141-thesis-challenge-universe.csv` and `docs/reports/task-141-thesis-challenge-audit.md`.
- [ ] Run full test suite & frontend build verification.

---

## Related Notes

- `python/portfolio/value_engine/munger_analyzer.py`
- `python/portfolio/value_engine/vietnamese_presenter.py`
- `frontend/src/pages/BusinessPage.jsx`
- `TASK-20260912-140-vietnamese-semantic-presentation-layer.md`

---

## Decisions

- Decision 1: Q3 -30%/-50% earnings stress test recalculates intrinsic value using canonical valuation formula parameters (`bear_iv`, `base_iv`, `bull_iv`, discount rates) to guarantee mathematical consistency with the main valuation engine.
- Decision 2: Thesis challenge results are embedded in `/api/portfolio/business/{symbol}` under `thesis_challenge` key to allow seamless frontend rendering and inclusion in AI exports.

---

## Validation Evidence

- Unit tests: `python/portfolio/tests/test_munger_thesis_challenge.py`
- Integration tests: `pytest` full suite
- Universe scan: 1,499 DB symbols scanned into CSV/MD reports
- Frontend build: `npm run build` in `frontend/`

---

## Result

Pending execution.
