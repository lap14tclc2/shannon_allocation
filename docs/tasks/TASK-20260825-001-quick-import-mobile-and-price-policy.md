---
id: TASK-20260825-001
title: Fix mobile theme selector and simplify Quick Import price policy
type: task
status: ready
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
- [ ] Popover không tràn ngang viewport.
- [ ] Theme cards/text không bị cắt hoặc chồng lấp.
- [ ] Nút đóng/chọn theme có touch target tối thiểu 44×44px.
- [ ] Có thể cuộn nội dung nếu chiều cao màn hình không đủ.
- [ ] Focus, Escape, click-outside và screen-reader label hoạt động.
- [ ] Theme vẫn được persist sau reload.

### TASK-20260825-001-B — System-controlled start date

- [ ] Xóa date picker khỏi Quick Import số dư hiện tại.
- [ ] Xóa ngày khỏi payload công khai của chế độ này hoặc backend bỏ qua giá trị client gửi.
- [ ] Backend tự tạo ngày theo clock/timezone nghiệp vụ.
- [ ] Tránh dùng UTC date trực tiếp nếu có thể làm lệch ngày tại Việt Nam.
- [ ] Preview hiển thị ngày hệ thống sẽ ghi nhưng không cho sửa.
- [ ] Idempotency không bị phá khi request được retry qua nửa đêm.

### TASK-20260825-001-C — Adjusted cost-basis validation

- [ ] Đổi label thành `Giá vốn sau điều chỉnh (VND/cp)`.
- [ ] Giá là bắt buộc, hữu hạn và lớn hơn 0.
- [ ] Tiếp tục chuẩn hóa về VND đầy đủ.
- [ ] Placeholder chỉ hướng dẫn, không điền sẵn dữ liệu.
- [ ] Không tự gọi corporate-action service để sửa opening quantity hoặc cost basis.
- [ ] Không tự áp dụng split/dividend cũ sau khi import.

### TASK-20260825-001-D — Guidance

- [ ] Hiển thị helper message ngay cạnh trường giá.
- [ ] Có link hoặc expandable guide cho giải thích đầy đủ.
- [ ] Guide hiển thị tốt trên mobile và cả hai theme.
- [ ] Cập nhật `docs/USER_GUIDE_VI.md`.
- [ ] Cập nhật `docs/USER_GUIDE_EN.md` với cùng quy tắc.
- [ ] Nội dung phân biệt rõ cổ tức tiền mặt và cổ tức cổ phiếu.

### TASK-20260825-001-E — Tests

- [ ] Component test cho theme selector ở mobile.
- [ ] Test Quick Import không render input ngày ở current-balance mode.
- [ ] API test chứng minh ngày do server quyết định.
- [ ] Test client gửi ngày giả không thể override ngày hệ thống.
- [ ] Test giá trống, bằng 0, âm, NaN và sai đơn vị.
- [ ] Test opening position không bị corporate action quá khứ điều chỉnh lần hai.
- [ ] Test corporate action mới sau ngày bắt đầu vẫn tạo ledger state đúng.
- [ ] Test helper/guide có thể truy cập bằng bàn phím và screen reader.
- [ ] Production build và responsive browser verification.

## Acceptance criteria

- [ ] Theme selector không vỡ layout tại 360–430px ở Retro Ledger và Cyber Fantasy.
- [ ] Người dùng không thể chọn hoặc gửi ngày bắt đầu cho Quick Import số dư hiện tại.
- [ ] Ngày lưu là ngày hiện tại do backend xác định theo timezone nghiệp vụ.
- [ ] Quick Import từ chối bản ghi không có giá vốn hợp lệ.
- [ ] UI nói rõ giá phải là giá vốn sau điều chỉnh, đơn vị VND/cổ phiếu.
- [ ] UI nói rõ QPort không tái dựng chia/tách hoặc cổ tức trước ngày bắt đầu.
- [ ] UI phân biệt cổ tức tiền mặt với cổ tức bằng cổ phiếu.
- [ ] Không làm mất bất kỳ loại ledger transaction hiện có nào.
- [ ] Không double-adjust số lượng hoặc giá vốn sau import.
- [ ] Test liên quan và production build đều pass.

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

Chưa triển khai. Điền kết quả test, build, responsive screenshots và commit/PR khi bắt đầu code.

## Result

Task đã sẵn sàng để triển khai. Chưa có source code nào được thay đổi.
