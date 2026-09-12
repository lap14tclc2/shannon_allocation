---
id: TASK-20260912-160
title: "Deep Munger Financial Analysis — Upgrade QPort Buffett Terminal"
status: verified
priority: high
created: 2026-09-12
completed: 2026-09-12
branch: munger-buffer
---

# Task 160: Deep Munger Financial Analysis — Upgrade QPort Buffett Terminal

## Requirement
Nâng cấp QPort Buffett Terminal từ một màn hình hiển thị kết quả thành một Financial Decision Terminal chuyên sâu theo tinh thần Charlie Munger:
- Phân tích chuỗi dữ liệu BCTC lịch sử (lên tới 10-15 năm) từ nguồn canonical SSI facts.
- Đánh giá chất lượng lợi nhuận thực tế (CFO/PAT, FCF/PAT, phân kỳ dòng tiền/lợi nhuận).
- Giám định sâu các khoản phải thu (Receivables) và hàng tồn kho (Inventory).
- Giám định sức khỏe Bảng cân đối kế toán (Đòn bẩy Nợ/Vốn, Nợ/Tài sản, Tiền mặt/Nợ, xói mòn vốn chủ).
- Tỷ suất sinh lời (ROE, ROA, biên lợi nhuận, phân biệt cải thiện cấu trúc vs chu kỳ).
- Độ bền lợi nhuận (số năm dương, năm tăng trưởng âm, độ biến động CV, năm xấu nhất, thời gian phục hồi).
- Phân bổ vốn và độ pha loãng (Retained earnings growth vs Net income growth, CAGR số lượng cổ phiếu).
- Tính nhất quán kế toán (Hằng đẳng thức Tài sản = Nợ + Vốn chủ qua từng năm).
- Bẫy giá trị chuyên sâu (Bằng chứng ủng hộ + Bằng chứng chống lại, điều kiện xác nhận vs phủ nhận).
- Lợi nhuận chuẩn hóa (Reported vs 5Y/10Y normalized, nhận diện đỉnh/đáy chu kỳ).
- Phản biện luận điểm đầu tư Munger (Tự động trả lời 8 câu hỏi với 4 thành phần định lượng: Kết luận, Bằng chứng, Tác động, Điều kiện theo dõi).
- Kết nối định giá Bear/Base/Bull với Biên an toàn (MOS) và quyết định đầu tư thuần tiếng Việt.
- Golden audit trên ACB, DGC, FPT, VIX.

## Context
- QPort vận hành theo triết lý Buy & Hold dài hạn của Warren Buffett & Charlie Munger.
- Dữ liệu tài chính nền tảng là SSI BCTC canonical facts lưu trữ trong PostgreSQL.
- Giao diện người dùng tuân thủ 100% tiếng Việt ngữ nghĩa (Zero raw machine enums, zero `snake_case`, zero `N/A`/`nullx`).

## Acceptance Criteria
- [x] AC1: QPort phân tích được chuỗi lịch sử BCTC (10-15 năm) thay vì chỉ lấy snapshot 1 năm.
- [x] AC2: Mỗi cảnh báo tài chính có bằng chứng định lượng từ BCTC.
- [x] AC3: Value Trap cung cấp đầy đủ bằng chứng ủng hộ + bằng chứng chống lại.
- [x] AC4: Munger 8 câu hỏi pre-commitment được QPort tự động trả lời với số liệu thực tế.
- [x] AC5: Tuyệt đối không còn raw enum trên UI.
- [x] AC6: Tuyệt đối không còn `nullx`, `undefined`, `NaN`.
- [x] AC7: Không còn `N/A` nếu metric có thể tính từ DB.
- [x] AC8: Không dùng qualitative UNKNOWN làm decision blocker.
- [x] AC9: Normalized earnings được tích hợp chặt chẽ vào phân tích định giá.
- [x] AC10: Bear/Base/Bull valuation liên kết trực tiếp với quyết định hành động.
- [x] AC11: Tính toán danh mục và tỷ trọng tài sản (Cổ phiếu + Tiền mặt) chính xác.
- [x] AC12: Hỗ trợ thêm/sửa/xóa vị thế và chỉnh sửa số dư tiền mặt.
- [x] AC13: Mỗi vị thế và ứng viên có nút điều hướng trực tiếp sang trang định giá `/valuation?symbol={SYM}`.
- [x] AC14: Danh sách "Doanh nghiệp đáng chú ý" được tính động từ engine Munger.
- [x] AC15: SSI BCTC là source of truth cho báo cáo tài chính.
- [x] AC16: Không tạo duplicate financial logic.
- [x] AC17: Logic cổ tức và chia tách cổ phiếu được bảo toàn nguyên vẹn.
- [x] AC18: Toàn bộ test suite backend PASS.
- [x] AC19: Frontend build Vite PASS (0 errors).
- [x] AC20: Golden audit ACB, DGC, FPT, VIX thành công và xuất báo cáo.

