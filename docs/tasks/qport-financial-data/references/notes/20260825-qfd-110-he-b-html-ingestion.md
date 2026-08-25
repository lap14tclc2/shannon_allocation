---
id: QFD-110
title: "Hệ B: HTML ingestion"
type: decision
status: draft
created: 2026-08-25
updated: 2026-08-25
sources:
  - ../sources/source-qport-financial-data-design.md
---

# QFD-110 — Hệ B: HTML ingestion

## Claim

Hệ B crawl HTML công khai, trước mắt là CafeF. Đây là hệ độc lập về transport và parser để có giá trị cross-check thực sự.

### Nguyên tắc crawler

- Chỉ truy cập trang công khai, không đăng nhập, không CAPTCHA bypass.
- Tôn trọng robots.txt, điều khoản sử dụng, rate limit và chính sách cache.
- Lưu HTML snapshot hoặc phần HTML liên quan cùng hash trước khi parse.
- Parser phải dựa vào semantic label/table header; tránh selector phụ thuộc vị trí tuyệt đối.
- Mỗi parser có fixture HTML và golden test.
- Phát hiện trang “soft error” trả HTTP 200 nhưng nội dung lỗi/chặn.

### Contract tối thiểu

```python
class FinancialHtmlProvider(Protocol):
    provider_id: str

    def discover(self, symbol: str) -> list[SourceDocument]: ...
    def fetch(self, document: SourceDocument) -> RawEnvelope: ...
    def parse(self, envelope: RawEnvelope) -> list[ProviderFact]: ...
```

### Khi nào chạy hệ B

- Đối chiếu theo sampling định kỳ.
- Hệ A trả `NO_DATA`, lỗi schema hoặc thiếu kỳ.
- Giá trị hệ A vượt rule kiểm tra hoặc thay đổi bất thường.
- Kỳ mới được công bố và có giá trị cao đối với quyết định đầu tư.

## Relationships

- supports: [QFD-020](./20260825-qfd-020-ba-vai-tro-nguon-du-lieu.md)
- supports: [QFD-120](./20260825-qfd-120-nguon-evidence-chinh-thuc.md)
- supports: [QFD-130](./20260825-qfd-130-danh-gia-cac-nguon-ngoai-mvp.md)
- supports: [QFD-400](./20260825-qfd-400-kien-truc-dich-vu.md)
- supports: [QFD-440](./20260825-qfd-440-phap-ly-dao-duc-va-an-toan-crawl.md)
