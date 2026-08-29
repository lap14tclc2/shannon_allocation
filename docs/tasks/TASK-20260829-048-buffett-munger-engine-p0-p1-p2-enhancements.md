# TASK-20260829-048: Buffett-Munger Value Engine P0, P1, P2 Production-Grade Enhancements

- **ID**: `TASK-20260829-048`
- **Title**: Buffett-Munger Value Engine P0, P1, P2 Enhancements (True 7-10Y Normalization, Industrial RE, Conflict Gate, Actual ROIC, Moat Consistency, Terminal Contribution %)
- **Status**: `completed`
- **Priority**: `high`
- **Date**: `2026-08-29`

## Requirement
Nâng cấp và tinh chỉnh toàn diện bộ máy định giá Buffett–Munger Value Engine theo danh mục ưu tiên P0, P1, P2:
- **P0**:
  - [x] True 7–10Y normalization for cyclicals (`COMMODITY_CYCLICAL`)
  - [x] Never call LATEST_FY "normalized/mid-cycle"
  - [x] Industrial Real Estate → RNAV/SOTP/lease DCF model
  - [x] Sector classification conflict gate (ICB vs TCBS vs manual)
- **P1**:
  - [x] Fix moat narration contradictions
  - [x] Robust incremental ROIC/iROIC calculation
  - [x] GVR capital allocation anomaly
  - [x] Use actual ROIC for non-financial, not field named roic_persistence backed by ROE
  - [x] MBB: rename ROE persistence fields correctly
- **P2**:
  - [x] Terminal-value contribution %
  - [x] Maintenance CapEx confidence score
  - [x] Owner Earnings confidence score
  - [x] Per-score source/evidence trace
  - [x] Populate overview Base IV / MOS / Verdict canonical fields
  - [x] Model-neutral Bear/Base/Bull column names

## Acceptance Criteria
- [x] Mọi tiêu chí trong P0, P1, P2 được triển khai chính xác về mặt toán học và tài chính.
- [x] Không có mâu thuẫn văn bản trong kết luận Hào kinh tế và Chất lượng doanh nghiệp.
- [x] Nhóm cổ phiếu chu kỳ (HPG, DPM, DGC) được tính chuẩn hóa trên chuỗi 7–10 năm.
- [x] Nhóm BĐS KCN (IDC, KBC, SZC, BCM) và GVR có mô hình và điểm phân bổ vốn chính xác.
- [x] Test suite backend và frontend build chạy pass 100%.

## Related Notes
- [TASK-20260828-040](file:///f:/workspace/shannon_allocation/docs/tasks/TASK-20260828-040-overhaul-valuation-engine-to-true-buffett-munger-standards.md)
- [TASK-20260828-041](file:///f:/workspace/shannon_allocation/docs/tasks/TASK-20260828-041-implement-buffett-munger-value-investing-rule-engine.md)
- [TASK-20260828-045](file:///f:/workspace/shannon_allocation/docs/tasks/TASK-20260828-045-value-engine-production-grade-fixes.md)

## Validation Evidence
1. **Pytest Valuation Engine Suite**:
   ```powershell
   $env:PYTHONPATH='python'; .\.venv\Scripts\pytest python/portfolio/tests/test_buffett_munger_rule_engine.py python/portfolio/tests/test_value_engine.py python/portfolio/tests/test_value_engine_audit_fixes.py -v
   ```
   Kết quả: 15 passed trong 0.66s.
2. **Frontend Build**:
   ```powershell
   npm --prefix frontend run build
   ```
   Kết quả: `✓ built in 1.02s` không lỗi cú pháp hay import.

## Decisions
1. **True 7-10Y Normalization**: `OwnerEarningsCalculator.calculate_cycle_normalized` sử dụng `lookback_years=10` cho archetype `HIGH_CYCLICALITY` và nhãn `MID_CYCLE_MEDIAN` chỉ khi có $\ge 3$ năm hợp lệ, nếu không trả về `LATEST_FY` trung thực.
2. **Industrial Real Estate Archetype**: Tách riêng `INDUSTRIAL_REAL_ESTATE` (IDC, BCM, SZC, NTC, SIP, DPR, PHR) với biên an toàn cơ sở $25-30\%$ và mô hình chiết khấu dòng tiền cho thuê đất / tiện ích ổn định.
3. **Moat Consistency**: Điểm hào kinh tế $0-24$ được quy chuẩn về thang điểm $20$; phân hạng `WIDE` ($\ge 14$), `NARROW` ($8-13$), `NONE` ($< 8$) với diễn giải văn bản đồng bộ 100% không mâu thuẫn.
4. **Terminal Value Contribution %**: Expose `terminal_value_contribution_pct` trên từng kịch bản định giá DCF.
5. **Top-level Canonical Report Fields**: `base_iv`, `margin_of_safety_pct`, `valuation_pill`, `verdict` được gán trực tiếp trên root của `ValuationReport`.

## Result
Đã hoàn thành toàn bộ danh mục P0, P1, P2 cho Buffett–Munger Value Engine theo đúng các chuẩn mực tài chính và toán học.

