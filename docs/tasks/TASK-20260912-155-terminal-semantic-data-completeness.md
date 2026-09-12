# TASK-20260912-155: Terminal Semantic + Portfolio Data Completeness Audit

- **ID**: TASK-20260912-155
- **Title**: Terminal Semantic + Portfolio Data Completeness Audit
- **Status**: completed
- **Priority**: high
- **Date**: 2026-09-12

---

## Requirement

1. Audit toàn bộ flow Terminal: Portfolio positions, cash balance, valuation integration, decision matrix, and Munger analysis summary.
2. Xử lý triệt để vấn đề "Chưa có giá TT": Đảm bảo Terminal lấy giá thị trường cho tất cả các mã có trong DB/provider (ACB, DGC, FPT, VIX, etc.).
3. Xử lý logic tính tổng danh mục khi có vị thế thiếu giá: Tuyệt đối không coi giá trị thị trường = 0 một cách im lặng. Tách rõ phần đã định giá vs chưa định giá và cảnh báo trạng thái dữ liệu.
4. Rà soát và loại bỏ 100% enum machine-readable trên toàn bộ giao diện Terminal và components liên quan (`HIGH_QUALITY`, `INVESTABLE`, `EXCEPTIONAL`, `REVIEW_BUSINESS`, `WATCH`, `CLEAR`, `INSUFFICIENT_DATA`, `NO_DETERIORATION`, `POSSIBLY_STRUCTURAL`, `BUSINESS_REVIEW_INCOMPLETE`, `POTENTIAL_COMPOUNDER`, `PROFIT_CASH_DIVERGENCE`, `RECEIVABLES_GROW_FASTER_THAN_REVENUE`, `PRIMARY_SSI`, `DERIVED`, `PASS`, `FAIL`, `UNKNOWN`, `N/A`, `nullx`, `NOT_APPLICABLE`, `UNPROTECTED`, `WAIT_FOR_MOS`, etc.).
5. Chuyển đổi toàn bộ forensic flags và warnings thành giải thích tiếng Việt tự nhiên, có cấu trúc (giai đoạn, lý do, tác động dài hạn, số liệu chứng minh).
6. Phân biệt rõ 4 trường hợp dữ liệu thiếu: "Không áp dụng", "Chưa đủ dữ liệu", "Chưa lấy được dữ liệu", "Chưa thể tính" (tuyệt đối không render "nullx", "undefined", "NaN").
7. Hiển thị thông tin Cash, Tổng tài sản danh mục (Cổ phiếu + Tiền mặt), Vốn đầu tư, Lãi/lỗ, Tỷ suất danh mục, Data Freshness & Source (e.g. "Nguồn BCTC: SSI").
8. Tạo báo cáo chi tiết `docs/reports/terminal-semantic-data-audit.md`.

## Context

- Terminal backend API: `portfolio/storage.py`, `portfolio/service.py`, `portfolio/correctable_service.py`, `portfolio/canonical_valuation.py`.
- Terminal frontend UI: `frontend/src/pages/TerminalPage.jsx`, `frontend/src/utils/vietnameseSemantics.js`.

## Acceptance Criteria

- [x] AC1: Không còn bất kỳ enum machine-readable nào trên giao diện Terminal.
- [x] AC2: Không còn "N/A", "null", "undefined", "NaN", "nullx" trên Terminal.
- [x] AC3: Toàn bộ forensic warnings hiển thị tiếng Việt tự nhiên và có giải thích.
- [x] AC4: Giá thị trường được load đầy đủ cho các mã có dữ liệu (ACB, DGC, FPT, VIX, etc.).
- [x] AC5: Khi có vị thế thiếu giá thị trường, tổng danh mục không coi giá trị = 0 im lặng mà hiển thị trạng thái riêng.
- [x] AC6: Tiền mặt và tổng tài sản danh mục (Cổ phiếu + Tiền mặt) hiển thị chuẩn xác.
- [x] AC7: Ma trận quyết định và Value Trap hoàn toàn bằng tiếng Việt chuẩn ngữ nghĩa Munger.
- [x] AC8: Thông tin Data Freshness và Nguồn BCTC hiển thị rõ ràng (e.g. "Nguồn BCTC: SSI").
- [x] AC9: Tạo báo cáo `docs/reports/terminal-semantic-data-audit.md`.
- [x] AC10: Tất cả regression tests pass (25/25 tests), frontend build pass.

## Constraints and Invariants

1. Không thay đổi logic định giá tài chính cốt lõi hoặc canonical facts DB.
2. Không render raw enum hay technical fallback `enum.replace("_", " ")`.
3. Giữ nguyên nguyên lý Buy & Hold và Ledger Invariants.

## Implementation Tasks

- [x] Task 1: Audit & fix Backend Market Price Provider & Portfolio summary calculations (`portfolio/storage.py`, `portfolio/correctable_service.py`).
- [x] Task 2: Audit & expand Vietnamese Semantic Mapping layer (`frontend/src/utils/vietnameseSemantics.js`).
- [x] Task 3: Audit & refactor Terminal UI components (`frontend/src/pages/TerminalPage.jsx`, Position Table, Decision Matrix, Detail Drawer, Summary Cards).
- [x] Task 4: Fix null / nullx / undefined / N/A rendering across Terminal UI.
- [x] Task 5: Viết tests kiểm thử frontend semantics, backend portfolio calculations, và zero enum leakage (`test_terminal_semantic_completeness.py`, `test_terminal_portfolio_positions.py`).
- [x] Task 6: Viết báo cáo `docs/reports/terminal-semantic-data-audit.md`.
- [x] Task 7: Chạy kiểm thử, build frontend, cập nhật task note sang `completed`, commit và push.

## Related Notes

- [TASK-20260912-148-complete-enum-leakage-audit.md](file:///c:/workspace/shannon_allocation/docs/tasks/TASK-20260912-148-complete-enum-leakage-audit.md)
- [TASK-20260912-150-terminal-portfolio-position-management.md](file:///c:/workspace/shannon_allocation/docs/tasks/TASK-20260912-150-terminal-portfolio-position-management.md)
- [TASK-20260912-154-deep-munger-financial-decision.md](file:///c:/workspace/shannon_allocation/docs/tasks/TASK-20260912-154-deep-munger-financial-decision.md)

## Validation Evidence

- Pytest: `pytest python/portfolio/tests/test_terminal_semantic_completeness.py python/portfolio/tests/test_terminal_portfolio_positions.py` -> 25 passed in 13.24s.
- Frontend build: `npm --prefix frontend run build` -> 0 errors, 114 modules transformed.

## Decisions

- Tách bạch rõ giữa giá trị thị trường đã xác định và phần chưa lấy được giá khi tính tổng danh mục.
- Toàn bộ enum backend được map tập trung qua presentation layer, fallback luôn là tiếng Việt có nghĩa an toàn.

## Result

- Terminal QPort hoàn thiện 100% ngữ nghĩa tiếng Việt chuẩn đầu tư.
- Hoàn thiện tính toán tổng tài sản và giá thị trường từ PostgreSQL fallback catalog.
- Báo cáo kiểm thử và audit chi tiết lưu tại `docs/reports/terminal-semantic-data-audit.md`.

