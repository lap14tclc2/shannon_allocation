---
id: TASK-20260917-171
title: Fix ReferenceError formatDecision is not defined in aiExport.js
status: completed
priority: high
date: 2026-09-17
---

# TASK-20260917-171: Fix ReferenceError formatDecision is not defined in aiExport.js

## Requirement
Khi người dùng bấm xuất báo cáo cho AI (`exportMungerAnalysisToAiMarkdown`), hệ thống báo lỗi JavaScript: `ReferenceError: formatDecision is not defined`.
Cần import `formatDecision` từ `../utils/vietnameseSemantics.js` vào `frontend/src/lib/aiExport.js`.

## Context
Trong `frontend/src/lib/aiExport.js`, dòng 635 gọi `formatDecision(decision.state)`, nhưng tại đầu file (dòng 13), `formatDecision` chưa được import từ `../utils/vietnameseSemantics.js`.

## Acceptance Criteria
- [x] Import `formatDecision` trong `frontend/src/lib/aiExport.js`.
- [x] Xuất báo cáo AI không bị crash lỗi `formatDecision is not defined`.
- [x] Chạy frontend tests / linter / verify build nếu có.

## Constraints and Invariants
- Giữ nguyên các hàm import khác.
- Phân tách đúng quy tắc surgical changes.

## Implementation Tasks
- [x] Thêm `formatDecision` vào danh sách import từ `../utils/vietnameseSemantics.js` trong `frontend/src/lib/aiExport.js`.
- [x] Kiểm tra thêm nếu còn hàm format nào trong `vietnameseSemantics.js` chưa import mà được dùng trong `aiExport.js`.

## Related Notes
- [BusinessPage.jsx](file:///c:/workspace/shannon_allocation/frontend/src/pages/BusinessPage.jsx)
- [aiExport.js](file:///c:/workspace/shannon_allocation/frontend/src/lib/aiExport.js)

## Validation Evidence
- Vite build passed cleanly: `npm run build` executed with exit code 0 (`built in 3.79s`).
- `formatDecision` properly imported on line 13 of `frontend/src/lib/aiExport.js`.

## Decisions
- Thêm `formatDecision` vào named imports từ `../utils/vietnameseSemantics.js` trong `frontend/src/lib/aiExport.js`.

## Result
Đã khắc phục hoàn tất lỗi `formatDecision is not defined` khi xuất báo cáo AI.

