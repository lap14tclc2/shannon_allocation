# TASK-20260828-044: Redesign Buffett–Munger Opinion Section with Laws of UX

- **ID**: `TASK-20260828-044`
- **Title**: Redesign "Nhận định Chuyên sâu Buffett–Munger" section applying Laws of UX
- **Status**: `verified`
- **Priority**: `high`
- **Date**: `2026-08-28`

## Requirement
Section "Nhận định Chuyên sâu theo Chuẩn Buffett–Munger" trên `ValuationPage.jsx` hiện là một khối văn bản dài một đoạn (`valuation_verdict` + `financial_resilience_diagnosis`) khó đọc, không tận dụng dữ liệu có cấu trúc sẵn trong `report`. Cần thiết kế lại section này đẹp, trực quan, tuân thủ các Laws of UX:

- **Chunking / Miller's Law**: tách 1 đoạn văn dài thành các nhóm dữ liệu có cấu trúc (verdict, ngành nghề, chất lượng, biên an toàn, giá trị nội tại).
- **Von Restorff Effect**: nhấn mạnh verdict chính (Đầu tư Giá trị Tuyệt vời / Hấp dẫn / ...) và con số Giá trị nội tại làm điểm nhấn thị giác.
- **Law of Proximity / Common Region**: các chỉ số liên quan nằm gần nhau trong card có ranh giới rõ ràng.
- **Law of Similarity**: đồng nhất kiểu dáng các chip chỉ số.
- **Peak–End Rule**: mở đầu bằng verdict (đỉnh cảm xúc), kết thúc bằng cấu trúc vốn & sức khỏe tài chính.
- **Aesthetic-Usability Effect**: giữ chất liệu retro "warm editorial paper" hiện có, tăng độ tinh tế.

## Context
- JSX hiện tại: `frontend/src/pages/ValuationPage.jsx` (`.valuation-analyst-opinion`, `.opinion-verdict`, `.opinion-subtext`).
- CSS: `frontend/src/valuation-page.css` (dòng 289-325) và `frontend/src/japanese-retro-theme.css` (pillar styles, status pills).
- Dữ liệu có cấu trúc sẵn trong `report`: `assessment.valuation_status`, `archetype_profile`, `quality_scorecard`, `margin_of_safety_analysis`, `scenarios.{BASE,BEAR,BULL}`, `assessment.financial_resilience_diagnosis`.
- Backend đã có `vi_labels.py` (backend); frontend cần map nhãn tiếng Việt tương đương để render chip mà không cần parse text.

## Acceptance Criteria
- [x] Section được thiết kế lại thành: (1) verdict hero nổi bật, (2) lưới 3 chip chỉ số (Ngành nghề / Chất lượng / Biên an toàn), (3) band Giá trị nội tại kịch bản Cơ sở + dải Thận trọng–Lạc quan, (4) khối Cấu trúc vốn & Sức khỏe tài chính.
- [x] Không dùng văn bản một đoạn dài; render từ dữ liệu có cấu trúc với nhãn tiếng Việt từ map dùng chung.
- [x] Có fallback an toàn khi thiếu dữ liệu (không crash, hiển thị '—').
- [x] Responsive: lưới 3 cột → 1 cột trên mobile.
- [x] `npm run build` pass.

## Constraints and Invariants
- Không đổi dữ liệu/API; chỉ đổi cách hiển thị frontend.
- Không thêm emoji; duy trì phong cách retro terminal/quant (riêng biểu tượng trong khối Sức khỏe tài chính dùng ký tự tối giản).
- Mobile (< 720px) giữ giao diện thẻ, desktop giữ phong cách hiện tại.

## Implementation Tasks
- [x] Tạo `frontend/src/lib/valuationLabels.js` chứa map nhãn tiếng Việt (verdict, archetype, quality tier, valuation model) đồng bộ `vi_labels.py`.
- [x] Viết lại JSX section `.valuation-analyst-opinion` dùng dữ liệu có cấu trúc.
- [x] Bổ sung CSS cho verdict hero, chip grid, intrinsic-value band, financial-health block.
- [x] `npm run build`.

## Related Notes
- [TASK-20260828-043](file:///f:/workspace/shannon_allocation/docs/tasks/TASK-20260828-043-pure-vietnamese-valuation-narrative.md)
- [TASK-20260828-034](file:///f:/workspace/shannon_allocation/docs/tasks/TASK-20260828-034-apply-laws-of-ux-to-qport-ui.md)
- [TASK-20260828-035](file:///f:/workspace/shannon_allocation/docs/tasks/TASK-20260828-035-comprehensive-laws-of-ux-upgrade.md)

## Validation Evidence
- `npm run build` trên `frontend/` → thành công trong 1.13s, 0 lỗi (101 modules).
- Section mới: header có verdict pill (Von Restorff), 3 chip chunked (Miller's Law), intrinsic band Cơ sở + dải Thận trọng→Lạc quan, khối Sức khỏe tài chính ở cuối (Peak–End).

## Decisions
- Render từ dữ liệu có cấu trúc thay vì parse narrative text để bền vững và không phụ thuộc chuỗi.
- Nhãn tiếng Việt dùng chung đặt ở `frontend/src/lib/valuationLabels.js`.
- Áp dụng: Miller's Law (3 chip chunk), Von Restorff (verdict pill + intrinsic band nổi bật), Law of Proximity/Common Region (các card có ranh giới), Law of Similarity (chip đồng nhất), Peak–End (verdict mở đầu, sức khỏe tài chính kết thúc).

## Result
Đã thiết kế lại section "Nhận định Chuyên sâu Buffett–Munger" thành cấu trúc trực quan: verdict pill nổi bật, lưới 3 chip chỉ số, band Giá trị nội tại Cơ sở kèm dải Thận trọng–Lạc quan, và khối Cấu trúc vốn & Sức khỏe tài chính — tuân thủ Laws of UX, giữ chất liệu retro, responsive 3→1 cột.