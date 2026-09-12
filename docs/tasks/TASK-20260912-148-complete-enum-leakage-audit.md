# TASK-20260912-148: Complete Enum Leakage Audit & Centralized Presentation Layer Upgrade

- **ID**: TASK-20260912-148
- **Title**: Complete Enum Leakage Audit & Centralized Presentation Layer Upgrade
- **Status**: completed
- **Priority**: high
- **Date**: 2026-09-12

---

## Requirement

Rà soát TOÀN BỘ source code dự án QPort để phát hiện mọi internal enum, machine code, status code đang xuất hiện trực tiếp hoặc có nguy cơ fallback thành nhãn thô trên End-User UI.

Mục tiêu cốt lõi:
1. Audit toàn bộ data flow: Backend Enum -> Service -> API Response -> Frontend State -> Component -> Formatter -> Rendered Text.
2. Xây dựng tài liệu kiểm toán Enum đầy đủ tại `docs/reports/enum-ui-leakage-audit.md`.
3. Khắc phục tất cả các vị trí string interpolation thô trong backend (`munger_analyzer.py`, `munger_thesis_challenge.py`, `quality_scorer.py`, `munger_forensics.py`, `munger_archetype_analyzers.py`).
4. Mở rộng lớp centralized presentation mapping (`vietnamese_presenter.py` và `vietnameseSemantics.js`) bao phủ 100% enum values.
5. Cập nhật các UI components (`CapitalPage.jsx`, `BusinessPage.jsx`, `LogsPage.jsx`, `TerminalPage.jsx`) loại bỏ mọi fallback `raw string || 'UNKNOWN'`.
6. Xây dựng automated semantic coverage test (`test_enum_semantic_coverage.py`) và UI raw-enum regression test (`test_ui_raw_enum_regression.py`).
7. Xác minh 100% hiển thị tiếng Việt tự nhiên trên 4 golden symbols **ACB**, **DGC**, **FPT**, **VIX**.

---

## Context

Dự án QPort cần đảm bảo trải nghiệm người dùng cao cấp, tuyệt đối không lộ vết các mã nội bộ (machine codes) như `RECEIVABLES_GROW_FASTER_THAN_REVENUE`, `POSSIBLE_VALUE_TRAP`, `BUILD_RESERVE_FIRST`, `NOT_APPLICABLE`, `UNKNOWN` lên giao diện end-user.

---

## Acceptance Criteria

- [x] Không có bất kỳ machine enum / internal code / raw status nào xuất hiện trên giao diện người dùng.
- [x] Mọi enum value thuộc `DimensionStatus`, `ConfidenceLevel`, `FindingSeverity`, `DeteriorationClassification`, `CompounderClassification`, `QualityTier`, `HardRejectReason`, `Q7Classification` đều có mapping tiếng Việt tự nhiên.
- [x] Không có string interpolation thô dạng `{status}` hay `{q7_class}` trong chuỗi giải thích narrative backend.
- [x] Toàn bộ fallback trên UI đều sử dụng nhãn tiếng Việt chuẩn thay vì chuỗi máy.
- [x] File báo cáo `docs/reports/enum-ui-leakage-audit.md` được tạo đầy đủ bảng phân loại enum inventory.
- [x] Test coverage `test_enum_semantic_coverage.py` và regression `test_ui_raw_enum_regression.py` vượt qua 100%.
- [x] Build frontend `npm run build` thành công 0 lỗi.

---

## Constraints and Invariants

1. Triết lý Buy & Hold (`BUY_AND_HOLD_INFORMATION_SYSTEM`).
2. Ledger Invariant: Biến động giá không thay đổi số lượng cổ phiếu.
3. KHÔNG thay đổi domain logic chỉ để phục vụ UI.
4. KHÔNG dùng fallback kiểu `display || raw_value` nếu `raw_value` có thể chứa enum machine code.
5. Phân tách rõ ràng giữa Domain Model (internal enum) và Presentation Model (semantic-safe representation).

---

## Implementation Tasks

- [x] Task 1: Complete repository audit & write enum inventory report `docs/reports/enum-ui-leakage-audit.md`.
- [x] Task 2: Refactor string interpolations in backend (`munger_analyzer.py`, `munger_thesis_challenge.py`, `quality_scorer.py`, `munger_forensics.py`, `munger_archetype_analyzers.py`).
- [x] Task 3: Expand centralized semantic mappers in `vietnamese_presenter.py` and `vietnameseSemantics.js`.
- [x] Task 4: Fix UI component fallbacks in `CapitalPage.jsx`, `BusinessPage.jsx`, `LogsPage.jsx`, `TerminalPage.jsx`.
- [x] Task 5: Build automated semantic coverage test `python/portfolio/tests/test_enum_semantic_coverage.py`.
- [x] Task 6: Build UI raw-enum regression test `python/portfolio/tests/test_ui_raw_enum_regression.py`.
- [x] Task 7: Run golden symbol audit CLI script and verify output strings.
- [x] Task 8: Run frontend production build `npm run build`.

---

## Related Notes

- [TASK-20260912-147](file:///c:/workspace/shannon_allocation/docs/tasks/TASK-20260912-147-deep-audit-and-fix-na-null-metrics.md)
- [enum-ui-leakage-audit.md](file:///c:/workspace/shannon_allocation/docs/reports/enum-ui-leakage-audit.md)
- [vietnamese_presenter.py](file:///c:/workspace/shannon_allocation/python/portfolio/value_engine/vietnamese_presenter.py)
- [vietnameseSemantics.js](file:///c:/workspace/shannon_allocation/frontend/src/utils/vietnameseSemantics.js)

---

## Validation Evidence

1. Automated Semantic Coverage & UI Regression Test Suite:
```bash
& "$HOME\.venv\Scripts\python.exe" -m pytest python/portfolio/tests/test_enum_semantic_coverage.py python/portfolio/tests/test_ui_raw_enum_regression.py python/portfolio/tests/test_vietnamese_semantics.py python/portfolio/tests/test_munger_financial_analysis.py python/portfolio/tests/test_munger_thesis_challenge.py python/portfolio/tests/test_na_null_metrics_regression.py python/portfolio/tests/test_munger_pipeline_regression.py -o pythonpath=python
# Result: 47 passed in 2.22s
```

2. Golden Symbol Audit Execution:
```bash
& "$HOME\.venv\Scripts\python.exe" python/portfolio/audit_golden_symbols.py
# Result: 4/4 Golden Symbols (ACB, DGC, FPT, VIX) successfully output natural Vietnamese decisions with 0 raw enum leakage.
```

3. Frontend Production Build Verification:
```bash
npm --prefix frontend run build
# Result: Built successfully (vite v6.4.3) with 0 errors.
```

---

## Decisions

- Tách biệt tuyệt đối giữa Internal Domain Code và Investor-Facing Presentation Layer.
- Tự động kiểm tra tính bảo phủ semantic bằng unit test `test_enum_semantic_coverage.py` – bất kỳ enum mới nào được thêm vào domain mà chưa có nhãn tiếng Việt sẽ làm test thất bại ngay lập tức.

---

## Result

Hoàn tất kiểm toán rò rỉ Enum toàn bộ dự án QPort. Toàn bộ mã máy/nội bộ đã được ánh xạ qua lớp Centralized Semantic Mapper (`vietnamese_presenter.py` và `vietnameseSemantics.js`), 100% test bộ lọc và regression UI qua điểm, frontend build sạch sẽ.
