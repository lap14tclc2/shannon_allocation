---
id: TASK-20260917-172
title: Refine Munger forensic semantics, decision trace, and compounder classification after HAH/BFC regression
status: completed
priority: high
date: 2026-09-17
---

# TASK-20260917-172: Refine Munger Forensic Semantics, Decision Trace, and Compounder Classification

## Requirement
Sau đợt kiểm thử hồi quy trên các mã HAH và BFC, cần tinh chỉnh 3 thành phần cốt lõi trong Munger Value Engine (không hard-code mã cổ phiếu cụ thể, áp dụng cho toàn bộ engine tổng quát):
1. **Tách bạch Vốn lưu động (Phải thu vs Hàng tồn kho vs Nợ nhà cung cấp vs Tổng hợp)**: Không dùng mã lỗi/cảnh báo gộp kiểu `WORKING_CAPITAL_DIVERGENCE` hay kết luận "Khoản phải thu / Tồn kho tăng nhanh hơn doanh thu" khi một trong hai yếu tố hoàn toàn bình thường (ví dụ: BFC phải thu tăng chậm hơn doanh thu nhưng tồn kho tăng nhanh hơn doanh thu). Phải có forensic assessment riêng cho Phải thu, Tồn kho, và Tổng hợp vốn lưu động.
2. **Minh bạch hóa Decision Trace cho việc WATCH cùng tồn tại với BUY / CONDITIONAL_BUY**: Giải thích rõ ràng tại sao các phát hiện WATCH (rủi ro phi cấu trúc, áp lực vốn lưu động tạm thời, biến động chu kỳ) không chặn quyết định Mua khi Biên an toàn thực tế đã bù đắp phần phụ phí rủi ro (MOS Addon) và nền tảng tài chính an toàn.
3. **Thắt chặt chuẩn phân loại COMPOUNDER**: Tránh gán nhãn `COMPOUNDER` quá lỏng lẻo cho các doanh nghiệp chỉ có tăng trưởng/ROE cao trong giai đoạn đỉnh chu kỳ lịch sử. Phân định rõ ràng giữa `COMPOUNDER` (tích lũy giá trị bền vững dài hạn: ROE cao ổn định, biến động lợi nhuận thấp, chuyển hóa tiền mặt tốt, bảng cân đối vững) với `CYCLICAL_QUALITY` (chất lượng theo chu kỳ), `POTENTIAL_COMPOUNDER` (tiềm năng), và `AVERAGE_BUSINESS`.

## Context
- Đợt cải tiến trước đã giải quyết các bất đồng bộ về logic phải thu, CFO/PAT, thanh khoản và thẩm quyền quyết định duy nhất.
- Kiểm thử thực tế trên BFC cho thấy:
  - BFC có tốc độ tăng khoản phải thu chậm hơn doanh thu, nhưng tồn kho tăng nhanh hơn doanh thu. Hệ thống trước đó đưa ra `WORKING_CAPITAL_DIVERGENCE` với tiêu đề gộp gây hiểu lầm rằng cả phải thu và tồn kho đều có vấn đề.
  - Khi có cảnh báo WATCH, nhà đầu tư cần biết cơ sở định lượng tại sao khuyến nghị vẫn là BUY / CONDITIONAL_BUY mà không bị mâu thuẫn logic.
  - BFC có tính chu kỳ phân bón/nông nghiệp và biến động lợi nhuận đáng kể, nên xếp vào `CYCLICAL_QUALITY` hoặc `POTENTIAL_COMPOUNDER` thay vì gán nhãn `COMPOUNDER` thuần túy.

## Acceptance Criteria
- [x] **Part 1 — Tách biệt Phải thu & Tồn kho**:
  - `value_trap.py`: Tách `evidence_matrix` thành các mục rủi ro độc lập: `RECEIVABLES_DIVERGENCE` (chỉ khi phải thu tăng nhanh hơn doanh thu) và `INVENTORY_DIVERGENCE` (chỉ khi tồn kho tích tụ nhanh hơn doanh thu).
  - Scorecard & Top risks: Chỉ ra chính xác cấu phần gây áp lực vốn lưu động; mục tổng hợp (`WORKING_CAPITAL`) chỉ đóng vai trò tóm tắt và nêu rõ cấu phần phân kỳ.
  - `munger_forensics.py`: Đảm bảo các finding codes và giải thích phản ánh đúng từng cấu phần riêng lẻ.
- [x] **Part 2 — Minh bạch Decision Trace (WATCH coexistence with BUY)**:
  - Bổ sung trường `watch_coexistence_rationale` / giải thích trong `decision_trace` và `long_term_decision` làm rõ: Các cảnh báo WATCH là rủi ro phi cấu trúc, được lượng hóa qua phụ phí Biên an toàn yêu cầu (`required_mos_pct`) và được kiểm soát bởi các yếu tố an toàn khác (tiền mặt, ROE), nên cùng tồn tại hợp lệ với BUY / CONDITIONAL_BUY.
