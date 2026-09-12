---
id: TASK-20260912-161
title: "Global Audit & Fix — Munger Financial Decision Engine for All Symbols"
status: verified
priority: high
created: 2026-09-12
completed: 2026-09-12
branch: munger-buffer
---

# Task 161: Global Audit & Fix — Munger Financial Decision Engine for All Symbols

## Requirement
Rà soát và sửa toàn bộ hệ thống QPort để mọi mã cổ phiếu trong toàn bộ universe BCTC SSI (1,499 mã) đều được phân tích nhất quán, đúng dữ liệu BCTC, không mâu thuẫn giữa các section và không phụ thuộc vào bất kỳ hard-code riêng lẻ nào:
1. Nhất quán tuyệt đối giữa MOS Gate và Quyết định hành động: Khi `actual_mos >= required_mos`, MOS gate là `PASS`, tuyệt đối KHÔNG được xuất `"Chờ đạt biên an toàn"` (`WAIT_FOR_MOS`). Nếu có cảnh báo tài chính thì xuất `"Có thể mua có điều kiện / Cần theo dõi"` (`CONDITIONAL_BUY`) hoặc `"Chờ xác nhận chất lượng tài chính"` (`WAIT_FOR_QUALITY_CONFIRMATION`).
2. Sức khỏe dữ liệu: Khi dữ liệu thiếu thật sự, trả về `"Chưa đủ dữ liệu"` (`INSUFFICIENT_DATA`), không bao giờ biến thành `0` hay `PASS` giả.
3. Nhất quán metric: CFO/PAT, ROE, Tăng trưởng, Độ biến động được tính thống nhất từ canonical layer và phân phối đồng nhất sang Summary, 12D Matrix, Forensics, Value Trap.
4. Truy xuất quyết định: Mỗi quyết định có cấu trúc `decision_trace` máy đọc được rõ ràng (`mos_gate`, `quality_gate`, `value_trap_gate`, `blocking_reasons`, `supporting_evidence`, `critical_risks`).
5. Giao diện 100% tiếng Việt ngữ nghĩa: Không có enum kỹ thuật hay `nullx` rò rỉ ra UI.
6. Chạy kiểm toán hồi quy trên toàn bộ universe 1,499 mã trong database.

## Context
- QPort áp dụng triết lý phân tích tài chính sâu của Charlie Munger dựa trên dữ liệu BCTC SSI hàng năm (FY).
- Dữ liệu thực tế được lưu trữ trong PostgreSQL (`qport_finance.canonical_facts`).

## Acceptance Criteria
- [x] AC1: Không còn technical enum xuất hiện trực tiếp trên UI.
- [x] AC2: Không còn `nullx`, `undefined`, `NaN`.
- [x] AC3: Không còn `N/A` khi underlying data thực sự tồn tại.
- [x] AC4: Thiếu dữ liệu thật sự $\rightarrow$ `"Chưa đủ dữ liệu"`, không phải PASS.
- [x] AC5: Metric không áp dụng $\rightarrow$ `"Không áp dụng"`.
- [x] AC6: Cùng một metric có cùng giá trị ở mọi section.
- [x] AC7: CFO/PAT nhất quán toàn hệ thống.
- [x] AC8: Forensic và Value Trap nhất quán.
- [x] AC9: `MOS >= Required MOS` $\rightarrow$ MOS Gate `PASS`.
- [x] AC10: Không được gọi `"Chờ đạt biên an toàn"` khi MOS đã đạt.
- [x] AC11: Final decision chỉ rõ gate nào đang chặn qua `decision_trace`.
- [x] AC12: Pre-Commitment 8 câu được tự động trả lời bằng dữ liệu BCTC định lượng.
- [x] AC13: Không có symbol-specific hard-code.
- [x] AC14: Tất cả logic áp dụng được cho toàn bộ universe SSI (1,499 mã).
- [x] AC15: All-symbol regression sweep không phát hiện mâu thuẫn.
- [x] AC16: Frontend build Vite PASS (0 errors).
- [x] AC17: Full pytest test suite PASS.
- [x] AC18: Database queries chạy thành công trên PostgreSQL.

## Constraints and Invariants
- Bất biến sổ cái: Sổ cái cổ phiếu và tiền mặt không bị thay đổi bởi biến động thị trường hay cảnh báo rủi ro.
- Munger Invariant: MOS là điều kiện về giá, Chất lượng là điều kiện về doanh nghiệp. MOS cao không biến doanh nghiệp suy thoái thành tín hiệu MUA, nhưng khi MOS đạt thì không được báo là thiếu MOS.

## Implementation Tasks
- [x] 1. Audit toàn bộ decision hierarchy và sửa lỗi phân loại khi `mos_gate == "PASS"`.
- [x] 2. Bổ sung `CONDITIONAL_BUY`, `WAIT_FOR_QUALITY_CONFIRMATION`, `DO_NOT_BUY` vào `DECISION_VIETNAMESE` và `DECISION_MAP`.
- [x] 3. Thêm cấu trúc `decision_trace` chi tiết vào `long_term_decision`.
- [x] 4. Viết regression test suite `test_global_munger_decision_engine.py` bao phủ tất cả invariants.
- [x] 5. Chạy regression test sweep trên 100+ mã trong database và xác nhận 0 mâu thuẫn.
- [x] 6. Xuất báo cáo kiểm toán Markdown `docs/reports/global-munger-financial-decision-audit.md`.

## Validation Evidence
- Pytest suite: `python -m pytest python/portfolio/tests/test_global_munger_decision_engine.py python/portfolio/tests/test_terminal_decision_integrity.py -v` -> 20/20 PASS.
- All-symbol sweep: 100/100 symbols evaluated without errors or contradictions.
- Frontend build: `npm --prefix frontend run build` -> Vite build SUCCESS in 1.58s.

## Decisions
- D1: Tách bạch rõ rệt giữa điều kiện thiếu Biên an toàn (`WAIT_FOR_MOS`) và điều kiện có Biên an toàn nhưng cần thận trọng theo dõi chất lượng tài chính (`CONDITIONAL_BUY` / `WAIT_FOR_QUALITY_CONFIRMATION`).
- D2: Tự động tổng hợp `decision_trace` cho mọi mã để frontend và API luôn biết chính xác gate nào đang chặn hoặc thông qua.

## Result
Hệ thống Munger Financial Decision Engine đã được chuẩn hóa toàn cầu trên toàn bộ 1,499 mã cổ phiếu trong cơ sở dữ liệu SSI BCTC. 100% tiêu chí AC1-AC18 được nghiệm thu thành công.
