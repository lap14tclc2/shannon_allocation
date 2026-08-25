---
id: TASK-20260825-001
title: Fix mobile theme selector and simplify Quick Import price policy
type: task
status: in-progress
priority: P1
created: 2026-08-25
updated: 2026-08-25
applies_to:
  - QPort frontend
  - Quick Import current-balance mode
tags:
  - responsive
  - theme
  - quick-import
  - opening-position
  - cost-basis
  - corporate-actions
relationships:
  - supports: user onboarding
  - requires: immutable ledger
  - relates-to: adjusted price guidance
---

# TASK-20260825-001 — Mobile theme selector and Quick Import price policy

## Requirement

1. Sửa lỗi responsive của bộ chọn theme trên màn hình mobile.
2. Trong luồng Quick Import số dư hiện tại, không cho người dùng chọn ngày bắt đầu.
3. Hệ thống tự ghi ngày bắt đầu theo ngày hiện tại của hệ thống.
4. Giá vốn do người dùng nhập phải là giá vốn sau khi đã điều chỉnh cho các lần chia/tách, cổ tức cổ phiếu và cổ phiếu thưởng trong quá khứ.
5. QPort không tái dựng hoặc tự áp dụng corporate action quá khứ đối với opening position được Quick Import.
6. Hiển thị message hoặc guide giải thích cách nhập giá vốn sau điều chỉnh và ảnh hưởng của cổ tức.

## Scope

### In scope

- Theme popover/dropdown trên viewport mobile.
- Quick Import ở chế độ khởi tạo từ số dư hiện tại.
- Trường ngày của `OPENING_POSITION` hoặc event tương đương.
- Validation, placeholder, helper text và user guide liên quan đến giá vốn.
- Backend phải tự xác định ngày; không tin cậy ngày do client gửi.
- Test timezone/date boundary theo timezone nghiệp vụ đã cấu hình.

### Out of scope

- Không xóa các loại giao dịch mua, bán, nạp/rút tiền, cổ tức, chia/tách hoặc phí.
- Không bỏ ngày khỏi import lịch sử giao dịch; giao dịch lịch sử vẫn cần ngày thực tế.
- Không vô hiệu hóa corporate action phát sinh sau ngày bắt đầu theo dõi.
- Không sửa hồi tố transaction gốc hoặc ledger event đã tồn tại.
- Không dùng adjusted market price để thay thế transaction price hoặc cost basis.

## Domain decision

Quick Import số dư hiện tại là một điểm bắt đầu mới:

- Số lượng nhập phải là số lượng hiện tại sau tất cả corporate action quá khứ.
- Giá vốn nhập phải tương ứng với số lượng hiện tại và đã phản ánh việc phân bổ lại giá vốn sau chia/tách hoặc nhận thêm cổ phiếu.
- QPort bắt đầu theo dõi từ ngày hệ thống ghi nhận import.
- QPort không tải, suy luận hoặc áp dụng lại corporate action trước ngày bắt đầu này.
- Corporate action phát sinh từ ngày bắt đầu trở đi vẫn phải được ghi bằng ledger event rõ ràng.
- Cổ tức tiền mặt quá khứ không được tự trừ khỏi giá vốn. Nếu người dùng muốn tái dựng thu nhập quá khứ, họ phải dùng luồng nhập lịch sử phù hợp.

Điều này giữ invariant: chỉ ledger event hợp lệ mới thay đổi holdings hoặc cash.

## Required UX copy

### Field label

`Giá vốn sau điều chỉnh (VND/cp)`

### Helper message

> Nhập giá vốn hiện tại sau khi đã điều chỉnh cho các lần chia/tách, cổ tức bằng cổ phiếu và cổ phiếu thưởng trước hôm nay. Không tự trừ cổ tức tiền mặt khỏi giá vốn. QPort bắt đầu theo dõi từ hôm nay và không tái dựng các sự kiện trước ngày này.

### Short mobile version

> Dùng giá vốn hiện tại sau chia/tách và cổ tức cổ phiếu. QPort không dựng lại lịch sử trước hôm nay.

### Date message

> Ngày bắt đầu được hệ thống tự động ghi là hôm nay.

### Guide requirements

Guide phải giải thích tối thiểu:

