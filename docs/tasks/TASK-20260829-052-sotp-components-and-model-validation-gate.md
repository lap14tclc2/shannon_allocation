# TASK-20260829-052: SOTP Components, Lease Cashflow DCF & Model Validation Gate

- **ID**: `TASK-20260829-052`
- **Title**: SOTP Components, Lease Cashflow DCF Parameters, Model Validation Gate & Strict Normalization
- **Status**: `completed`
- **Priority**: `high`
- **Date**: `2026-08-29`

## Requirement
Thực hiện toàn diện các tiêu chí:
- **P0 — Model Execution**:
  - [x] SOTP must expose actual `components[]`
  - [x] SOTP value = `sum(component values) - liabilities`
  - [x] No generic DCF may masquerade as SOTP
  - [x] `LEASE_CASHFLOW_DCF` parameter structure (remaining land, lease rate, schedule, concession end, infra capex, timeline)
  - [x] Finite concession cannot automatically use perpetual TV ($TV = 0$)
  - [x] `MODEL_VALIDATION_GATE` checks (recommended model, actual model, required inputs, formula family, forbidden formula family)
  - [x] Invalid model $\rightarrow$ no definitive IV/verdict
- **P0 — Normalization**:
  - [x] DGC/HPG cyclical normalization = 7–10Y
  - [x] `LATEST_FY` never called normalized/mid-cycle
  - [x] `current_owner_earnings` and `normalized_owner_earnings` explicitly separated
- **P1**:
  - [x] Proxy maintenance capex $\rightarrow$ LOW confidence
  - [x] Segment-based capital-allocation evidence
  - [x] GVR 15/15 requires segment-level support
  - [x] `quality_status` separated from `valuation_status`
  - [x] `model_status` added (`MODEL_VERIFIED`, `MODEL_INCOMPLETE`, `MODEL_PENDING`, `FALLBACK_MODEL`)
- **P2**:
  - [x] Overview Base IV/MOS populated
  - [x] Bear/Bull DCF $\rightarrow$ Bear/Base/Bull IV
  - [x] Show Archetype + Model + Model Status

## Acceptance Criteria
- [x] Mọi quy tắc trong spec được áp dụng và xác minh qua pytest và frontend build.

## Related Notes
- [TASK-20260829-051](file:///f:/workspace/shannon_allocation/docs/tasks/TASK-20260829-051-strict-model-eligibility-and-valuation-pipeline.md)

## Validation Evidence
- `pytest python/portfolio/tests/test_buffett_munger_rule_engine.py python/portfolio/tests/test_value_engine.py python/portfolio/tests/test_value_engine_audit_fixes.py python/portfolio/tests/test_vi_labels.py python/portfolio/tests/test_valuation_page_contract.py -v`: 28/28 tests passed (100%).
- `npm --prefix frontend run build`: 102 modules compiled in 1.09s without errors.

## Decisions
- Tạo module `SOTPValuationModel` (`sotp_valuation.py`) bóc tách mảng `components[]` thực tế (Cao su lõi, Vườn cây NAV, Đất KCN RNAV) và khấu trừ Nợ ròng (`Net Debt`).
- Tích hợp `MODEL_VALIDATION_GATE` kiểm soát tính hợp lệ của mô hình thực thi so với phân loại kinh tế, nếu không khớp sẽ gán `model_status = MODEL_INCOMPLETE` và không phát sinh verdict định giá sai lệch.
- Tách biệt rõ ràng `current_owner_earnings` (năm gần nhất) và `normalized_owner_earnings` (chu kỳ 10 năm) trong `OwnerEarningsBridge`.
- Bổ sung `Trạng thái Mô hình` trên Bảng Tổng quan Định giá.

## Result
Đã hoàn thành toàn diện việc thực thi và kiểm định các tiêu chí nghiêm ngặt về SOTP Components, Lease Cashflow DCF, Model Validation Gate, và Normalization theo chuẩn mực Buffett–Munger.
