# TASK-20260828-042: Optimize /api/portfolio/sync Performance & Full Vietnamese Localization of Valuation Page

- **ID**: `TASK-20260828-042`
- **Title**: Optimize /api/portfolio/sync Performance (Parallel Data Fetching) & Pure Vietnamese Localization of Valuation Page
- **Status**: `completed`
- **Priority**: `high`
- **Date**: `2026-08-28`

## Requirement
1. **Tối ưu tốc độ `/api/portfolio/sync`:** Hiện tại việc đồng bộ giá lịch sử hàng ngày lặp tuần tự từng mã (`for symbol in ledger_symbols`) với các request mạng và delay kéo dài hơn 1 phút (70s). Cần tối ưu song song (Concurrent / ThreadPoolExecutor) hoặc truy xuất cache thông minh, rút ngắn thời gian sync xuống dưới 5–10 giây.
2. **Việt hóa thuần Việt 100% trang Định giá (`ValuationPage.jsx`):** Loại bỏ/chuyển dịch các thuật ngữ tiếng Anh kỹ thuật gây khó hiểu (như *Base IV, MoS, Owner Earnings, CAPEX, D&A, Reinvestment, Financial Fortress, Reverse DCF, Sensitivity Matrix, Debt Payback, Compounder, Retained Capital...*) thành ngôn ngữ tài chính tiếng Việt gần gũi, rõ nghĩa và dễ hiểu cho nhà đầu tư phổ thông.

## Acceptance Criteria
- [x] `/api/portfolio/sync` chạy song song (Thread pool cho các symbols), giảm thời gian từ > 60s xuống còn 2.08s.
- [x] `ValuationPage.jsx` được biên tập lại toàn bộ nhãn, tiêu đề, giải thích phương pháp, thẻ chỉ số sang tiếng Việt tự nhiên và chuẩn mực.
- [x] Các thuật ngữ viết tắt tiếng Anh (P/E, P/B, ROE, EPS) được chú thích tiếng Việt rõ ràng; các thuật ngữ như Base IV $\rightarrow$ Giá trị Thực cơ sở; MoS $\rightarrow$ Biên An Toàn; Owner Earnings $\rightarrow$ Lợi Nhuận Thực Chủ Doanh Nghiệp; Maintenance CapEx $\rightarrow$ Chi phí Tái đầu tư Duy trì.
- [x] Build frontend `npm run build` thành công, kiểm thử unit test pass.

## Implementation Tasks
- [x] Tối ưu hóa hàm `sync_daily` trong `python/portfolio/service.py` bằng `ThreadPoolExecutor` để tải đồng thời dữ liệu giá của các mã và ưu tiên `VndirectProvider` tải D1 nhanh.
- [x] Biên tập và cập nhật lại giao diện `frontend/src/pages/ValuationPage.jsx` theo phong cách tiếng Việt tự nhiên, chuẩn mực đầu tư giá trị.
- [x] Kiểm thử tốc độ gọi API `/api/portfolio/sync` và giao diện thực tế (Benchmark: 2.08s).

## Related Notes
- [TASK-20260828-041](file:///f:/workspace/shannon_allocation/docs/tasks/TASK-20260828-041-implement-buffett-munger-value-investing-rule-engine.md)

## Validation Evidence
- Benchmark `sync_daily()` trước tối ưu: 70+ giây (do tải tuần tự và gọi vnstock theo chunk 150 ngày).
- Benchmark `sync_daily()` sau tối ưu (ThreadPoolExecutor + VndirectProvider primary): **2.08 giây** (rút ngắn gấp >30 lần).
- `npm run build` trên `frontend/` hoàn thành thành công trong 1.04s, 0 lỗi cú pháp hay thiếu biến.

## Decisions
- Song song hóa việc tải dữ liệu giá lịch sử qua `ThreadPoolExecutor(max_workers=8)`.
- Ưu tiên `VndirectProvider` tải toàn bộ chuỗi D1 trong 1 HTTP request nhanh, `VnstockProvider` làm fallback.
- Thuần Việt hóa 100% các khái niệm định giá trong `ValuationPage.jsx`:
  - `Base IV` $\rightarrow$ **Giá trị Thực cơ sở**
  - `Margin of Safety (MoS)` $\rightarrow$ **Biên An Toàn Thực tế** (kèm Yêu cầu tối thiểu theo chuẩn Buffett-Munger)
  - `Owner Earnings` $\rightarrow$ **Lợi nhuận Thực của Chủ Doanh nghiệp**
  - `Financial Fortress` $\rightarrow$ **Pháo đài Tài chính**
  - `Sensitivity Matrix` $\rightarrow$ **Bảng Độ nhạy Định giá theo Tỷ lệ Chiết khấu và Tăng trưởng**
  - `EPS / ROE / P/E / P/B` $\rightarrow$ **Lợi nhuận/CP / Sinh lời Vốn / Giá/LNST / Giá/Sổ sách**

## Result
Đã hoàn tất tối ưu tốc độ API sync từ > 1 phút xuống **2.08 giây** và chuyển ngữ toàn bộ giao diện trang Định giá sang tiếng Việt tự nhiên, chuẩn mực.

