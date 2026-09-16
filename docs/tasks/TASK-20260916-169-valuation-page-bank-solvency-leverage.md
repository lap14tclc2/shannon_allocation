# TASK-20260916-169: Update Valuation Page Solvency Metric for Bank & Financial Archetypes

## Metadata
- **ID**: `TASK-20260916-169`
- **Title**: Update Valuation Page Solvency Metric for Bank & Financial Archetypes (Leverage & Capital Cushion instead of Debt/Equity)
- **Status**: in-progress
- **Priority**: high
- **Date**: 2026-09-16
- **Branch**: `feature/buffett-munger-refactor`

---

## Requirement
Người dùng phản hồi:
*"Trang định giá hiện tại chưa đúng lắm vì bank vẫn dùng nợ/vcsh, update lại logic của valuation page"*

## Context & Root Cause Analysis
1. Tại backend `canonical_valuation.py`, trường `financial_fortress` tính toán `debt_to_equity_ratio` cho toàn bộ doanh nghiệp. Mặc dù `is_financial` được xác định, `financial_fortress` vẫn gán `debt_to_equity_ratio` và thiếu các chỉ số đo lường an toàn tài chính đặc thù của Ngân hàng/Tài chính:
   - Tổng tài sản (`total_assets_vnd`).
   - Đòn bẩy tài sản (`bank_leverage` = `total_assets / equity`).
   - Tỷ lệ đệm vốn (`equity_to_assets_pct` = `equity / total_assets * 100`).
   - Nhãn chỉ số hiển thị (`solvency_label`, `solvency_display`).
2. Tại frontend `ValuationPage.jsx` và `ValuationDetailOverlay.jsx`:
   - Thẻ `02 Pháo đài Tài chính · Nợ / VCSH` đang cố định tiêu đề và hiển thị:
     - `Nợ / Vốn chủ sở hữu (D/E)`
     - `Tổng nợ vay`
     - `Tiền mặt & tương đương`
     - `Nợ ròng (Nợ − Tiền)`
     - `Nợ ròng / EBITDA`
   - Đối với ngân hàng (như TCB, ACB, MBB...), mô hình kinh doanh là huy động tiền gửi (tiền gửi là nguồn vốn kinh doanh, không phải nợ vay thông thường) và cấp tín dụng. Việc hiển thị "Nợ/VCSH" hoặc "Nợ ròng / EBITDA" là sai lệch bản chất tài chính ngân hàng theo chuẩn mực định giá Buffett–Munger.

## Acceptance Criteria
- [x] Tại `canonical_valuation.py`:
  - Trong `financial_fortress`, khi `is_bank` hoặc `archetype == BANK`:
    - Tính toán `bank_leverage = round(total_assets / equity, 2)` và `equity_to_assets_pct = round(equity / total_assets * 100, 1)`.
    - Thêm các trường ngữ nghĩa: `is_bank: True`, `is_financial: True`, `solvency_label: "Đòn bẩy TS (TS/VCSH)"`, `solvency_display`, `equity_to_assets_pct`, `total_assets_vnd`.
    - Cập nhật chẩn đoán `diagnosis` cho ngân hàng phản ánh chất lượng đệm vốn và đòn bẩy an toàn.
- [x] Tại `ValuationPage.jsx` (Trang Định giá chính):
  - Thẻ `02 Pháo đài Tài chính`:
    - Nếu là Ngân hàng (`isBank` / `report.archetype_profile?.archetype === 'BANK'`):
      - Đổi tiêu đề: `Pháo đài Tài chính · Đòn bẩy TS`
      - Hiển thị chỉ số chính: `${bank_leverage}x` (kèm phụ đề: `Đòn bẩy Tài sản · Đệm vốn ${equity_to_assets_pct}%`)
      - Danh sách chi tiết hiển thị: `Tổng Tài sản`, `Vốn Chủ Sở Hữu`, `Tỷ lệ Đệm vốn (VCSH/TS)`, `Đòn bẩy Tài sản (TS/VCSH)`.
- [x] Tại `ValuationDetailOverlay.jsx` (Modal chi tiết định giá):
  - Đồng bộ hiển thị trụ cột 2 Pháo đài tài chính cho Ngân hàng tương tự.
- [x] Kiểm thử tự động `pytest` và build frontend `npm run build` thành công.

## Constraints and Invariants
- Giữ nguyên các doanh nghiệp thông thường (`NORMAL_ENTERPRISE`) hiển thị Nợ/VCSH và Net Debt.
- Đảm bảo tính nhất quán tuyệt đối giữa `BusinessPage` và `ValuationPage`.

## Implementation Tasks
- [x] Cập nhật `python/portfolio/canonical_valuation.py`.
- [x] Cập nhật `frontend/src/pages/ValuationPage.jsx`.
- [x] Cập nhật `frontend/src/components/ValuationDetailOverlay.jsx`.
- [x] Chạy automated test suite & verify frontend build.

## Validation Evidence
1. **Automated Tests**:
   - `pytest python/portfolio/tests/test_valuation_page_contract.py -v`: 3 passed in 0.62s.
2. **Frontend Build Verification**:
   - `npm run build`: `built in 3.42s` thành công không có lỗi.
3. **Behavioral Invariant**:
   - Ngân hàng (TCB, ACB, MBB...):
     - Tiêu đề: `Pháo đài Tài chính · Đòn bẩy TS`
     - Metric chính: `6.6x` (TCB) kèm sub `Đòn bẩy Tài sản · Đệm vốn 15.1%`
     - Chi tiết: `Tổng tài sản`, `Vốn chủ sở hữu`, `Tỷ lệ Đệm vốn (VCSH/TS)`, `Đòn bẩy Tài sản (TS/VCSH)`.
   - Doanh nghiệp phi tài chính: Giữ nguyên `Nợ / Vốn CSH (D/E)`, `Tổng nợ vay`, `Tiền mặt`, `Nợ ròng`, `Nợ ròng/EBITDA`.

## Result
Đã hoàn thành chuẩn hóa logic Trụ cột Pháo đài Tài chính trên trang Định giá (`ValuationPage.jsx` và `ValuationDetailOverlay.jsx`), phân tách bản chất đòn bẩy ngân hàng/tài chính khỏi nợ vay doanh nghiệp sản xuất theo đúng chuẩn Buffett-Munger.

