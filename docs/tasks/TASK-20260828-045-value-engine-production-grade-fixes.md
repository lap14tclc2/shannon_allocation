# TASK-20260828-045: Value Engine Production-Grade Fixes (confidence gate, mid-cycle OE, bank isolation, growth trace, moat evidence)

- **ID**: `TASK-20260828-045`
- **Title**: Fix 7 audit issues in Buffett–Munger value engine to production-grade
- **Status**: `verified`
- **Priority**: `high`
- **Date**: `2026-08-28`

## Requirement
Audit của chuyên gia (đính kèm) cho engine 7/10 và liệt kê 7 vấn đề cần sửa trước khi coi `HIGH_CONVICTION_VALUE` là production-grade:

**P0**
1. `HIGH_CONVICTION_VALUE` phải yêu cầu `confidence == HIGH`; `MEDIUM` cộng ≥5% MOS yêu cầu; `LOW` cộng ≥10%. Hiện engine bỏ qua confidence.
2. "Normalized mid-cycle Owner Earnings" chưa thực sự normalized: FPT/HPG đang gán nhãn "5Y averaged" nhưng giá trị là tính từ FY2025. Với cyclical phải dùng normalization 7–10Y thật (median margin × median revenue), không được dán nhãn FY1 thành "5Y averaged".
3. Ngân hàng (MBB) còn artifacts DCF generic: EPV, reverse DCF, sensitivity r×g kiểu Gordon. Bank phải chỉ xuất analytics tương thích ngân hàng, sensitivity phải là ROE×CoE.

**P1**
4. Growth chưa có derivation trace: g phải từ reinvestment rate × incremental ROE, capped bởi lịch sử/maturity (VNM 5Y CAGR âm mà Base growth 18% là quá aggressive).
5. Moat vẫn gần như suy từ ROE; phải có evidence breakdown theo từng nguồn moat; ROE đơn lẻ không thể tạo WIDE moat.
6. Capital Allocation 15/15 quá dễ; phải dùng incremental-return evidence (ΔOwnerEarnings / ΔRetainedCapital).
7. Bank health còn dùng CFO/cash conversion (vô nghĩa cho bank); phải bỏ khỏi cash_quality_score.

## Acceptance Criteria
- [x] P0-1: `MarginOfSafetyEngine` nhận `confidence_level`; HIGH +0%, MEDIUM +5%, LOW +10% MOS; HIGH_CONVICTION chỉ khi confidence==HIGH.
- [x] P0-2: `calculate_cycle_normalized` dùng median margin × median revenue tối thiểu 3 năm; nhãn trung thực (số năm + phương pháp); không dán nhãn sai.
- [x] P0-3: Bank dùng sensitivity ROE×CoE; EPV/reverse DCF = None cho bank; `SensitivityMatrix` có `sensitivity_type` + nhãn hàng/cột.
- [x] P1-4: Growth derivation ghi trace (retained rate, incremental ROE, historical CAGR, cap); growth bị cap bởi lịch sử; confidence giảm khi lịch sử âm.
- [x] P1-5: Moat có evidence breakdown theo nguồn; ROE đơn lẻ không đạt WIDE (20/20).
- [x] P1-6: Capital Allocation dùng incremental-return; HPG có nợ lớn + FCF âm không còn tự động 15/15.
- [x] P1-7: Bank cash_quality không dùng CFO/cash conversion.
- [x] Tests pass + `npm run build` pass.

## Constraints and Invariants
- Không đổi hợp đồng dữ liệu hiện có gây vỡ frontend; thêm field mới phải có default.
- `BUY_AND_HOLD_INFORMATION_SYSTEM`: không sinh lệnh mua/bán.
- Không dùng synthetic fallback cho OE <= 0 (vẫn chặn định giá).
- Frontend `ValuationPage.jsx` phải render nhãn matrix mới nếu có.

## Implementation Tasks
- [x] P0-1: sửa `margin_of_safety.py` + `engine.py` truyền `confidence_level`.
- [x] P0-2: sửa `owner_earnings.py` `calculate_cycle_normalized`.
- [x] P0-3: sửa `bank_valuation.py` + `engine.py` + `models.py` (SensitivityMatrix type/labels), disable EPV/reverse cho bank.
- [x] P1-4: growth derivation trong `engine.py` + `models.py` (growth_derivation).
- [x] P1-5: moat evidence breakdown trong `quality_scorer.py`.
- [x] P1-6: capital allocation incremental-return trong `quality_scorer.py`.
- [x] P1-7: bank cash quality bỏ CFO trong `quality_scorer.py` + `app/main.py`.
- [x] Cập nhật tests (thêm test mới, sửa test cũ theo rule mới).
- [x] Chạy `pytest` + `npm run build`.

## Related Notes
- [TASK-20260828-040](file:///f:/workspace/shannon_allocation/docs/tasks/TASK-20260828-040-overhaul-valuation-engine-to-true-buffett-munger-standards.md)
- [TASK-20260828-041](file:///f:/workspace/shannon_allocation/docs/tasks/TASK-20260828-041-implement-buffett-munger-value-investing-rule-engine.md)

## Validation Evidence
- `pytest portfolio/tests/test_buffett_munger_rule_engine.py portfolio/tests/test_value_engine_audit_fixes.py portfolio/tests/test_buffett_valuation_upgrade.py portfolio/tests/test_vi_labels.py portfolio/tests/test_valuation_page_contract.py portfolio/tests/test_value_engine.py` → **23 passed**.
- `npm run build` trên `frontend/` → thành công trong 2.68s, 0 lỗi.
- Toàn bộ suite `portfolio/tests`: 270 passed, 1 skipped; 7 failures trong đó 6 là pre-existing (file `AppNav.jsx`, `header-v2.css`, `mobile-iphone.css`, `StartPage.jsx`, `cafef_financials.py` không nằm trong scope), 1 regression đã sửa (`test_valuation_page_contract`).
- `CONFIDENCE_MOS_PENALTY = {HIGH: 0, MEDIUM: 5, LOW: 10, BLOCKED: 10}`.

## Decisions
- Giữ lại struct cũ để tương thích; thêm field mới có default.
- Moat evidence dùng dữ liệu sẵn trong `financial_history_10y` (margin stability, ROE persistence, scale, durability) + cảnh báo trung thực khi thiếu dữ liệu.
- Growth derivation: `g = retention × incremental_roe`, capped bởi historical CAGR + maturity; nếu CAGR lịch sử < 3% → hạ confidence.

## Result
Đã sửa toàn bộ 7 vấn đề từ audit: (P0-1) HIGH_CONVICTION giờ yêu cầu confidence==HIGH với penalty MEDIUM +5%/LOW +10%; (P0-2) mid-cycle OE dùng median margin × median revenue ≥3 năm, nhãn trung thực không dán nhãn sai; (P0-3) bank dùng sensitivity RIM ROE×CoE, EPV/reverse DCF = None; (P1-4) growth có trace đầy đủ + cap lịch sử + hạ confidence; (P1-5) moat có evidence breakdown 6 nguồn, ROE đơn lẻ không đạt WIDE; (P1-6) capital allocation dùng incremental-return; (P1-7) bank cash_quality bỏ CFO/cash conversion. 23 tests pass, build pass.