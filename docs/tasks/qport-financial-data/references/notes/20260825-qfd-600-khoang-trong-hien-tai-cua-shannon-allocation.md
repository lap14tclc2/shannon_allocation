---
id: QFD-600
title: "Khoảng trống hiện tại của Shannon Allocation"
type: observation
status: verified
created: 2026-08-25
updated: 2026-08-25
sources:
  - ../sources/source-qport-financial-data-design.md
---

# QFD-600 — Khoảng trống hiện tại của Shannon Allocation

## Claim

Qua rà soát repository:

- `python/portfolio/market_data.py` đang dùng Vnstock cho OHLCV và VNDIRECT fallback.
- `python/portfolio/vnstock_isolated.py` có các task probe, OHLCV, events và company info; chưa có task financial statements.
- `python/portfolio/security_reference.py` mới dùng company info cho ISIN/sàn/tên/lot size.
- `python/portfolio/dividends.py` là pipeline sự kiện/cổ tức đa nguồn; không phải pipeline BCTC.
- Test worker hiện thiên về fake worker; chưa chứng minh live integration của financial statements.

Kết luận: nên mở rộng theo connector boundary mới, không nhồi parser BCTC trực tiếp vào `market_data.py` hoặc `dividends.py`.

## Relationships

- supports: [QFD-100](./20260825-qfd-100-he-a-api-ingestion.md)
- supports: [QFD-140](./20260825-qfd-140-khong-tron-domain-su-kien-voi-bctc.md)
- supports: [QFD-610](./20260825-qfd-610-roadmap-trien-khai.md)
