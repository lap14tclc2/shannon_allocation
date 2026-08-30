# TASK-20260829-063: Refactor Methodology Section into Visual 4-Step Value Pipeline

- **ID**: `TASK-20260829-063`
- **Title**: Refactor Valuation Methodology Section into Intuitive Visual Pipeline Infographic
- **Status**: completed
- **Priority**: medium
- **Date**: 2026-08-29
- **Assignee**: AI Agent & Frontend Contributor

---

## Requirement
Transform the text-heavy 4-box `MethodologyGuide` in `ValuationPage.jsx` and `valuation-page.css` into an intuitive, visually structured 4-step pipeline infographic:
1. Replace walls of text with crisp visual micro-steps, flow arrows, formula chips, and badge tags.
2. Step 1: **Phân loại 40 Archetypes & Chuẩn hóa Chu kỳ 10 năm** (`BCTC 10 Năm` → `Mid-Cycle Median`).
3. Step 2: **Bóc tách Dòng tiền Thực** (`LNST + D&A − Maintenance CapEx` & chuyên biệt Ngân hàng/BĐS KCN).
4. Step 3: **Định tuyến Mô hình 3 Kịch bản** (`Bear IV` ➔ `Base IV` ➔ `Bull IV`).
5. Step 4: **Biên An Toàn Động 20%–50% & 16 Lớp Rủi ro** (Nguyên tắc bảo vệ vốn Buffett–Munger).
6. Add visual pipeline connector lines, badges, and intuitive formula highlights.

---

## Acceptance Criteria
- [x] Methodology section uses a visual 4-step pipeline layout with step indicators (`BƯỚC 1` .. `BƯỚC 4`), icons, and visual flow arrows.
- [x] Dense text is replaced with concise bullets, key formula badges, and archetype tags.
- [x] Preserves collapsible accordion container with clean summary toggle.
- [x] CSS is responsive and stacks cleanly on mobile (<720px) and tablet (<1024px).
- [x] `npm run build` succeeds with 0 errors.

---

## Implementation Tasks
- [x] Update `MethodologyGuide` in `frontend/src/pages/ValuationPage.jsx`.
- [x] Add pipeline, step cards, formula chips, and connector styles in `frontend/src/valuation-page.css`.
- [x] Test build and verify responsive layout.

---

## Validation Evidence
- `npm run build`: Vite build production bundle succeeded with 0 errors (dist built in 1.07s).

---

## Result
- Methodology section transformed from dense paragraphs into a clear, visual 4-step pipeline infographic with formulas, flow arrows, scenario pills, and Buffett-Munger core quote.

