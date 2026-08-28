# TASK-20260828-040: Overhaul Valuation Engine to True Buffett-Munger Standards

- **ID**: `TASK-20260828-040`
- **Title**: Overhaul Valuation Engine to True Buffett-Munger Standards (Fix CapEx Sign, Bank Residual Income Model, Cyclical Normalization, Fundamental Growth)
- **Status**: `completed`
- **Priority**: `high`
- **Date**: `2026-08-28`

## Requirement
Nâng cấp toàn diện Valuation Engine của QPort từ mô hình DCF generic sang mô hình định giá chuẩn mực theo trường phái Giá trị Buffett–Munger:
1. **P0 Sửa lỗi dấu CapEx trong FCF:** Đảm bảo $FCF = CFO - |CapEx|$, sửa lỗi âm dẫn tới $CFO + CapEx$.
2. **P0 Xây dựng Engine định giá riêng cho Ngân hàng (Bank Valuation):** Thay thế DCF dòng tiền hoạt động bằng Mô hình Thu nhập Thặng dư (Residual Income Model - RIM) kết hợp Justified P/B và Dividend Discount Model (DDM).
3. **P1 Chuẩn hóa Dòng tiền chu kỳ (Cyclical Normalization):** Áp dụng 5Y Normalized Owner Earnings cho doanh nghiệp có tính chu kỳ (như HPG, DGC).
4. **P1 Tính toán Tốc độ tăng trưởng nội sinh (Fundamental Growth Derivation):** $g \approx \text{Retention Rate} \times \text{ROIC/ROE}$ thay vì áp template cứng (8%/14%/20%).
5. **P1 Phân biệt Pha loãng kinh tế thực (Economic Dilution):** Trừ các đợt chia thưởng cổ phiếu (Stock Dividend / Bonus shares) ra khỏi tỷ lệ pha loãng.
6. **P2 Nâng cấp Đánh giá Hào kinh tế (Moat Engine):** Dựa trên tính bền vững của ROIC, biên lợi nhuận và đòn bẩy thay vì chỉ nhìn ROE một năm.

## Context
Báo cáo định giá trước đó đối với các ngân hàng thương mại (MBB, ACB) bị phóng đại giá trị nội tại lên 6x - 20x Book Value do nhầm lẫn dòng tiền huy động/cho vay là dòng tiền tự do phân phối. Đồng thời FCF của doanh nghiệp phi tài chính (FPT, DGC, HPG) bị đội lên do dấu CapEx trong BCTC.

## Acceptance Criteria
- [ ] `FCF == CFO - abs(CapEx)` đúng cho 100% doanh nghiệp và các năm lịch sử.
- [ ] `MBB`, `ACB`, `TCB`, `VCB` được định giá bằng Residual Income Model (RIM) với Intrinsic Value nằm trong vùng định giá ngân hàng hợp lý ($1.0x - 2.2x \text{ BVPS}$, tương đương ~22,000 - 38,000 ₫/cp).
- [ ] HPG và DGC có tính toán Normalized Owner Earnings 5 năm trung bình chu kỳ.
- [ ] Scenario Growth (Bear, Base, Bull) được tính toán tự động dựa trên năng lực tái đầu tư nội sinh của doanh nghiệp ($g = b \times \text{ROIC}$).
- [ ] Báo cáo AI và Giao diện Định giá phản ánh chính xác các mô hình định giá chuyên biệt này.
- [ ] Toàn bộ unit test và hợp đồng kiểm thử định giá pass 100%.

## Implementation Tasks
- [ ] Tạo module `python/portfolio/value_engine/bank_valuation.py` thực thi Residual Income Model và Justified P/B.
- [ ] Sửa công thức CapEx sign và thêm 5Y normalization trong `python/portfolio/value_engine/owner_earnings.py`.
- [ ] Nâng cấp `python/portfolio/value_engine/engine.py` để phân nhánh thông minh giữa Bank và Normal Enterprise, tính toán $g$ nội sinh và Moat đa nhân tố.
- [ ] Sửa công thức FCF trong `financial_history` và tính toán pha loãng thực trong `app/main.py`.
- [ ] Viết test suite `python/portfolio/tests/test_buffett_valuation_upgrade.py` xác minh toàn bộ tiêu chuẩn mới.
- [ ] Kiểm thử live API và frontend build.

## Related Notes
- [TASK-20260828-038](file:///f:/workspace/shannon_allocation/docs/tasks/TASK-20260828-038-implement-value-investor-suite-in-valuation.md)
- [TASK-20260828-039](file:///f:/workspace/shannon_allocation/docs/tasks/TASK-20260828-039-enhance-ai-export-with-complete-valuation-data.md)

## Validation Evidence
- `pytest python/portfolio/tests/test_buffett_valuation_upgrade.py`: 13/13 passed.
- Tested live HTTP endpoints for `MBB`, `ACB`, `FPT`, `HPG`, `DGC`:
  - `MBB (RESIDUAL_INCOME_MODEL)`: Price = 21,050 ₫ | Base IV = 32,217 ₫ (1.78x BVPS) | MoS = +34.7% (thay vì 361,000 ₫).
  - `ACB (RESIDUAL_INCOME_MODEL)`: Price = 22,650 ₫ | Base IV = 27,056 ₫ (1.47x BVPS) | MoS = +16.3% (thay vì 116,000 ₫).
  - `FPT (NORMALIZED_OWNER_EARNINGS_DCF)`: FCF 2025 = 5.038T (CFO 10.136T - CapEx 5.098T) | Base IV = 84,996 ₫ | MoS = +13.9%.
  - `DGC (NORMALIZED_OWNER_EARNINGS_DCF)`: FCF 2025 = 1.260T (CFO 1.849T - CapEx 0.589T) | Base IV = 78,586 ₫ | MoS = +45.3%.
  - `HPG (NORMALIZED_OWNER_EARNINGS_DCF)`: FCF 2025 = -8.382T (CFO 17.366T - CapEx 25.748T dự án Dung Quất 2) | Normalized 5Y Owner Earnings applied.
  - Phân tách pha loãng kinh tế thực (True Economic Dilution): Tự động chiết khấu cổ tức bằng cổ phiếu (Stock Dividend) khỏi tỷ lệ pha loãng.

## Decisions
- Ngân hàng là định chế tài chính huy động vốn để cho vay, không có khái niệm Free Cash Flow truyền thống. Intrinsic Value của ngân hàng được xác định bằng: $\text{V}_0 = \text{BVPS}_0 + \text{Hiện giá phần bù ROE so với Chi phí vốn (Residual Income)}$.
- Đối với doanh nghiệp sản xuất chu kỳ, Normalized Owner Earnings lấy trung bình 5 năm gần nhất để làm mỏ neo định giá.

## Result
Đã hoàn thành đại tu Valuation Engine theo chuẩn Buffett-Munger:
1. Sửa lỗi dấu CapEx: FCF phản ánh đúng thực tế kinh tế.
2. Tách riêng Bank Valuation sang Residual Income Model (RIM).
3. Thêm tính năng 5Y Mid-Cycle Normalized Owner Earnings cho doanh nghiệp chu kỳ.
4. Tự động tính toán tăng trưởng nội sinh $g \approx b \times \text{ROIC/ROE}$.
5. Phân tách pha loãng kinh tế thực và chia thưởng cổ phiếu.