- [x] **Part 3 — Thắt chặt Compounder Classification**:
  - `munger_analyzer.py`: Điều kiện `COMPOUNDER` đòi hỏi: (1) Lịch sử dữ liệu đủ dài (>= 5 năm), (2) ROE trung vị vững chắc (>= 15%), (3) Biến động lợi nhuận thấp/vừa phải (`pat_volatility < 0.35`), (4) Dòng tiền kinh doanh lành mạnh (`cfo_pat` median >= 0.70 hoặc chất lượng dòng tiền không FAIL), (5) Phân bổ vốn và nợ an toàn, không có suy giảm cấu trúc.
  - Doanh nghiệp có ROE/tăng trưởng cao nhưng biến động chu kỳ (`pat_volatility >= 0.35` hoặc biên độ chu kỳ cao) được phân loại chính xác thành `CYCLICAL_QUALITY`.
  - Các doanh nghiệp chưa đủ dữ liệu sâu hoặc chất lượng tiềm năng xếp vào `POTENTIAL_COMPOUNDER`.
- [x] **Part 4 — Semantics & Frontend Alignment**:
  - Cập nhật từ điển nhãn và semantics (`vietnamese_presenter.py`, `vietnameseSemantics.js`).
- [x] **Part 5 — Verification**:
  - Chạy toàn bộ test suites liên quan (decision integrity, value trap, munger engine) và `npm run build` không có lỗi.

## Constraints and Invariants
- Không hard-code ticker HAH, BFC hay bất kỳ mã cụ thể nào trong core engine.
- Tuân thủ bất biến `BUY_AND_HOLD_INFORMATION_SYSTEM`.
- Đảm bảo tính tất định (deterministic) 100% không phụ thuộc random hay state bên ngoài.

## Implementation Tasks
- [x] Cập nhật `python/portfolio/value_engine/value_trap.py`:
  - Tách logic phát hiện và tạo evidence matrix riêng cho Phải thu (`RECEIVABLES_DIVERGENCE`) và Tồn kho (`INVENTORY_DIVERGENCE`).
  - Sửa `wc_drag_cause` để mô tả chính xác cấu phần đơn lẻ hoặc kết hợp.
  - Khắc phục enum leaks trong `critical_missing` map sang tiếng Việt.
- [x] Cập nhật `python/portfolio/value_engine/munger_forensics.py`:
  - Rà soát các finding code và giải thích về khoản phải thu và tồn kho.
- [x] Cập nhật `python/portfolio/value_engine/munger_analyzer.py`:
  - Nâng cấp bộ lọc `compounder_class`: đưa thêm tiêu chí độ sâu lịch sử, biến động lợi nhuận, dòng tiền CFO/PAT và hiệu quả vốn vào điều kiện để trở thành `COMPOUNDER`.
  - Thêm `watch_coexistence_rationale` vào `decision_trace` và `long_term_decision`.
- [x] Cập nhật từ điển và frontend presentation (`vietnamese_presenter.py`, `vietnameseSemantics.js`).
- [x] Viết unit tests kiểm tra tính tách bạch của Working Capital, phân loại Compounder vs Cyclical Quality, và Decision trace (`test_munger_working_capital_refinement.py`).
- [x] Chạy kiểm thử pytest (34 passed) và frontend build (`npm run build`).

## Related Notes
- [TASK-20260916-170](file:///c:/workspace/shannon_allocation/docs/tasks/TASK-20260916-170-munger-decision-forensic-consistency.md)
- [TASK-20260917-171](file:///c:/workspace/shannon_allocation/docs/tasks/TASK-20260917-171-fix-aiexport-formatdecision-undefined.md)
- [munger_analyzer.py](file:///c:/workspace/shannon_allocation/python/portfolio/value_engine/munger_analyzer.py)
- [value_trap.py](file:///c:/workspace/shannon_allocation/python/portfolio/value_engine/value_trap.py)
- [munger_forensics.py](file:///c:/workspace/shannon_allocation/python/portfolio/value_engine/munger_forensics.py)

## Validation Evidence
- `pytest python/portfolio/tests/test_munger_decision_forensic_consistency.py python/portfolio/tests/test_deep_value_trap_forensics.py python/portfolio/tests/test_deep_munger_decision_engine.py python/portfolio/tests/test_value_engine.py python/portfolio/tests/test_munger_working_capital_refinement.py`: **34 passed, 1 skipped in 1.00s**.
- `npm run build`: built in 3.45s cleanly with exit code 0.

## Decisions
- Tách biệt hoàn toàn `RECEIVABLES_DIVERGENCE` và `INVENTORY_DIVERGENCE` trong evidence matrix và top risks.
- Giữ `WORKING_CAPITAL` làm scorecard category tổng hợp cấp cao, nhưng evidence chi tiết phân lập theo từng khoản mục.
- Đưa ngưỡng biến động lợi nhuận (`pat_volatility < 0.35`), độ sâu lịch sử (>= 5 năm), và dòng tiền kinh doanh (CFO/PAT >= 0.70) vào tiêu chuẩn `COMPOUNDER`, phân loại chính xác các mã chu kỳ sang `CYCLICAL_QUALITY`.

## Result
Đã hoàn tất tinh chỉnh 3 thành phần cốt lõi của Munger Engine:
1. Phân lập hoàn toàn forensic cho Phải thu và Hàng tồn kho; không còn kết luận gộp gây hiểu lầm.
2. Cung cấp trường `watch_coexistence_rationale` tường minh lý giải sự cùng tồn tại của cảnh báo WATCH và quyết định BUY / CONDITIONAL_BUY.
3. Thắt chặt bộ tiêu chuẩn phân loại `COMPOUNDER`, tách biệt chính xác giữa Doanh nghiệp tích lũy giá trị bền vững và Doanh nghiệp chất lượng mang tính chu kỳ (`CYCLICAL_QUALITY`).

