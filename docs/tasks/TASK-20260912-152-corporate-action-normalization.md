# TASK-20260912-152: Corporate Action Normalization for Dividend and Stock Split

- **ID**: TASK-20260912-152
- **Title**: Corporate Action Normalization for Dividend and Stock Split
- **Status**: completed
- **Priority**: high
- **Date**: 2026-09-12

---

## Requirement

1. Audit toàn bộ logic dividend & corporate actions hiện tại trong QPort.
2. Chuẩn hóa dữ liệu khi có stock split / bonus share / reverse split.
3. Đảm bảo historical price và per-share financial metrics (EPS, DPS, BVPS) cùng share basis.
4. Đảm bảo dividend history được xử lý đúng sau corporate action, bảo toàn total cash dividend economics.
5. Đảm bảo valuation không double-count dividend.
6. Đảm bảo các chỉ số dài hạn Buffett/Munger sử dụng dữ liệu nhất quán, không tạo fake growth / fake crash.
7. Đảm bảo portfolio position management tương thích, không làm thay đổi giá trị kinh tế giả tạo.

## Context

- QPort đã có dividend service / provider (TCBS, SSI, VNDirect, raw observation).
- Dữ liệu historical prices từ price providers (VNDirect, TCBS) có thể đã adjusted hoặc raw.
- SSI XLSX canonical data chứa financial statements (FY2011-FY2025).
- Đã audit luồng dữ liệu per-share và giá để chuẩn hóa thống nhất 1 share basis hiện hành mà không double-adjust.

## Acceptance Criteria

- [x] AC1: Existing dividend provider vẫn được sử dụng, không xây lại provider.
- [x] AC2: Không duplicate dividend logic.
- [x] AC3: Stock split không tạo fake growth/decline cho các chỉ số tài chính.
- [x] AC4: Historical EPS được normalize đúng share basis.
- [x] AC5: Historical DPS được normalize đúng share basis.
- [x] AC6: Historical price được normalize đúng 1 lần.
- [x] AC7: Không double-adjust price.
- [x] AC8: Không double-count dividend trong valuation.
- [x] AC9: Intrinsic value sử dụng consistent share basis (equity value vs IV per share).
- [x] AC10: Portfolio position bảo toàn economic value và total cost basis.
- [x] AC11: Buffett/Munger financial analysis không bị distortion bởi corporate actions.
- [x] AC12: Không làm ảnh hưởng valuation hiện tại.
- [x] AC13: Không làm ảnh hưởng dividend logic hiện tại.
- [x] AC14: Không làm ảnh hưởng Shannon/ERC/IP-DPS.
- [x] AC15: Bộ test suite đầy đủ 17 test cases bao phủ toàn bộ các kịch bản.
- [x] AC16: Audit script `audit_corporate_action_normalization.py` và report `docs/reports/corporate-action-normalization-audit.md`.

## Constraints and Invariants

- Không hard-code corporate actions theo từng ticker cụ thể.
- Buy & Hold invariant: Biến động giá hoặc corporate action không làm mất tính toàn vẹn kinh tế của sổ cái.
- Zero raw enum leakage trên UI (sử dụng tiếng Việt chuẩn).

## Implementation Tasks

- [x] Phase 1: Audit toàn bộ dividend, price, per-share metrics, valuation & corporate action logic hiện tại.
- [x] Phase 2: Thiết kế và cài đặt module `python/portfolio/corporate_action_normalizer.py`.
- [x] Phase 3: Cập nhật EPS calculation trên current share basis trong `munger_archetype_analyzers.py`.
- [x] Phase 4: Rà soát & kiểm chứng chống double-count dividend trong Valuation Engine.
- [x] Phase 5: Xây dựng script `audit_corporate_action_normalization.py` và chạy trên golden symbols (FPT, VIX, ACB, DGC).
- [x] Phase 6: Viết comprehensive test suite `test_corporate_action_normalization.py` (17 test cases).
- [x] Phase 7: Viết report chi tiết `docs/reports/corporate-action-normalization-audit.md`.
- [x] Phase 8: Kiểm thử toàn bộ regression, build frontend, commit & push.

## Decisions

1. Share Basis Normalization: Quy đổi các chỉ số per-share (EPS, DPS, BVPS) về current share basis ($S_{current}$) để bảo đảm $CAGR(EPS_{norm}) \equiv CAGR(\text{Net Profit})$ khi doanh nghiệp thực hiện chia thưởng / tách cổ phiếu phi kinh tế.
2. Anti Double-Adjustment: Đánh dấu rõ nguồn dữ liệu `is_provider_adjusted=True` (như VNDIRECT dchart) để tránh nhân hệ số điều chỉnh lùi lần thứ hai.
3. Clean Surplus Reconciliation: Tính chênh lệch lợi nhuận giữ lại theo chuẩn mực kế thừa, trả về giải thích tiếng Việt thân thiện, không render chuỗi mã lỗi kỹ thuật.

## Validation Evidence

1. Golden symbols audit:
```text
===================================================================================================================
QPORT CORPORATE ACTION & SHARE-BASIS NORMALIZATION AUDIT
===================================================================================================================
Mã     | Sự kiện quyền                    | Số CP gốc       | Số CP hiện hành  | Price  | EPS    | DPS    | Double-Adj | Status
-------------------------------------------------------------------------------------------------------------------
FPT    | Cổ phiếu thưởng & Cổ tức CP (15%/năm) | 396,000,000 cp  | 1,460,000,000 cp | PASS   | PASS   | PASS   | NONE       | PASS
VIX    | Phát hành tăng vốn & Cổ tức CP   | 100,000,000 cp  | 1,450,000,000 cp | PASS   | PASS   | PASS   | NONE       | PASS
ACB    | Cổ tức cổ phiếu (15–25%/năm)     | 937,000,000 cp  | 4,466,000,000 cp | PASS   | PASS   | PASS   | NONE       | PASS
DGC    | Cổ phiếu thưởng & Cổ tức CP      | 107,000,000 cp  | 379,000,000 cp   | PASS   | PASS   | PASS   | NONE       | PASS
===================================================================================================================
```

2. Test suite results:
```text
python\portfolio\tests\test_corporate_action_normalization.py ................. [100%]
============================= 17 passed in 0.59s ==============================
```

3. Regression tests:
```text
python\portfolio\tests\test_terminal_portfolio_positions.py ............ [ 41%]
...........                                                              [ 79%]
python\portfolio\tests\test_ui_raw_enum_regression.py .                  [ 82%]
python\portfolio\tests\test_na_null_metrics_regression.py .....          [100%]
============================= 29 passed in 9.38s ==============================
```

4. Frontend Vite production build:
```text
✓ 114 modules transformed.
dist/index.html                   1.86 kB
dist/assets/index-B4V80acv.css  260.44 kB
dist/assets/index-BbsRtcJn.js   693.84 kB
✓ built in 1.54s
```

## Result

Hoàn thành xuất sắc chuẩn hóa Corporate Action & Share-Basis:
- Module `corporate_action_normalizer.py` đáp ứng đầy đủ tất cả yêu cầu về quy đổi share basis, chống double-adjust giá, bảo toàn kinh tế cổ tức, kiểm tra không double count trong định giá và điều chỉnh vị thế danh mục.
- Toàn bộ 4 mã golden symbols (FPT, VIX, ACB, DGC) đều đạt kết quả PASS hoàn hảo.
- 17 test cases mới và 29 regression tests pass 100%.
