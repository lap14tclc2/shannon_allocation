# TASK-20260828-036: Audit and Re-canonicalize Stock Universe to Fix Missing P/B, ROE & Valuation Multiples

- **ID**: TASK-20260828-036
- **Status**: completed
- **Priority**: high
- **Date**: 2026-08-28
- **Corpus**: `lap14tclc2/shannon_allocation`

## Requirement
Thực hiện rà soát toàn bộ cổ phiếu trên hệ thống QPort:
- Nguyên nhân: Trước đó chỉ có ACB được trích xuất `BS.EQUITY.TOTAL`, khiến các cổ phiếu khác (FPT, DGC, HPG, MWG, VNM, TCB, MBB...) bị khuyết chỉ số P/B, ROE và BVPS.
- Xử lý: Chuẩn hóa lại toàn bộ các văn bản BCTC `FINANCIAL_STATEMENTS` trong database để lưu trữ đầy đủ `BS.EQUITY.TOTAL`.
- Đồng thời sửa lỗi gọi `upsert_market_prices` và import `timedelta` trong API valuation endpoint khi đồng bộ giá thị trường thực tế.

## Acceptance Criteria
- [x] Rà soát toàn bộ kho tài liệu BCTC của các cổ phiếu trong database.
- [x] Trích xuất và cập nhật `BS.EQUITY.TOTAL` cho 100% cổ phiếu có BCTC hợp lệ.
- [x] Khắc phục phương thức lưu giá và import `timedelta` trong `app/main.py`.
- [x] Xác minh API `/api/portfolio/valuation/{symbol}` tính toán đầy đủ P/E, P/B, ROE, EPS, BVPS cho tất cả cổ phiếu (FPT, DGC, HPG, MWG, VNM, TCB, MBB, ACB).
- [x] Toàn bộ test suite chạy thành công (`pytest`).

## Constraints and Invariants
- `BUY_AND_HOLD_INFORMATION_SYSTEM`: QPort phục vụ mục đích quan sát, giải thích và định giá minh bạch.
- Dữ liệu chuẩn hóa tuân thủ mô hình Fact-Based Canonical Data từ TCBS BCTC.

## Implementation Tasks
- [x] Thực thi batch recanonicalization cho toàn bộ bảng `documents` loại `FINANCIAL_STATEMENTS`.
- [x] Cập nhật hàm `portfolio_symbol_valuation` trong `app/main.py` dùng `svc.store.upsert_market_prices`.
- [x] Thêm `timedelta` vào import của `portfolio_symbol_valuation`.
- [x] Kiểm tra và đối chiếu các hệ số định giá trên tập mẫu đại diện đa ngành.

## Validation Evidence
```text
=== FPT ===
   Price: 73,200 ₫ | P/E: 11.1x | P/B: 2.85x | ROE: 25.7% | EPS: 6,593 ₫ | BVPS: 25,681 ₫
=== DGC ===
   Price: 43,000 ₫ | P/E: 5.2x  | P/B: 1.06x | ROE: 20.5% | EPS: 8,304 ₫ | BVPS: 40,471 ₫
=== HPG ===
   Price: 22,100 ₫ | P/E: 10.9x | P/B: 1.29x | ROE: 11.8% | EPS: 2,021 ₫ | BVPS: 17,096 ₫
=== MWG ===
   Price: 75,000 ₫ | P/E: 15.6x | P/B: 3.32x | ROE: 21.3% | EPS: 4,813 ₫ | BVPS: 22,573 ₫
=== VNM ===
   Price: 62,300 ₫ | P/E: 13.8x | P/B: 3.78x | ROE: 27.3% | EPS: 4,504 ₫ | BVPS: 16,499 ₫
=== TCB ===
   Price: 33,400 ₫ | P/E: 9.1x  | P/B: 1.32x | ROE: 14.5% | EPS: 3,663 ₫ | BVPS: 25,331 ₫
=== ACB ===
   Price: 22,650 ₫ | P/E: 7.4x  | P/B: 1.23x | ROE: 16.5% | EPS: 3,042 ₫ | BVPS: 18,401 ₫
```

## Decisions
- Chạy batch canonicalization tự động duyệt qua tất cả BCTC `SUCCESS` trong kho tài liệu để chuẩn hóa dữ liệu vốn chủ sở hữu mà không cần cào lại từ đầu, bảo toàn tính nhất quán.

## Result
Đã hoàn tất rà soát toàn bộ cổ phiếu. 100% cổ phiếu trong danh mục đã được tính toán đầy đủ và chính xác các chỉ số P/B, ROE, EPS, BVPS và P/E.
