---
id: SRC-QFD-002
title: Live Crawled Financial Data Fixtures (FPT) — Unified ProviderFact Standard
type: source
status: verified
accessed: 2026-08-25
---

# SRC-QFD-002 — Live Crawled Financial Data Fixtures (FPT)

Tài liệu nguồn này quy định **chuẩn format và cấu trúc dữ liệu thống nhất** cho toàn bộ dữ liệu crawl từ hai nguồn độc lập (CafeF và Vnstock), phục vụ đối soát, so sánh và kiểm thử không sai lệch.

---

## 1. Quy tắc cấu trúc dữ liệu thống nhất (Unified Contract Rule)

Tất cả các nguồn dữ liệu tài chính (kể cả trích xuất từ HTML table của CafeF hay qua REST API của Vnstock) **BẮT BUỘC** phải được chuẩn hóa về cùng một schema contract `qport-provider-fact/v1` tương thích hoàn toàn với [QFD-220](../notes/20260825-qfd-220-providerfact-contract.md):

```json
{
  "security_id": "sec-fpt",
  "symbol_observed": "FPT",
  "statement_type": "INCOME_STATEMENT",
  "line_item_code": "IS.REVENUE.NET",
  "label_observed": "Doanh thu thuần",
  "value_raw": "14093297397476",
  "value_normalized": 14093297397476,
  "currency": "VND",
  "scale_observed": 1,
  "period_start": "2024-01-01",
  "period_end": "2024-03-31",
  "period_type": "QUARTER",
  "fiscal_year": 2024,
  "fiscal_quarter": 1,
  "consolidation_scope": "CONSOLIDATED",
  "provider_id": "cafef_html | vnstock_api",
  "source_document_id": "<raw-source-id-or-filename>",
  "observed_at": "2026-08-25T13:57:29Z",
  "parser_version": "<adapter-version>"
}
```

### Các ràng buộc bắt buộc:
1. **Khóa định danh kinh tế đồng nhất**: Cả CafeF và Vnstock đều phải map nhãn quan sát (`label_observed`) về cùng một `line_item_code` theo taxonomy chuẩn ([QFD-260](../notes/20260825-qfd-260-taxonomy-theo-loai-hinh-doanh-nghiep.md)).
2. **Đơn vị tiền tệ cơ sở (`value_normalized`)**: Luôn quy đổi về số nguyên VNĐ (đơn vị cơ sở), loại bỏ scale để engine đối soát ([QFD-300](../notes/20260825-qfd-300-reconciliation-engine-xac-dinh.md)) so sánh trực tiếp.
3. **Bảo tồn chuỗi chứng cứ (`value_raw` & `source_document_id`)**: Giữ nguyên chuỗi ký tự thô ban đầu để phục vụ kiểm toán provenance ([QFD-230](../notes/20260825-qfd-230-provenance-va-evidence-chain.md)).

---

## 2. Danh mục Fixtures đã chuẩn hóa

| Nguồn | File JSON Chuẩn hóa (`ProviderFact`) | File Raw gốc | Số lượng facts |
|---|---|---|:---:|
| **Kênh B (CafeF Ingestion)** | [standardized_cafef_FPT_facts.json](../fixtures/standardized_cafef_FPT_facts.json) | [cafef_FPT_income_statement.html](../fixtures/cafef_FPT_income_statement.html) | 69 |
| **Kênh A (Vnstock API)** | [standardized_vnstock_FPT_facts.json](../fixtures/standardized_vnstock_FPT_facts.json) | [vnstock_FPT_financials.json](../fixtures/vnstock_FPT_financials.json) | 100 |

---

## 3. Liên kết Zettelkasten & Chỉ mục

- Chi tiết index fixtures: [README.md](../fixtures/README.md)
- Áp dụng hợp đồng: [QFD-220](../notes/20260825-qfd-220-providerfact-contract.md)
- Taxonomy chung: [QFD-260](../notes/20260825-qfd-260-taxonomy-theo-loai-hinh-doanh-nghiep.md)
- Engine đối soát dữ liệu thống nhất: [QFD-300](../notes/20260825-qfd-300-reconciliation-engine-xac-dinh.md)
