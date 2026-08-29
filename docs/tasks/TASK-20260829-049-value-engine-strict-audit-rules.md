# TASK-20260829-049: Value Engine Strict Audit Rules (P0, P1, P2)

- **ID**: `TASK-20260829-049`
- **Title**: Value Engine Strict Audit Rules (P0 Cyclical 7-10Y, LATEST_FY honesty, IDC Lease DCF, Negative iROIC Penalty, TV>75% Downgrade, Bank schema clean-up, MBB normalized_roe)
- **Status**: `completed`
- **Priority**: `high`
- **Date**: `2026-08-29`

## Requirement
Thực hiện toàn diện các quy tắc kiểm toán tài chính nghiêm ngặt (Strict Audit Rules):
- **P0**:
  - [x] Implement true 7–10Y normalization for cyclicals
  - [x] LATEST_FY can never be labelled normalized/mid-cycle
  - [x] IDC Industrial Real Estate → RNAV/SOTP/lease DCF
  - [x] Sector taxonomy conflict → explicit warning/gate
  - [x] Capital allocation cannot score 15/15 when cumulative iROIC is materially negative
- **P1**:
  - [x] Robust iROIC denominator/materiality rules
  - [x] Terminal Value >75% → scenario warning
  - [x] Base TV >75% → confidence downgrade
  - [x] Add maintenance_capex_method
  - [x] D&A proxy → LOW confidence
  - [x] Bank removes Owner Earnings/CapEx schema
  - [x] Rename MBB base_growth → normalized_roe
- **P2**:
  - [x] Populate Base IV/MOS in overview
  - [x] Bear/Base/Bull IV naming instead of DCF
  - [x] Model column in overview

## Acceptance Criteria
- [x] Mọi quy tắc trong P0, P1, P2 được áp dụng triệt để trong engine backend và hiển thị frontend.
- [x] Toàn bộ unit tests và contract tests chạy pass 100%.

## Related Notes
- [TASK-20260829-048](file:///f:/workspace/shannon_allocation/docs/tasks/TASK-20260829-048-buffett-munger-engine-p0-p1-p2-enhancements.md)

## Validation Evidence
- `pytest python/portfolio/tests/test_buffett_munger_rule_engine.py python/portfolio/tests/test_value_engine.py python/portfolio/tests/test_value_engine_audit_fixes.py -v`: 17/17 tests passing.
- `npm --prefix frontend run build`: 102 modules compiled in 1.07s without errors.

## Decisions
- Ngân hàng loại bỏ hoàn toàn schema Owner Earnings / CapEx (`owner_earnings_bridge = None`), chỉ giữ lại các chỉ tiêu BVPS, ROE chuẩn hóa và Residual Income Model.
- Capital allocation penalty: Nếu iROIC lũy kế 3 năm $< -5\%$, điểm phân bổ vốn bị chặn tối đa $\le 6/15$.
- Terminal value $> 75\%$ trong kịch bản Base tự động hạ bậc confidence (HIGH $\rightarrow$ MEDIUM, MEDIUM $\rightarrow$ LOW) kèm cảnh báo.

## Result
Đã hoàn thành toàn bộ 15 yêu cầu trong danh mục P0, P1, P2. Dữ liệu và giao diện đã được kiểm thử toàn diện.
