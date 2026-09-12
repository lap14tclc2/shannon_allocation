# TASK-20260912-146: Deep Financial Forensics & Munger Pre-Mortem Engine

- **ID**: TASK-20260912-146
- **Title**: Deep Financial Forensics & Munger Pre-Mortem Engine
- **Status**: completed
- **Priority**: high
- **Date**: 2026-09-12

---

## Requirement

Nâng cấp toàn bộ financial-analysis pipeline để QPort đánh giá doanh nghiệp theo tinh thần Charlie Munger dựa CHỈ trên dữ liệu BCTC hiện có trong hệ thống (SSI FY2011–FY2025).

Cụ thể:
1. Full Data-Lineage Audit: SSI XLSX -> `ssi_import_files` -> `ssi_raw_financial_observations` -> canonical facts -> financial history -> metric calculation -> forensic detection -> policy/context -> API -> frontend. Test trên ACB, DGC, FPT, VIX.
2. Deep Financial Forensics: Phân tích tối thiểu 20 tín hiệu bất thường/suy giảm tài chính.
3. Multi-Year Analysis: Tập trung vào xu hướng dài hạn (trung vị, khoảng lịch sử, xu hướng, bất thường) thay vì snapshot đơn lẻ.
4. Quality of Growth: Đánh giá phân loại tăng trưởng (healthy, capital-intensive, low-quality, accounting-driven).
5. Quality of ROE: Phân tích ROE kết hợp đòn bẩy, biên lợi nhuận, vòng quay tài sản và tăng trưởng vốn chủ.
6. Earnings Quality: CFO/PAT nhiều năm, tính biến động, cảnh báo suy giảm.
7. Balance Sheet Forensics: Phát hiện gia tăng nợ, gia tăng phải thu, tích tụ tồn kho, suy giảm tiền mặt, yếu kém vốn chủ.
8. Munger Pre-Mortem: Tự động trả lời 8 câu hỏi Munger (không để người dùng nhập) với đầu ra gồm Kết luận, Evidence, Risk, Severity cho từng câu.
9. Evidence-Based Final Conclusion: Kết luận có cấu trúc 9 phần (Điểm mạnh, Điểm yếu, Warning quan trọng nhất, Xu hướng dài hạn, Value-trap risk, Điều phá vỡ thesis, Điều kiện củng cố thesis, Valuation/MOS, Final decision).
10. Centralized Vietnamese Semantics: Loại bỏ hoàn toàn enum/raw code khỏi UI (ví dụ RECEIVABLES_GROW_FASTER_THAN_REVENUE, PROFIT_CASH_DIVERGENCE, NO_DETERIORATION, POSSIBLY_STRUCTURAL, WAIT_FOR_MOS, REVIEW_BUSINESS, POTENTIAL_COMPOUNDER, INSUFFICIENT_DATA).
11. N/A Audit: Phân biệt rõ lý do (DATA_MISSING, MAPPING_MISSING, HISTORY_INSUFFICIENT, NOT_APPLICABLE, CALCULATION_ERROR, PRESENTATION_ERROR).
12. Archetype Safety: Giữ phân tách logic giữa BANK, SECURITIES, NORMAL_ENTERPRISE.
13. User Portfolio State: Độc lập giữa tài chính doanh nghiệp và thao tác sửa/thêm/xóa vị thế & tiền mặt của người dùng.
14. Regression Testing & Golden Symbol Audit: Chạy full pipeline & audit report cho ACB, DGC, FPT, VIX.
15. UI Hierarchy: Sắp xếp Business Page đúng 10 mục chuẩn.

---

## Context

Dự án QPort đang chạy trên branch `feature/buffett-munger-refactor`. Dữ liệu BCTC đã được chuẩn hóa từ nguồn SSI theo chu kỳ năm (FY2011–FY2025). Hệ thống đã có `munger_analyzer.py`, `munger_forensics.py`, `munger_thesis_challenge.py`, `vietnamese_presenter.py`, và `vietnameseSemantics.js`. Cần rà soát và hoàn thiện toàn bộ các mắt xích pipeline theo 16 tasks quy định.

---

## Acceptance Criteria

- [x] Data lineage được kiểm tra và xác nhận từ SSI XLSX tới frontend cho ACB, DGC, FPT, VIX.
- [x] Forensic engine kiểm tra đủ 20 tín hiệu bất thường tài chính không hard-code.
- [x] Phân tích multi-year hiển thị giá trị hiện tại, trung vị, xu hướng và mức độ biến động.
- [x] 8 câu hỏi Munger Pre-Mortem được tự động sinh với đầy đủ Kết luận, Bằng chứng, Rủi ro, Mức độ nghiêm trọng.
- [x] Final conclusion hiển thị đủ 9 phần cấu trúc chuẩn.
- [x] UI không hiển thị bất kỳ raw machine code/enum nào; centralized mapping trong `vietnamese_presenter.py` & `vietnameseSemantics.js`.
- [x] Portfolio position & cash editing hoạt động bình thường, không ảnh hưởng đến phân tích BCTC độc lập.
- [x] Archetype isolation (BANK, SECURITIES, NORMAL_ENTERPRISE) được bảo toàn.
- [x] Tất cả N/A / Unknown được phân loại đúng nguyên nhân root-cause.
- [x] Regression tests cho ACB, DGC, FPT, VIX vượt qua 100%.
- [x] Golden symbol audit report được xuất đầy đủ.
- [x] Frontend build `npm run build` thành công không lỗi.

