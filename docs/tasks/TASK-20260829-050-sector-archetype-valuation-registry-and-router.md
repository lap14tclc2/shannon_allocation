# TASK-20260829-050: Comprehensive Sector/Archetype Valuation Registry & Model Router

- **ID**: `TASK-20260829-050`
- **Title**: Comprehensive Sector/Archetype Valuation Registry & Model Router for Vietnam Stock Market
- **Status**: `completed`
- **Priority**: `high`
- **Date**: `2026-08-29`

## Requirement
Xây dựng Sector/Archetype Valuation Registry hoàn chỉnh cho toàn bộ thị trường chứng khoán Việt Nam:
1. Universal Economic Archetypes (40 archetypes chuẩn hóa).
2. Universal Overlays (16 overlays kinh tế: chu kỳ, thâm dụng vốn, nhạy cảm hàng hóa, concession, dự án, v.v.).
3. Model Eligibility Gate & Forbidden Models Check.
4. Valuation Model Router:
   - `COMMERCIAL_BANK` / Finance $\rightarrow$ `RESIDUAL_INCOME_MODEL`.
   - `INDUSTRIAL_REAL_ESTATE` (IDC, SZC, BCM...) $\rightarrow$ `LEASE_CASHFLOW_DCF` / `RNAV`.
   - `CONCESSION_INFRASTRUCTURE` / `ENERGY_INFRASTRUCTURE` (GAS, BOT, Thủy điện) $\rightarrow$ `CONCESSION_DCF` (Finite-life).
   - `BASIC_MATERIALS_METALS` (HPG) / `COMMODITY_CHEMICAL` $\rightarrow$ 7–10Y `MID_CYCLE_MEDIAN`.
   - `CONSUMER_STAPLES` (VNM) / `TECHNOLOGY_SERVICES` (FPT) $\rightarrow$ Compounder `NORMALIZED_OWNER_EARNINGS_DCF` + `EPV`.
   - `RUBBER_PLANTATION` / Conglomerate (GVR) $\rightarrow$ Plantation NAV + SOTP.
5. Pending states & classification conflict warnings.

## Acceptance Criteria
- [x] 40 Archetypes và 16 Overlays được khai báo đầy đủ trong `archetypes.py` cùng `ARCHETYPE_REGISTRY`.
- [x] IDC và nhóm BĐS KCN được định tuyến sang `LEASE_CASHFLOW_DCF` thay vì generic DCF.
- [x] Các mô hình chuyên biệt được kiểm thử với các case thực tế (IDC, HPG, FPT, MBB, GAS, VNM, GVR).
- [x] Báo cáo hiển thị đúng nhãn tiếng Việt thuần và các chỉ số đặc thù của từng archetype.
- [x] Tất cả unit tests và build frontend hoàn thành không lỗi.

## Related Notes
- [TASK-20260829-048](file:///f:/workspace/shannon_allocation/docs/tasks/TASK-20260829-048-buffett-munger-engine-p0-p1-p2-enhancements.md)
- [TASK-20260829-049](file:///f:/workspace/shannon_allocation/docs/tasks/TASK-20260829-049-value-engine-strict-audit-rules.md)

## Validation Evidence
- `pytest python/portfolio/tests/test_buffett_munger_rule_engine.py python/portfolio/tests/test_value_engine.py python/portfolio/tests/test_value_engine_audit_fixes.py -v`: 19/19 tests passed (100%).
- `npm --prefix frontend run build`: 102 modules compiled in 1.03s without errors.

## Decisions
- Hoàn thiện toàn bộ registry 40 Archetypes và 16 Overlays trong `archetypes.py` cùng bảng tra cứu `ARCHETYPE_REGISTRY`.
- Thêm `IndustrialRealEstateValuationModel` (`real_estate_valuation.py`) chuyên biệt cho BĐS KCN (IDC, BCM, SZC, KBC...) dựa trên dòng tiền hợp đồng thuê đất, doanh thu chưa thực hiện và khấu trừ CIP dở dang.
- Thêm `ConcessionValuationModel` (`concession_valuation.py`) chuyên biệt cho hạ tầng độc quyền và tiện ích có thời hạn (GAS, POW, BOT) với Terminal Value = 0 (Finite-life).
- Đồng bộ bảng từ điển tiếng Việt thuần trong `vi_labels.py` và `valuationLabels.js`.

## Result
Đã hoàn thành toàn diện việc mở rộng Sector/Archetype Valuation Registry & Model Router cho toàn bộ thị trường chứng khoán Việt Nam. Dữ liệu và routing mô hình được xác minh qua 19 tests tự động.
