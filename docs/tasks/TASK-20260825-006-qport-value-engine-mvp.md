---
id: TASK-20260825-006
title: Implement QPort Value Engine MVP for Non-Financial Enterprises
status: completed
priority: P0
created: 2026-08-25
updated: 2026-08-25
tags:
  - value-engine
  - valuation
  - owner-earnings
  - dcf
  - epv
  - reverse-dcf
  - margin-of-safety
  - invariants
related:
  - TASK-20260825-004
  - TASK-20260825-005
---

# TASK-20260825-006 — Implement QPort Value Engine MVP for Non-Financial Enterprises

## Requirement

Triển khai module **QPort Value Engine (QVE)** phục vụ định giá nội tại doanh nghiệp theo triết lý Buffett, đáp ứng đầy đủ tiêu chí nghiệm thu **`QVE-240 (MVP Definition of Done)`**:

1. **Deterministic Calculation & Pure Math**:
   - Tính toán hoàn toàn tất định, độc lập và không phụ thuộc vào AI (`QVE-021`, `QVE-240`).
2. **Owner Earnings & Normalization Engine (`QVE-101`, `QVE-102`, `QVE-103`)**:
   - $OwnerEarnings = NetIncome + D\&A - MaintenanceCAPEX \pm \Delta WorkingCapital$.
   - Cung cấp bridge giải thích từng thành phần.
3. **Mô hình định giá cho Doanh nghiệp phi tài chính (`QVE-111`, `QVE-112`, `QVE-140`)**:
   - **Owner Earnings DCF**: Mô hình chiết khấu dòng tiền chủ sở hữu 2 giai đoạn (5-10 năm + terminal value) với kịch bản Bear / Base / Bull.
   - **Earnings Power Value (EPV)**: Định giá sức mạnh sinh lời bền vững không tăng trưởng (Greenwald).
   - **Reverse DCF**: Tính ngược tốc độ tăng trưởng ngụ ý (Implied Growth Rate) mà thị trường đang phản ánh qua thị giá hiện tại.
4. **Phân tích kịch bản, Độ nhạy & Biên an toàn (`QVE-121`, `QVE-130`, `QVE-150`, `QVE-161`)**:
   - Ma trận độ nhạy 2 chiều (Discount Rate vs Terminal Growth).
   - Margin of Safety (MoS) = $(IntrinsicValue - CurrentPrice) / IntrinsicValue \times 100\%$.
   - Đánh giá Confidence Level dựa trên chất lượng và độ dài lịch sử BCTC.
5. **Báo cáo định giá Bất biến (`QVE-170`, `QVE-180`, `QVE-181`)**:
   - Cấu trúc `ValuationReport` mang hash ID tất định, versioned công thức, snapshot thời gian chạy và lưu vết toàn vẹn dữ liệu gốc (Lineage).
6. **Bất biến hệ thống**:
   - Hoàn toàn ở chế độ Thông tin (`BUY_AND_HOLD_INFORMATION_SYSTEM`), tuyệt đối không tự động phát sinh lệnh giao dịch hoặc thay đổi sổ cái danh mục (`QVE-022`, `QVE-203`).

## Context

Hệ thống đã có module `qport-financial-data` chuẩn hóa dữ liệu tài chính (Vnstock + CafeF) theo mô hình bitemporal point-in-time facts. Module Value Engine sẽ tiêu thụ các Canonical Facts này để tính toán giá trị nội tại cho các cổ phiếu trong danh mục.

## Acceptance Criteria

- [x] Tạo module `python/portfolio/value_engine/` với cấu trúc chuẩn.
- [x] `OwnerEarningsCalculator` tính đúng Owner Earnings với bridge bóc tách D&A, CAPEX, WC.
- [x] `DCFValuationModel` tính đúng giá trị nội tại theo Bear/Base/Bull scenarios.
- [x] `EPVValuationModel` tính đúng EPV (Zero-Growth Intrinsic Value).
- [x] `ReverseDCFModel` tính đúng Implied Growth Rate từ thị giá.
- [x] `SensitivityAnalyzer` tạo ma trận 2 chiều (Discount Rate vs Growth).
- [x] `ValuationReport` được xuất ra dưới dạng dataclass/JSON bất biến, có lineage đầy đủ tới từng canonical fact ID.
- [x] Unit tests, Invariant tests và Golden tests kiểm chứng tính đúng đắn trên dữ liệu thực tế (FPT).
- [x] Bất biến sổ cái được giữ nguyên 100% (không có API nào làm thay đổi ledger events).

## Constraints and Invariants

- Không bao giờ gán giá trị 0 cho dữ liệu thiếu (Preserve null != 0).
- Không đưa ra lời khuyên Mua/Bán (Chỉ cung cấp dải giá trị, biên an toàn và phân tích độ nhạy).
- Tính toán phải hoàn toàn tất định (cùng input -> cùng output).

## Implementation Tasks

### A. Core Models & Report Contracts
- [x] Tạo `python/portfolio/value_engine/models.py`:
  - `ValuationScenario`, `OwnerEarningsBridge`, `SensitivityMatrix`, `MarginOfSafetyResult`, `ValuationReport`.

### B. Normalization & Owner Earnings Engine
- [x] Tạo `python/portfolio/value_engine/owner_earnings.py`:
  - Phân tách D&A, Maintenance CAPEX policy, Working Capital adjustments.

### C. Valuation Models
- [x] Tạo `python/portfolio/value_engine/dcf.py` (Owner Earnings DCF).
- [x] Tạo `python/portfolio/value_engine/epv.py` (Earnings Power Value).
- [x] Tạo `python/portfolio/value_engine/reverse_dcf.py` (Market-Implied Growth).

### D. Engine Orchestrator & Report Generator
- [x] Tạo `python/portfolio/value_engine/engine.py`:
  - Điều phối luồng định giá: Facts -> Quality check -> Owner Earnings -> DCF/EPV/Reverse -> Scenarios -> Report.

### E. Test Suite Verification
- [x] Tạo `python/portfolio/tests/test_value_engine.py`:
  - Unit tests cho từng mô hình toán.
  - Integration test chạy end-to-end trên fixture BCTC thật của FPT.
  - Invariant tests (tất định, null handling, non-mutation).

## Validation Evidence

```text
pytest python/portfolio/tests/test_value_engine.py python/portfolio/tests/test_financial_data.py python/portfolio/tests/test_financial_pipeline.py
============================= 15 passed in 0.59s ==============================
```

## Decisions

### 2026-08-25 — Giai đoạn 1 tập trung Doanh nghiệp phi tài chính
Triển khai bộ mô hình chuẩn Buffett (Owner Earnings DCF + EPV + Reverse DCF) cho doanh nghiệp sản xuất/công nghệ/dịch vụ trước, các mô hình tài chính (Residual Income cho Ngân hàng, RNAV cho Bất động sản) sẽ được mở rộng trong giai đoạn 2.

## Result

Đã hoàn thành module QPort Value Engine MVP cho doanh nghiệp phi tài chính, hỗ trợ tính toán Owner Earnings, DCF 3 kịch bản, EPV, Reverse DCF, Ma trận độ nhạy và API Báo cáo định giá bất biến `GET /api/portfolio/valuation/:symbol`. Toàn bộ test suites đạt 100%.
