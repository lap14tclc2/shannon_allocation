---
id: QFD-100
title: "Hệ A: API ingestion"
type: decision
status: draft
created: 2026-08-25
updated: 2026-08-25
sources:
  - ../sources/source-qport-financial-data-design.md
---

# QFD-100 — Hệ A: API ingestion

## Claim

Hệ A sử dụng connector API, ưu tiên capability fundamental của Vnstock ở chế độ guest/public không yêu cầu người dùng đăng nhập. Không coi endpoint nội bộ của website là API ổn định nếu không có contract công khai.

### Trách nhiệm

- Probe capability trước khi chạy batch.
- Lấy company profile và ba báo cáo tài chính.
- Ghi nguyên payload trước khi transform.
- Tôn trọng quota, timeout, backoff và cache.
- Không để SDK/vendor model rò vào domain model của QPort.

### Contract tối thiểu của adapter

```python
class FinancialApiProvider(Protocol):
    provider_id: str

    def probe(self) -> ProviderHealth: ...
    def get_company(self, symbol: str) -> RawEnvelope: ...
    def get_statements(
        self,
        symbol: str,
        statement_type: str,
        period_type: str,
        start_period: str | None = None,
    ) -> list[RawEnvelope]: ...
```

`RawEnvelope` MUST chứa `provider_id`, `request_fingerprint`, `requested_at`, `received_at`, `http_status/sdk_status`, `payload`, `payload_hash`, `connector_version`.

### Failure semantics

- `RATE_LIMITED`: retry theo `Retry-After` hoặc exponential backoff có jitter.
- `AUTH_REQUIRED`: connector guest bị thay đổi; ngừng connector, không tự tìm cách né auth.
- `SCHEMA_CHANGED`: lưu payload, quarantine transform, phát cảnh báo.
- `NO_DATA`: kết quả hợp lệ nhưng không có kỳ yêu cầu; cho phép hệ B thử fallback.
- `TRANSIENT_ERROR`: retry có giới hạn.

## Relationships

- supports: [QFD-020](./20260825-qfd-020-ba-vai-tro-nguon-du-lieu.md)
- supports: [QFD-130](./20260825-qfd-130-danh-gia-cac-nguon-ngoai-mvp.md)
- supports: [QFD-400](./20260825-qfd-400-kien-truc-dich-vu.md)
- supports: [QFD-410](./20260825-qfd-410-connector-boundary-va-provider-registry.md)
