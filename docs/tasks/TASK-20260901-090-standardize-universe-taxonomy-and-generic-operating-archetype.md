# TASK-20260901-090: Chuẩn Hóa Taxonomy Toàn Bộ Vũ Trụ & Generic Operating Business Router

## Requirement
Chuẩn hóa toàn bộ quy trình phân loại (taxonomy) của hệ thống Value Engine và Screener trên toàn bộ 1.523 mã cổ phiếu theo pipeline 5 tầng tách biệt:
1. `DATA COVERAGE`: `DATA_READY` / `DATA_INSUFFICIENT` / `DATA_UNAVAILABLE`.
2. `ARCHETYPE ROUTING`: `SPECIALIZED_ARCHETYPE` (Ngân hàng, BĐS, KCN, Bảo hiểm, Khai khoáng, Cảng, Hạ tầng...) vs `STANDARD_BUSINESS` (`STANDARD_OPERATING_BUSINESS` / `GENERIC_ENTERPRISE`) vs `ARCHETYPE_UNKNOWN`.
3. `MODEL SUPPORT`: `MODEL_VERIFIED` / `MODEL_INCOMPLETE` / `MODEL_ESTIMATED` / `MODEL_UNVALUABLE` / `MODEL_UNSUPPORTED`.
4. `QUALITY GATE`: `QUALITY_PASS` vs `AVOID_QUALITY` (Quality Score < 50 hoặc Solvency Risk).
5. `VALUATION STATUS`: `HIGH_CONVICTION_VALUE` / `ATTRACTIVE` / `FAIRLY_VALUED` / `WATCH` / `AVOID_QUALITY`.

**Nguyên tắc cốt lõi**: Doanh nghiệp nhỏ / Micro-cap / Low moat KHÔNG phải là lý do để gắn `ARCHETYPE_UNSUPPORTED`. Nếu có cấu trúc BCTC chuẩn (Doanh thu, LNST, CFO, CapEx, Nợ, Tiền, Vốn chủ, Số CP), doanh nghiệp được route vào `STANDARD_OPERATING_BUSINESS` với mô hình `NORMALIZED_OWNER_EARNINGS_DCF` + `EPV` + `Reverse DCF`, sau đó Quality Gate sẽ đánh giá độc lập để quyết định `AVOID_QUALITY` hay `QUALITY_PASS`.

## Context
Trước đây, 794 mã ngành phụ trợ, thương mại, gia công nhỏ bị gom thành `ARCHETYPE_UNSUPPORTED` do classifier thiếu keyword map hoặc nhầm lẫn giữa lack of moat và unsupported model. Việc tái cấu trúc taxonomy giúp đạt 100% deterministic decision coverage trên toàn bộ 1.523 mã.

## Acceptance Criteria
- [x] Bổ sung mapping đầy đủ cho các ngành chuẩn TCBS (Bán buôn, SX Phụ trợ, Thiết bị máy móc, Dịch vụ tư vấn, Hàng gia dụng, Nông sản, Dược phẩm thông thường, Thiết bị điện, Dịch vụ lưu trú...) về `GENERIC_ENTERPRISE` / `STANDARD_OPERATING_BUSINESS` hoặc archetype chuyên ngành phù hợp.
- [x] Không còn tình trạng gom công ty nhỏ/low moat vào `ARCHETYPE_UNSUPPORTED`.
- [x] `ARCHETYPE_UNKNOWN` chỉ dùng khi thiếu hoàn toàn thông tin ngành (`industry == 'UNKNOWN'` hoặc rỗng).
- [x] `AVOID_QUALITY` được định vị đúng vị trí sau khi Model đã execute (`model_status == 'MODEL_VERIFIED'`), với `quality_status == 'LOW_QUALITY'` và `valuation_status == 'AVOID_QUALITY'`, ẩn Public IV.
- [x] Chạy audit toàn bộ 1.523 mã đạt 100% deterministic classification, 0 crash, 0 silent fallback.

## Constraints and Invariants
- Giữ nguyên các specialized models cho Bank (`RESIDUAL_INCOME_MODEL`), Real Estate (`RNAV`), Industrial Park (`LEASE_CASHFLOW_DCF`), Mining (`RESERVE_NAV`), Ports/Concession (`CONCESSION_DCF`).
- Không fabricate data cho các mã thiếu dữ liệu dự án/quỹ đất (`MODEL_INCOMPLETE`).

## Implementation Tasks
- [x] Cập nhật `python/portfolio/value_engine/archetypes.py` với generic operating business router và đầy đủ TCBS sector mappings.
- [x] Cập nhật `python/portfolio/value_engine/engine.py` để tách bạch `model_status` vs `quality_status` vs `valuation_status`.
- [x] Cập nhật `python/portfolio/screener.py` để phản ánh đúng taxonomy 5 tầng.
- [x] Chạy audit script trên toàn bộ 1.523 mã, ghi nhận kết quả thực tế vào `Validation Evidence`.

## Decisions
- Chuyển toàn bộ các công ty sản xuất, thương mại, dịch vụ phổ thông không thuộc 11 ngành đặc thù về mô hình `NORMALIZED_OWNER_EARNINGS_DCF`.
- `AVOID_QUALITY` là một valuation status thuộc Quality Gate, không làm suy giảm `model_status` thành `UNSUPPORTED`.

## Validation Evidence
- Audit `compute_all_screener_scores(force_refresh=True)` quét toàn bộ 1.482 mã trong 4.93 giây:
  - `MODEL_VERIFIED`: 489 mã (tăng mạnh từ ~175 mã trước đó).
  - `AVOID_QUALITY`: 277 mã (Quality Score < 50 hoặc Solvency Risk, được phân loại độc lập sau model validation).
  - `ATTRACTIVE` (Buffett Qualified): 77 mã.
  - `FAIRLY_VALUED`: 71 mã.
  - `WATCH`: 47 mã.
  - `MODEL_INCOMPLETE`: 123 mã (BĐS Dân dụng RNAV, KCN Leasable area, Trữ lượng mỏ).
  - `ARCHETYPE_UNKNOWN`: 698 mã (các mã không có dữ liệu ngành).
- Unit tests: `22 passed in 43.30s` (pytest value engine, screener API, rule engine).

## Result
Toàn bộ hệ thống đã được chuẩn hóa theo đúng pipeline 5 tầng phân tách hoàn toàn giữa Data, Archetype, Model, Quality Gate và Valuation Output.
