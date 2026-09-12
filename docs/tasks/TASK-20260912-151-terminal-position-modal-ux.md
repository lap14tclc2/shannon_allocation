# TASK-20260912-151: Terminal Position Modal Input Colors & Symbol Suggest Search

- **ID**: TASK-20260912-151
- **Title**: Terminal Position Modal Input Colors & Symbol Suggest Search
- **Status**: completed
- **Priority**: high
- **Date**: 2026-09-12

---

## Requirement

Sửa lại màu sắc của input và sử dụng search input cho symbol trong modal quản lý danh mục Terminal:
1. Sửa màu sắc background, border, text, placeholder của tất cả input trong modal (Thêm vị thế, Chỉnh sửa vị thế, Cập nhật tiền mặt) để đồng bộ với theme (light/dark / retro washi palette), tránh hiện tượng input bị đen/tối trên nền modal sáng.
2. Tích hợp `SymbolSuggestInput` (autocomplete / searchable dropdown) cho việc chọn mã cổ phiếu khi thêm vị thế mới.

## Context

- Hiện tại `PositionForm` và `CashForm` trong `TerminalPage.jsx` sử dụng hardcoded `var(--input-bg, #0d1117)`, gây ra màu nền đen trên nền modal màu kem sáng, text và placeholder bị chìm/khó đọc.
- Hệ thống đã có sẵn component `SymbolSuggestInput` hỗ trợ tìm kiếm ticker, tên công ty, sàn giao dịch từ API `lookupSecurities`.
- Tái sử dụng `SymbolSuggestInput` và đồng bộ input styling theo token theme chuẩn (`--input`, `--text`, `--border-strong`, `--muted`).

## Acceptance Criteria

- [x] Input trong modal có màu nền, màu viền và màu chữ hài hòa với modal panel trên cả light mode và dark mode.
- [x] Placeholder text hiển thị rõ ràng, dễ đọc.
- [x] Symbol input trong modal "Thêm vị thế" sử dụng `SymbolSuggestInput` có gợi ý tìm kiếm realtime.
- [x] `holdingSymbols` được truyền vào `SymbolSuggestInput` để đánh dấu các mã đã có trong danh mục.
- [x] Modal "Chỉnh sửa vị thế" và "Cập nhật tiền mặt" cũng được cập nhật màu sắc input chuẩn.
- [x] Build & tests tiếp tục pass mà không phát sinh lỗi regression.

## Constraints and Invariants

- Tái sử dụng `SymbolSuggestInput.jsx` có sẵn, không viết lại search component mới.
- Giữ nguyên toàn bộ logic validation và CRUD positions / cash đã xây dựng ở TASK-150.

## Implementation Tasks

- [x] Import và tích hợp `SymbolSuggestInput` vào `PositionForm` trong `TerminalPage.jsx`
- [x] Cập nhật style cho các input trong `PositionForm`, `CashForm`, `Modal` trong `TerminalPage.jsx`
- [x] Cập nhật CSS cho `.symbol-suggest-input` trong `japanese-retro-theme.css` để đảm bảo hiển thị đồng nhất
- [x] Kiểm thử build vite frontend và 23 backend tests

## Decisions

1. Use theme CSS tokens `var(--input, var(--panel-subtle, #ffffff))` and `var(--text, #201d18)` for clean theme compatibility.
2. Integrate `SymbolSuggestInput` with `holdingSymbols` prop populated from current portfolio positions.

## Validation Evidence

1. Frontend Vite production build:
```text
> qport-frontend@2.0.0-vercel build
> vite build
✓ 114 modules transformed.
dist/index.html                   1.86 kB
dist/assets/index-B4V80acv.css  260.44 kB
dist/assets/index-BbsRtcJn.js   693.84 kB
✓ built in 1.54s
```

2. Backend unit tests:
```text
python\portfolio\tests\test_terminal_portfolio_positions.py ............ [ 52%]
...........                                                              [100%]
============================= 23 passed in 9.86s ==============================
```

## Result

- Input styling trong các modal của Terminal (`Thêm vị thế`, `Chỉnh sửa vị thế`, `Cập nhật Tiền mặt`) chuyển sang sử dụng theme tokens `var(--input, var(--panel-subtle, #ffffff))` và viền `var(--border-strong, var(--border, #9c927f))` với text `var(--text, #201d18)`, giải quyết triệt để lỗi nền đen trên modal sáng.
- Mã cổ phiếu khi thêm mới chuyển sang dùng `SymbolSuggestInput` với chức năng gợi ý tìm kiếm realtime theo tên mã/công ty/sàn và gắn nhãn "Đang nắm giữ" nếu mã đã có trong danh mục.