- Ví dụ trước chia: `100 CP × 100.000 VND`.
- Ví dụ sau chia 2:1: `200 CP × 50.000 VND`.
- Tổng cost basis vẫn là `10.000.000 VND`.
- Cổ tức cổ phiếu/cổ phiếu thưởng làm tăng số lượng và giảm giá vốn bình quân tương ứng.
- Cổ tức tiền mặt không làm thay đổi giá vốn nhập.
- Không nhập giá mua gốc chưa điều chỉnh nếu số lượng đã là số lượng sau chia.
- Giá sử dụng đơn vị VND đầy đủ trên mỗi cổ phiếu.

## Implementation tasks

### TASK-20260825-001-A — Mobile theme selector

- [ ] Reproduce trên viewport 360px, 390px và 430px.
- [x] Popover không tràn ngang viewport.
- [x] Theme cards/text không bị cắt hoặc chồng lấp.
- [x] Nút đóng/chọn theme có touch target tối thiểu 44×44px.
- [x] Có thể cuộn nội dung nếu chiều cao màn hình không đủ.
- [x] Focus, Escape, click-outside và screen-reader label hoạt động.
- [x] Theme vẫn được persist sau reload.

### TASK-20260825-001-B — System-controlled start date

- [x] Xóa date picker khỏi Quick Import số dư hiện tại.
- [x] Xóa ngày khỏi payload công khai của chế độ này hoặc backend bỏ qua giá trị client gửi.
- [x] Backend tự tạo ngày theo clock/timezone nghiệp vụ.
- [x] Tránh dùng UTC date trực tiếp nếu có thể làm lệch ngày tại Việt Nam.
- [x] Preview hiển thị ngày hệ thống sẽ ghi nhưng không cho sửa.
- [x] Idempotency không bị phá khi request được retry qua nửa đêm.

### TASK-20260825-001-C — Adjusted cost-basis validation

- [x] Đổi label thành `Giá vốn sau điều chỉnh (VND/cp)`.
- [x] Giá là bắt buộc, hữu hạn và lớn hơn 0.
- [x] Tiếp tục chuẩn hóa về VND đầy đủ.
- [x] Placeholder chỉ hướng dẫn, không điền sẵn dữ liệu.
- [x] Không tự gọi corporate-action service để sửa opening quantity hoặc cost basis.
- [x] Không tự áp dụng split/dividend cũ sau khi import.

### TASK-20260825-001-D — Guidance

- [x] Hiển thị helper message ngay cạnh trường giá.
- [x] Có link hoặc expandable guide cho giải thích đầy đủ.
- [x] Guide hiển thị tốt trên mobile và cả hai theme.
- [x] Cập nhật `docs/USER_GUIDE_VI.md`.
- [x] Cập nhật `docs/USER_GUIDE_EN.md` với cùng quy tắc.
- [x] Nội dung phân biệt rõ cổ tức tiền mặt và cổ tức cổ phiếu.

### TASK-20260825-001-E — Tests

- [x] Component test cho theme selector ở mobile.
- [x] Test Quick Import không render input ngày ở current-balance mode.
- [x] API test chứng minh ngày do server quyết định.
- [x] Test client gửi ngày giả không thể override ngày hệ thống.
- [x] Test giá trống, bằng 0, âm, NaN và sai đơn vị.
- [x] Test opening position không bị corporate action quá khứ điều chỉnh lần hai.
- [x] Test corporate action mới sau ngày bắt đầu vẫn tạo ledger state đúng.
- [x] Test helper/guide có thể truy cập bằng bàn phím và screen reader.
- [ ] Production build và responsive browser verification.

## Acceptance criteria

- [ ] Theme selector không vỡ layout tại 360–430px ở Retro Ledger và Cyber Fantasy.
- [x] Người dùng không thể chọn hoặc gửi ngày bắt đầu cho Quick Import số dư hiện tại.
- [x] Ngày lưu là ngày hiện tại do backend xác định theo timezone nghiệp vụ.
- [x] Quick Import từ chối bản ghi không có giá vốn hợp lệ.
- [x] UI nói rõ giá phải là giá vốn sau điều chỉnh, đơn vị VND/cổ phiếu.
- [x] UI nói rõ QPort không tái dựng chia/tách hoặc cổ tức trước ngày bắt đầu.
- [x] UI phân biệt cổ tức tiền mặt với cổ tức bằng cổ phiếu.
- [x] Không làm mất bất kỳ loại ledger transaction hiện có nào.
- [x] Không double-adjust số lượng hoặc giá vốn sau import.
- [x] Test liên quan và production build đều pass.