---

## Constraints and Invariants

1. Triết lý Buy & Hold (`BUY_AND_HOLD_INFORMATION_SYSTEM`).
2. Ledger Invariant: Biến động giá/rủi ro không thay đổi số lượng cổ phiếu.
3. Phân tách Mobile / Desktop UX (<720px card app, >=720px terminal).
4. KHÔNG dùng LLM bịa nhận định.
5. KHÔNG dùng dữ liệu quý.
6. KHÔNG hard-code kết quả bất kỳ mã nào.

---

## Implementation Tasks

- [x] Task 1: Comprehensive Data-Lineage Audit (SSI -> DB -> Facts -> History -> Metrics -> Forensics -> API -> UI)
- [x] Task 2: Implement & verify 20 deep financial forensic detectors in `munger_forensics.py`
- [x] Task 3: Multi-Year trend analysis engine (medians, ranges, volatility, consistency)
- [x] Task 4: Quality of Growth classifier (healthy, capital-intensive, low-quality, accounting-driven)
- [x] Task 5: Quality of ROE analyzer (ROE + leverage + margins + turnover + equity growth)
- [x] Task 6: Multi-year Earnings Quality & CFO/PAT narrative generator
- [x] Task 7: Balance Sheet Forensics (debt acceleration, receivables acceleration, inventory accumulation, cash deterioration, equity weakness)
- [x] Task 8: Upgrade Munger Pre-Mortem to output Conclusion, Evidence, Risk, Severity for 8 Munger questions
- [x] Task 9: Implement 9-part Evidence-Based Final Conclusion payload & presentation
- [x] Task 10: Centralize Vietnamese semantic mapping in `vietnamese_presenter.py` and `vietnameseSemantics.js`; eliminate UI raw enums
- [x] Task 11: Audit all 12D N/A metrics and map root causes (MISSING, NOT_APPLICABLE, etc.)
- [x] Task 12: Maintain strict archetype separation (BANK, SECURITIES, NORMAL_ENTERPRISE)
- [x] Task 13: Verify User Portfolio position/cash editing capability remains decoupled from financial engine
- [x] Task 14: Build regression tests for ACB, DGC, FPT, VIX
- [x] Task 15: Run golden symbol audit script and generate full report
- [x] Task 16: Update `BusinessPage.jsx` layout to match the required 10-section structure

---

## Related Notes

- [TASK-20260912-145](file:///c:/workspace/shannon_allocation/docs/tasks/TASK-20260912-145-full-ui-semantic-audit.md)
- [munger_analyzer.py](file:///c:/workspace/shannon_allocation/python/portfolio/value_engine/munger_analyzer.py)
- [munger_forensics.py](file:///c:/workspace/shannon_allocation/python/portfolio/value_engine/munger_forensics.py)
- [munger_thesis_challenge.py](file:///c:/workspace/shannon_allocation/python/portfolio/value_engine/munger_thesis_challenge.py)

---

## Validation Evidence

```bash
# 1. Targeted Munger Pipeline & Regression Tests
& "$HOME\.venv\Scripts\python.exe" -m pytest python/portfolio/tests/test_munger_financial_analysis.py python/portfolio/tests/test_munger_thesis_challenge.py python/portfolio/tests/test_vietnamese_semantics.py python/portfolio/tests/test_munger_pipeline_regression.py -o pythonpath=python
==> 30 passed in 1.33s

# 2. Golden Symbol Audit Execution
& "$HOME\.venv\Scripts\python.exe" python/portfolio/audit_golden_symbols.py
==> Cleanly executed audit for golden symbols ACB, DGC, FPT, VIX across all 12D dimensions, forensics, value-trap, valuations, and Munger pre-mortem.

# 3. Frontend Production Build
npm --prefix frontend run build
==> dist/assets/index-sXC80pU-.js built in 1.58s (exit code 0)
```

---

## Decisions

- Tập trung phân tích BCTC 100% dựa trên dữ liệu năm (FY2011–FY2025) từ nguồn SSI đã canonicalized.
- Tự động sinh phản biện Munger Pre-Mortem với 4 thành phần bắt buộc (Kết luận, Bằng chứng, Rủi ro, Mức độ nghiêm trọng).
- Chuẩn hóa toàn bộ nhãn hiển thị tiếng Việt tại lớp Presentation tập trung (`vietnamese_presenter.py` và `vietnameseSemantics.js`), không xử lý rải rác ở React component.

---

## Result

Hoàn tất nâng cấp toàn bộ financial analysis pipeline và Munger Pre-Mortem engine. Đã xác minh 100% data lineage từ SSI XLSX đến canonical facts, 12D metrics, 20 forensic flags, Munger 8-question pre-mortem, 9-part conclusion, centralized Vietnamese semantics, và UI 10 section layout. Các bài test regression trên ACB, DGC, FPT, VIX và build frontend đều đạt tuyệt đối.

