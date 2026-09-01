# TASK-20260831-087: Backfill market prices toàn universe — screener từ 334 → 1482 mã

**status:** completed
**date:** 2026-08-31
**priority:** high

## Requirement

User hỏi: "tại sao screener chỉ có 334 mã chứ không phải 1523 mã trong db" — tiêu đề UI "Sàng lọc toàn diện 334 doanh nghiệp".

Root cause: `market_prices` chỉ có giá của **334**/1523 mã. Screener cần giá để tính MOS (`(IV − price)/IV`) → mã không có giá bị loại khỏi universe. 1189 mã có BCTC đầy đủ nhưng **thiếu giá** (không được crawl). Đây là gap dữ liệu (price ingestion), không phải lỗi logic screener.

Fix: backfill giá cho toàn universe (mã có facts nhưng chưa có giá) qua VNDirect/Vnstock, persist vào `market_prices` → screener bao phủ ~1482 mã.

## Context

- `market_prices` trước: 334 mã (HOSE 106/405 · HNX 58/299 · UPCOM 170/819).
- Facts: 1499 mã có canonical_facts + shares.
- Backfill sau: 1135 mã được fetch (35064 row lưu), remaining 0.
- Screener universe sau: **1482** (mã có facts + ≥2 năm history + giá). 41 mã thiếu facts/<2 năm không thể sàng lọc (đúng).

## Acceptance Criteria

- [x] Hàm `backfill_market_prices(limit, max_workers, days)` trong `finance_catalog.py` — fetch threaded + persist, trả summary (requested/fetched_price/rows_saved/failed/remaining).
- [x] Admin endpoint `POST /api/admin/prices/backfill` (body `{limit?}`).
- [x] Screener universe tăng từ 334 → ~1482; `get_screener_results.universe_size` phản ánh đúng.
- [x] Mọi mã có facts+≥2 năm đều vào universe; mã không có giá vẫn bị loại (không thể tính MOS) — đúng behavior.
- [x] Screener tests pass; không vỡ parity DGC.

## Constraints and Invariants

- Không tự tính lại valuation (screener vẫn đọc canonical report).
- Không hardcode; backfill dùng provider có sẵn (VNDirect/Vnstock qua `AutoMarketData`).
- Giá lưu qua `frame_to_price_rows` (đã chuẩn hoá `canonical_vnd_price`).

## Implementation Tasks

- [x] `finance_catalog.py`: `backfill_market_prices`.
- [x] `app/main.py`: `POST /api/admin/prices/backfill`.
- [x] Chạy backfill toàn universe (1135 mã, 35064 rows, remaining 0).
- [x] Verify screener universe 334 → 1482; `get_screener_results` hoạt động (56 buffett-qualified).
- [x] Chạy test screener + build frontend.

## Related Notes

- docs/user-test.md §19/§37 (universe snapshot, no-crash requirement).
- docs/tasks/TASK-20260831-086 (data_status contract).

## Validation Evidence

```
Trước: universe=334 (HOSE 106/405 · HNX 58/299 · UPCOM 170/819 có giá)
Sau backfill: requested=1135 fetched_price=1135 rows_saved=35064 failed=0 remaining=0 (elapsed 103s)

compute_all_screener_scores: universe=1482 (time 5.03s)
  model_status: MODEL_VERIFIED 357 | MODEL_INCOMPLETE 218 | ARCHETYPE_UNKNOWN 803
                MODEL_UNVALUABLE 102 | MODEL_ESTIMATED 1 | MODEL_PARTIAL 1
  with public IV: 141 | with public MOS: 135
  data_status: VALID_WITH_CLASSIFIED_EVENTS 1405 | VALID 68 | INSUFFICIENT 8 | CONFLICTED 1

get_screener_results: universe_size=1482 total_screened=1482 (buffett_qualified 56)
  HSG/PLX/SSI/DGC đều có mặt (trước đó không có giá -> không trong universe)

pytest test_screener_api.py: 4 passed (43.8s)
```

## Decisions

- Backfill là việc DATA (một lần/admin); screener không tự fetch 1189 giá trong request (tránh chậm).
- Mã vẫn không có giá sau backfill (delisted/illiquid UPCOM) bị loại — không thể tính MOS; đúng behavior.

## Addendum — Auto-fetch giá mỗi lần vào page (yêu cầu user)

User yêu cầu "giá phải auto fetch mỗi lần vào page" — không phụ thuộc backfill thủ công:

- **`_fetch_latest_prices(symbols, start, today, max_workers)`**: fetch giá + thanh khoản 20D (VNDirect, threaded) + **in-memory cache 180s** (tránh quá tải provider khi reload/filter liên tục; mỗi lần vào page thật sự cách nhau >TTL vẫn fetch mới).
- **`_apply_refreshed_price(item, close)`**: cập nhật `current_price`, `margin_of_safety`, `is_buffett_qualified`, `pe/pb` (scale theo tỷ lệ giá).
- **`_persist_price_rows(rows)`**: persist price rows vào `market_prices`.
- **`get_screener_results`**: sau sort, **auto-refresh giá cho các mã sẽ hiển thị** (`filtered[:limit]`) mỗi request; KHÔNG ghi đè `avg_turnover` (liquidity filter đã chạy với giá trị cached). Step-2 (missing-liquidity) refactor dùng chung helper.
- **`compute_all_screener_scores`**: auto-backfill giá (bounded 40 mã/compute) cho mã có BCTC nhưng chưa có giá → universe tự hoàn thiện.

Performance: call đầu ~11s (universe compute 5s + fetch ~6s); call sau trong 180s ~0.3s (cache). Filter change trong 3 phút tái dùng cache → nhanh.

```
get_screener_results call1 (fresh fetch ~200 mã): time 11.3s, giá cập nhật
get_screener_results call2 (trong cache TTL):      time 0.3s

pytest test_screener_api.py: 5 passed (48.8s)
pytest test_value_engine.py + validation + contract: 23 passed (0.7s)
npm run build: OK
```

## Result

Đã đóng gap "334 vs 1523": nguyên nhân là thiếu giá (1189 mã có BCTC nhưng không có `market_prices`). Thêm `backfill_market_prices` + admin endpoint, chạy backfill toàn universe → screener bao phủ **1482 mã** (mã có BCTC + ≥2 năm + giá). UI title tự cập nhật theo `universe_size`. 4 screener tests pass.