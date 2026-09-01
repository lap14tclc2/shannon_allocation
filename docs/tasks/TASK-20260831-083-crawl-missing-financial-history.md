# TASK-20260831-083: Handle Crawl Missing Financial History (Full-cycle backfill)

**status:** in-progress
**date:** 2026-08-31
**priority:** high

## Requirement

Bổ sung dữ liệu BCTC lịch sử còn thiếu (7–10 năm) để các mã ngành hàng hóa chu kỳ (DGC, HPG, BCC, HT1, BSR...) đạt chuẩn **full-cycle normalization** trong valuation engine. Hiện các mã này bị `MODEL_INCOMPLETE` / `MODEL_PARTIAL` vì finance DB chỉ có 1–4 năm thay vì 7–10 năm.

Feedback 03:56: "7–10Y full-cycle normalization vẫn chưa có thật — 0 mã đạt full-cycle".

## Context

- Nguồn TCBS (`apiextaws.tcbs.com.vn/tcanalysis/v1/finance`) trước đây không auth, giờ bị WAF (Cloudflare) + yêu cầu token.
- Đã xác nhận: dùng `curl_cffi` `impersonate="chrome120"` **vượt được Cloudflare**; URL đúng `?yearly=1&isAll=true`; headers đúng.
- Token JWT TCInvest cung cấp: token đầy đủ, chưa hết hạn, chữ ký 256 bytes hợp lệ, NHƯNG server trả `RSA signature did not verify` — token ký bằng key không khớp public key hiện tại. **Không sửa được bằng code.**
- CafeF: HTTP 200 nhưng bảng BCTC render bằng JS — HTML tĩnh không có số liệu.
- vnstock Legacy: `cannot import Reference` (hỏng); cần vnstock3 / `vnstock_data` (sponsor).
- VSDC: đã implement provider cho corporate actions (task 082 addendum 6) — nguồn chính thức public hoạt động.

## Acceptance Criteria

- [ ] Có cơ chế crawl/backfill 7–10 năm BCTC cho một symbol (income/balance/cash flow) đổ vào `canonical_facts`.
- [ ] Crawler dùng `curl_cffi` impersonation + token từ `TCBS_BEARER_TOKEN` (đã tích hợp `_tcbs_fetch_json`, `yearly=1`).
- [ ] Sau khi crawl đủ, mã chu kỳ (DGC...) chuyển từ `MODEL_INCOMPLETE/PARTIAL` sang được chuẩn hóa mid-cycle (>=7 năm → `MODEL_VERIFIED` hoặc ít nhất không còn block vì thiếu lịch sử).
- [ ] Token hợp lệ hoặc nguồn thay thế (official-document PDF) sẵn sàng để chạy production.
- [ ] Ghi Validation Evidence (số năm/normalization_method trước/sau).

## Constraints and Invariants

- Không commit token/secret vào repo; token chỉ qua env `TCBS_BEARER_TOKEN`.
- Không fabricate dữ liệu tài chính khi nguồn không trả về.
- Bất biến sổ cái Buy & Hold không đổi.
- Ưu tiên nguồn free/public/no-auth (user-test.md): TCBS developer key / official-document thay vì CafeF/Vietstock lâu dài.

## Implementation Tasks

- [x] Phân tích nguồn: TCBS WAF + token, CafeF JS, vnstock hỏng, VSDC OK.
- [x] `finance_catalog.py`: thêm `_tcbs_fetch_json` (curl_cffi impersonate + retry/backoff jitter cho 429), dùng trong `_fetch_tcbs_history`.
- [x] Sửa `_tcbs_document_url`: `yearly=0` → `yearly=1&isAll=true`.
- [x] Sửa `_tcbs_document_headers`: thêm `Accept`.
- [x] Thêm `random` import cho backoff jitter.
- [x] Xác minh curl_cffi vượt Cloudflare (từ 403 "Just a moment" → JSON API).
- [x] Endpoint user-facing `POST /api/portfolio/valuation/{symbol}/crawl` (gọi `crawl_symbol` → TCBS) + helper `crawlValuationHistory` (api.js).
- [x] UI: nút "⬇ Cập nhật dữ liệu TCBS" trên valuation overlay (header, chỉ khi report chưa MODEL_VERIFIED / có missing_data) và trên card section-2 screener.
- [x] Popup nhập TCBS Bearer token (`TcbsTokenPrompt`) khi crawl 401/403 `TCBS_AUTH_REQUIRED` — kèm section chi tiết lỗi; token lưu per-user (`app_meta.tcbs_bearer_token`) và thread qua `crawl_symbol`/`_fetch_tcbs_history`.
- [x] **Disable trên Vercel**: `_crawl_enabled()` (cần `QPORT_FINANCE_RUNTIME=local|worker` và không `VERCEL`); trả `crawl_enabled` trong response valuation+screener; frontend ẩn nút crawl trên Vercel; endpoint trả 403 `CRAWL_DISABLED_ON_VERCEL` nếu không enabled.
- [x] **Dữ liệu crawl lưu vào DB**: `crawl_symbol` → `_save_document` (bảng `documents`) → `_canonicalize_document` → `canonical_facts` (finance DB) — valuation đọc từ DB.
- [ ] Có token hợp lệ (developer key / token mới) trên server để crawl chạy được.
- [ ] Chạy crawl_symbol cho DGC và các mã chu kỳ; verify `canonical_facts` đủ 7–10 năm.
- [ ] Chạy valuation lại DGC → xác nhận full-cycle normalization.

