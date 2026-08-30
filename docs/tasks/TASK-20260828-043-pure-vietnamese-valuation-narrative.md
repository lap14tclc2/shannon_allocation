# TASK-20260828-043: Pure Vietnamese Valuation Narrative (remove technical English codes)

- **ID**: `TASK-20260828-043`
- **Title**: Thuần Việt hóa tuyệt đối Nhận định Buffett–Munger & lọc bớt thuật ngữ kỹ thuật
- **Status**: `verified`
- **Priority**: `high`
- **Date**: `2026-08-28`

## Requirement
Trang Định giá (`ValuationPage.jsx`) vẫn hiển thị nhận định chuyên sâu chứa nhiều mã kỹ thuật tiếng Anh khó hiểu với nhà đầu tư phổ thông:

```
Đánh giá Giá trị Buffett–Munger: HIGH_CONVICTION_VALUE. Hình thái kinh tế: TECHNOLOGY_SERVICES (NORMALIZED_OWNER_EARNINGS_DCF). Điểm Chất lượng Doanh nghiệp: 93/100 (EXCEPTIONAL). Biên an toàn yêu cầu: 20.0% (Thực tế Base MoS đạt +30.2%). Giá trị nội tại ước tính Base 104,879 ₫ (dải Bear-Bull: ...).
```

Cần viết lại narrative ở backend để 100% là tiếng Việt tự nhiên, loại bỏ các mã enum (HIGH_CONVICTION_VALUE, TECHNOLOGY_SERVICES, NORMALIZED_OWNER_EARNINGS_DCF, EXCEPTIONAL, MoS, Bear/Bull, Base...) và thay bằng ngôn ngữ tài chính gần gũi.

## Context
- Narrative được sinh trong `python/portfolio/value_engine/engine.py` (`val_verdict`, hàm `evaluate`).
- Các mã nguồn: `ValuationPill` (models.py), `EconomicArchetype` (archetypes.py), `QualityTier` (quality_scorer.py), `recommended_model` (archetypes.py).
- Frontend `ValuationPage.jsx` đã có bản đồ Việt hóa cho status pill (`ValuationStatusPill`), tái sử dụng các nhãn này.

## Acceptance Criteria
- [x] `val_verdict` trong `engine.py` không còn chứa bất kỳ mã enum tiếng Anh nào; toàn bộ nhãn trạng thái/archetype/tier/model được dịch sang tiếng Việt tự nhiên.
- [x] Các từ kỹ thuật "MoS", "Bear/Bull", "Base", "Normalized Owner Earnings" được thay bằng cụm tiếng Việt dễ hiểu ("Biên An Toàn", "Thận trọng/Lạc quan", "Cơ sở", "Lợi nhuận Thực chuẩn hóa").
- [x] Thêm map Việt hóa dùng chung (status, archetype, tier, model) tại vị trí phù hợp trong backend.
- [x] Có unit test kiểm tra narrative không chứa mã tiếng Anh / chứa từ khóa tiếng Việt.
- [x] `pytest` pass, `npm run build` pass.

## Constraints and Invariants
- Không đổi logic định giá; chỉ đổi cách trình bày narrative.
- Không xóa các trường dữ liệu có cấu trúc (`archetype_profile`, `quality_scorecard`, `margin_of_safety_analysis`) vì UI dùng chúng.
- Giữ mã enum trong dữ liệu máy đọc được; chỉ dịch phần text hiển thị.

## Implementation Tasks
- [x] Tạo module map dịch (hoặc dict) cho `ValuationPill`, `EconomicArchetype`, `QualityTier`, `recommended_model` trong backend.
- [x] Sửa `val_verdict` trong `engine.py` dùng các nhãn tiếng Việt.
- [x] Bổ sung test kiểm tra narrative thuần Việt.
- [x] Chạy test + build.

## Related Notes
- [TASK-20260828-042](file:///f:/workspace/shannon_allocation/docs/tasks/TASK-20260828-042-optimize-sync-and-vietnamese-valuation-ui.md)

## Validation Evidence
- `python -m pytest portfolio/tests/test_vi_labels.py portfolio/tests/test_buffett_munger_rule_engine.py` → **8 passed** (0.56s).
- `npm run build` trên `frontend/` → thành công trong 3.09s, 0 lỗi.
- Narrative mới mẫu: "Đánh giá Giá trị Buffett–Munger: Đầu tư Giá trị Tuyệt vời. Ngành nghề kinh doanh: Dịch vụ Công nghệ (Chiết khấu Lợi nhuận Thực bình quân chu kỳ). Điểm Chất lượng Doanh nghiệp: 93/100 (Xuất sắc). Biên an toàn tối thiểu cần đạt: 20.0% (thực tế kịch bản Cơ sở đạt +30.2%). Giá trị nội tại kịch bản Cơ sở: 104,879 ₫ (dải định giá Thận trọng–Lạc quan: 63,827 ₫ – 152,550 ₫)."

## Decisions
- Tái sử dụng nhãn tiếng Việt đã có ở frontend `ValuationStatusPill` để đồng nhất ngôn ngữ.
- Tạo module `vi_labels.py` dùng chung cho cả backend (narrative) và tương lai cho frontend.
- Các mã enum vẫn giữ nguyên trong dữ liệu có cấu trúc (`archetype_profile`, `quality_scorecard`, `margin_of_safety_analysis`) để UI/xuất AI tiếp tục hoạt động; chỉ text hiển thị được dịch.

## Result
Đã thuần Việt hóa 100% narrative Buffett–Munger: loại bỏ mã enum tiếng Anh (HIGH_CONVICTION_VALUE, TECHNOLOGY_SERVICES, NORMALIZED_OWNER_EARNINGS_DCF, EXCEPTIONAL) và các thuật ngữ kỹ thuật (MoS, Bear/Bull, Base, Owner Earnings, EPV, Reverse DCF) sang tiếng Việt tự nhiên, dễ hiểu cho nhà đầu tư phổ thông.