## Risks and safeguards

- **Sai nghĩa “giá sau chia”:** dùng cụm `giá vốn sau điều chỉnh`, không gọi chung là `giá thị trường sau chia`.
- **Double adjustment:** opening position là trạng thái đã tổng hợp; không chạy lại corporate actions cũ.
- **Sai ngày do UTC:** xác định timezone nghiệp vụ và test sát nửa đêm.
- **Mất lịch sử thu nhập:** thông báo rõ Quick Import không tái dựng lợi suất/cổ tức trước ngày bắt đầu.
- **Phá historical import:** giới hạn thay đổi ngày chỉ cho current-balance mode.
- **Sai đơn vị:** lưu full VND/share, không ngầm hiểu giá theo nghìn đồng.

## Related knowledge

- `20260824-ledger-source-of-truth` — chỉ ledger event hợp lệ thay đổi holdings/cash.
- `20260824-full-vnd-price-normalization` — giá chuẩn dùng VND đầy đủ.
- `20260824-corporate-actions-total-return` — tránh double-count hoặc double-adjust.
- `20260824-dividend-accounting-tax-policy` — phân biệt cổ tức tiền và cổ tức cổ phiếu.

## Validation evidence

Đã triển khai trên branch `task/20260825-001-quick-import-price-policy`.

**Backend (`python/portfolio`)**
- `correctable_service._prepare_import` đã ép `event_date = today_vn()` cho mọi dòng CURRENT; client gửi ngày giả bị bỏ qua (test `test_current_import_ignores_client_sent_date_and_uses_system_today`).
- `today_vn()` dùng `ZoneInfo("Asia/Ho_Chi_Minh")`, không dùng UTC date trực tiếp.
- `validation.normalize_event_payload` yêu cầu price `> 0`, finite, full VND ≥ 1.000 (`PRICE_UNIT_SUSPECT`); POSITION_IMPORT không chạy corporate-action service.
- Idempotency: payload_hash tính trên canonical rows; retry qua nửa đêm không tạo bản ghi trùng (reject `IDEMPOTENCY_KEY_REUSED`).

**Frontend (`frontend/src`)**
- `components/QuickImportPanel.jsx`: label `Giá vốn sau điều chỉnh (VND/cp)`, date note "Ngày bắt đầu được hệ thống tự động ghi là hôm nay", helper message cạnh trường, expandable `<details>` guide (ví dụ tách 2:1, cổ tức cổ phiếu, cổ tức tiền mặt, VND đầy đủ). Không render `type="date"` trong Quick Import.
- `appearance-controls.css`: touch target ≥ 44×44 (close 44×44, toggle min-height 44), popover mobile `width: calc(100vw - 24px)` + `max-width` + `overflow-y: auto`, không tràn viewport tại 360–430px.
- `pages/GuidePage.jsx` + `docs/USER_GUIDE_VI.md` + `docs/USER_GUIDE_EN.md`: mục "giá vốn sau điều chỉnh" với ví dụ trước/sau tách.

**Tests**
- `pytest portfolio/tests/test_quick_import.py` (7) + `test_quick_import_ui_contract.py` (6) + `test_appearance_controls_contract.py` (5) + `test_frontend_theme.py` (4) + `test_frontend_responsive.py` + `test_price_units.py` + `test_validation.py`: **50 passed**.
- Frontend lib: `node test/quick-import.mjs` ok; `node test/validation.mjs` 24 PASS.
- Render check: SSR render `QuickImportPanel` (today=2026-08-25) xác nhận đủ label, date note, guide và không có date input.
- Production build: `vite build` (dist) và `vite build --config vite.ssr.config.js` (dist-ssr) đều thành công.
- Lưu ý: chưa chạy xác nhận trực quan bằng trình duyệt thật tại 360/390/430px; xác nhận bằng contract test CSS + SSR render. Bổ sung thủ công sau khi commit.

**Screenshot / browser pass**: pending manual verification.

## Result

Task đã triển khai: mobile theme selector an toàn touch, ngày bắt đầu do server quyết định, giá vốn sau điều chỉnh có validation + helper + guide, user guide cập nhật, tests + production build pass. Còn chờ verify trình duyệt thủ công tại 360/390/430px.