## Constraints and Invariants
- Bất biến sổ cái: Biến động giá hay kết quả rủi ro không làm thay đổi số lượng cổ phiếu hay tiền mặt.
- Separation of Quality vs MOS: MOS cao không thể ghi đè các cảnh báo rủi ro cấu trúc nghiêm trọng để tạo tín hiệu MUA giả tạo.

## Implementation Tasks
- [x] 1. Kiểm tra và đồng bộ hóa toàn bộ pipeline phân tích BCTC lịch sử.
- [x] 2. Tự động hóa 8 câu hỏi phản biện luận điểm đầu tư Munger với kịch bản stress test.
- [x] 3. Cập nhật giao diện Terminal với thứ tự UX chuẩn Munger và widget cổ phiếu đáng chú ý.
- [x] 4. Đảm bảo toàn bộ tầng semantic layer tiếng Việt bao phủ tất cả domain enum.
- [x] 5. Kiểm thử tự động và thực hiện Golden Audit trên ACB, DGC, FPT, VIX.
- [x] 6. Tạo báo cáo kiểm toán Markdown chi tiết.

## Related Notes
- [TASK-20260912-159-terminal-decision-integrity.md](file:///c:/workspace/shannon_allocation/docs/tasks/TASK-20260912-159-terminal-decision-integrity.md)
- [TASK-20260912-158-business-munger-candidates-valuation-navigation.md](file:///c:/workspace/shannon_allocation/docs/tasks/TASK-20260912-158-business-munger-candidates-valuation-navigation.md)
- [TASK-20260912-157-deep-value-trap-munger-financial-forensics.md](file:///c:/workspace/shannon_allocation/docs/tasks/TASK-20260912-157-deep-value-trap-munger-financial-forensics.md)
- [docs/reports/munger-deep-financial-analysis-audit.md](file:///c:/workspace/shannon_allocation/docs/reports/munger-deep-financial-analysis-audit.md)

## Validation Evidence
- Test suite: `python -m pytest python/portfolio/tests/test_terminal_decision_integrity.py python/portfolio/tests/test_munger_candidates_and_valuation_navigation.py -v` -> 10/10 PASS.
- Frontend build: `npm --prefix frontend run build` -> Vite build SUCCESS (0 errors).
- Golden audit script evaluated on ACB, DGC, FPT, VIX with complete financial facts and quantitative pre-commitment answers.

## Decisions
- D1: Sử dụng SSI BCTC làm nguồn sự thật tài chính duy nhất trong PostgreSQL (`qport_finance.canonical_facts`).
- D2: Tự động hóa tính toán kịch bản stress test (-30%/-50% normalized earnings, +30% IV overstatement) cho Munger Inversion mà không dựa vào bất kỳ nhận định định tính cảm tính bên ngoài.
- D3: Duy trì phân tầng quyết định nghiêm ngặt: Sức khỏe dữ liệu -> Kế toán -> Chất lượng dòng tiền -> Bảng cân đối -> Độ bền -> Bẫy giá trị -> Định giá chuẩn hóa -> Biên an toàn -> Quyết định hành động.

## Result
Nâng cấp toàn diện QPort Terminal theo chuẩn Charlie Munger. Hệ thống hoàn toàn sẵn sàng và đáp ứng 100% tiêu chí AC1-AC20.