## Related Notes

- docs/tasks/TASK-20260831-082 (feedback rounds: full-cycle gap #6).
- docs/user-test.md (official-document-first ingestion; bỏ TCBS vì auth).
- docs/feedback.txt (03:56: full-cycle normalization là technical debt lớn nhất).

## Validation Evidence

```
# curl_cffi impersonate=chrome120 vượt Cloudflare (trước: 403 "Just a moment")
status 401 -> {"status":401,"message":"*RSA signature did not verify*"}   # token key mismatch (server-side)

# token cung cấp
exp 2026-08-31T16:28:24Z (chưa hết hạn), sig 342 ký tự / 256 bytes (hợp lệ hình thức)
-> server từ chối chữ ký -> cần token/credential hợp lệ mới

# VSDC provider (nguồn official hoạt động) — task 082 addendum 6
test_vsdc.py: 6 passed; live SBT -> security_id 707, phân loại CASH/STOCK_DIVIDEND/RIGHTS_ISSUE đúng.

# Test suite (không regression từ curl_cffi/yearly=1)
56 passed (vsdc + corporate_actions + audit_integrity + vi_labels); finance_catalog ast OK
```

## Decisions

- TCBS crawl hiện yêu cầu `TCBS_BEARER_TOKEN` (require_token=True) — vì endpoint không còn public.
- Giữ fallback `_url_json` khi `curl_cffi` không cài (sẽ fail WAF, nhưng không crash).
- Token JWT TCInvest không đủ quyền xác thực chữ ký → cần developer API key hoặc token mới; nếu không, chuyển hẳn sang official-document PDF ingestion (hướng bền vững theo user-test.md).

## Result

Hạ tầng crawl đã sẵn sàng (curl_cffi bypass Cloudflare + yearly=1 + headers đúng); chưa chạy được production vì thiếu credential hợp lệ. Bước kế tiếp: lấy developer API key TCBS hoặc token mới; nếu không có, implement official-document PDF parser (HNX/HOSE/SSC).

## Addendum 7 — user-test.md: full-cycle evidence + historical anomaly detector

Theo `docs/user-test.md` (audit DGC, MODEL_VERIFIED nhưng thiếu evidence full-cycle + anomaly FY2017):

- **Expose full-cycle normalization evidence**: AI export (`screenerStockDetail`/`downloadSymbolAIExport`) xuất `normalization_method`, `normalization_years`, `cycle_window`, `current_owner_earnings`, `normalized_owner_earnings`, `mid_cycle_margin` từ `owner_earnings_bridge` — `MODEL_VERIFIED` của công ty chu kỳ phải chứng minh `normalization_years >= 7`.
- **Historical anomaly detector**: `detect_financial_anomalies(financial_history)` (`engine.py`) flag revenue/LNST/CFO nhảy ≥ +100% hoặc ≤ -60% giữa các năm → `DATA_ANOMALY`/`SUSPICIOUS_CHANGE`; field `data_anomalies` trong `ValuationReport`; engine append reason cảnh báo.
- **UI**: overlay hiển thị box "⚠️ BẤT THƯỜNG LỊCH SỬ BCTC" (blocked + qualified).
- **Test**: `test_detect_financial_anomalies_flags_implausible_year_jumps` (2017 -76%, 2018 +873%) + clean-history; 57 pass.