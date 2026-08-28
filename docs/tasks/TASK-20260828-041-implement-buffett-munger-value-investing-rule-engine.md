# TASK-20260828-041: Implement Buffett-Munger Value Investing Rule Engine & Specification

- **ID**: `TASK-20260828-041`
- **Title**: Implement Buffett-Munger Value Investing Rule Engine & Rule Specification (Archetype Classification, Quality Score, Sector Valuation Adapters)
- **Status**: `completed`
- **Priority**: `high`
- **Date**: `2026-08-28`

## Requirement
Thiết kế và triển khai toàn diện **Buffett–Munger Value Investing Rule Engine** cho toàn bộ thị trường chứng khoán Việt Nam theo kiến trúc 2 tầng (Universal Principles $\rightarrow$ Economic Archetypes & Sector Rules):
1. Tạo tài liệu quy chuẩn toán học & triết lý: `docs/specifications/BUFFETT_MUNGER_VALUE_ENGINE_RULES.md`.
2. Triển khai Economic Archetype Classifier (21 nhóm ngành kinh tế & overlays).
3. Triển khai Business Quality Score 100 điểm (Predictability, Moat, Return/iROIC, Financial Strength, Cash Quality, Capital Allocation, Governance).
4. Triển khai Sector-Specific Valuation Adapters (Bank RIM, Securities, Developers RNAV, Cyclicals Normalized OE, Utilities DDM/DCF, Tech/Staples Compounders, Airlines/Shipping Unvaluable/Cycle).
5. Dynamic Margin of Safety Engine (20%–50% dựa trên rủi ro ngành và chất lượng doanh nghiệp).
6. Hard Reject Rules (Circle of Competence fail, Accounting Unreliable, Unnormalizable $\rightarrow$ UNVALUABLE).
7. Final Status System: `UNVALUABLE`, `AVOID_QUALITY`, `WATCH`, `FAIRLY_VALUED`, `ATTRACTIVE`, `HIGH_CONVICTION_VALUE`.

## Context
Buffett/Munger không dùng một công thức số học duy nhất mà dùng bộ nguyên tắc tư duy kinh tế: Business dễ hiểu, lợi thế bền vững, ban lãnh đạo phân bổ vốn tốt, ít đòn bẩy, giá có biên an toàn. Mỗi nhóm hình thái kinh tế (Banks, Developers, Utilities, Cyclicals, Compounders) cần adapter định giá tương thích.

## Acceptance Criteria
- [ ] File `docs/specifications/BUFFETT_MUNGER_VALUE_ENGINE_RULES.md` được tạo đầy đủ 14 phần chi tiết.
- [ ] `python/portfolio/value_engine/` có các modules phân tách rõ:
  - `archetypes.py`: Phân loại 21 Economic Archetypes và Multi-overlays.
  - `quality_scorer.py`: Tính điểm Business Quality Score 100 điểm và Hard Reject.
  - `margin_of_safety.py`: Dynamic Required MOS Engine (20% - 50%).
  - `engine.py`: Orchestrator điều phối toàn bộ workflow từ Raw Data $\rightarrow$ Quality Gate $\rightarrow$ Classifier $\rightarrow$ Normalization $\rightarrow$ Sector Adapter $\rightarrow$ IV Range $\rightarrow$ MoS $\rightarrow$ Final Status.
- [ ] API backend và AI Export cập nhật cấu trúc mới.
- [ ] Unit tests cho toàn bộ Rule Engine pass 100%.

## Implementation Tasks
- [ ] Tạo file đặc tả `docs/specifications/BUFFETT_MUNGER_VALUE_ENGINE_RULES.md`.
- [ ] Tạo module `python/portfolio/value_engine/archetypes.py`.
- [ ] Tạo module `python/portfolio/value_engine/quality_scorer.py`.
- [ ] Tạo module `python/portfolio/value_engine/margin_of_safety.py`.
- [ ] Nâng cấp `python/portfolio/value_engine/engine.py` và `models.py`.
- [ ] Viết test suite `python/portfolio/tests/test_buffett_munger_rule_engine.py`.
- [ ] Chạy verification và hoàn tất task.

## Related Notes
- [TASK-20260828-040](file:///f:/workspace/shannon_allocation/docs/tasks/TASK-20260828-040-overhaul-valuation-engine-to-true-buffett-munger-standards.md)
- [BUFFETT_MUNGER_VALUE_ENGINE_RULES.md](file:///f:/workspace/shannon_allocation/docs/specifications/BUFFETT_MUNGER_VALUE_ENGINE_RULES.md)

## Validation Evidence
- Created `docs/specifications/BUFFETT_MUNGER_VALUE_ENGINE_RULES.md` defining 10 hard invariants, 21 economic archetypes, 100-pt Business Quality Score, sector adapters, and dynamic MOS.
- Created `python/portfolio/value_engine/archetypes.py` (21 archetypes + overlays).
- Created `python/portfolio/value_engine/quality_scorer.py` (100-pt quality score + Hard Reject system).
- Created `python/portfolio/value_engine/margin_of_safety.py` (20%-50% dynamic required MOS).
- Integrated orchestrator in `python/portfolio/value_engine/engine.py`.
- Run pytest: `pytest python/portfolio/tests/test_buffett_munger_rule_engine.py python/portfolio/tests/test_buffett_valuation_upgrade.py`: **15/15 Passed**.

## Decisions
- Phân tách dứt khoát 2 tầng: Universal Principles $\rightarrow$ Economic Archetype Classifier $\rightarrow$ Sector Valuation Adapter.
- Mọi cổ phiếu khi định giá đều được gắn với 1 trong 21 hình thái kinh tế và tính toán biên an toàn động.

## Result
Đã hoàn thành triển khai toàn bộ hệ thống Buffett-Munger Value Investing Rule Engine và tài liệu quy chuẩn đặc tả toán học chi tiết.
