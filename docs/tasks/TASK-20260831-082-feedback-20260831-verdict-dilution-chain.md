# TASK-20260831-082: Apply 31/08 Audit Feedback — Verdict Precedence, Dilution Classification, Chain Re-anchor

**status:** completed
**date:** 2026-08-31
**priority:** high

## Requirement

Sửa theo feedback audit export 31/08/2026 (`docs/feedback.txt`): P0 regression nằm ở decision layer (dilution -> hard reject -> final verdict).

1. **P0 - Hard-reject precedence**: `hard_rejects` phải override verdict; không trả `ATTRACTIVE / HIGH_CONVICTION_VALUE / FAIRLY_VALUED`. (FRT/SCS -> ATTRACTIVE, CMG/VCI -> FAIRLY_VALUED dù có `EXCESSIVE_DILUTION`.)
2. **P0 - Restore dilution classification schema**: `dilution_classification`, `confirmed_economic_dilution_pct`, `unexplained_share_change_pct`, `UNEXPLAINED_SHARE_CHANGE`; `UNKNOWN != 0`. Share-count tăng do stock dividend/bonus/split != economic dilution.
3. **P0 - Re-anchor activity chain**: chain đang `BROKEN / PREV_HASH_MISMATCH / first_bad_id=73`; migration `BROKEN_HISTORICAL -> CHAIN_REANCHOR -> VERIFIED_FROM_ANCHOR` (không rewrite history).

## Context

Feedback audit export 31/08: engine tự báo `hard_rejects=[EXCESSIVE_DILUTION]` nhưng kết luận `ATTRACTIVE` (FRT/SCS) / `FAIRLY_VALUED` (CMG/VCI). Export không còn field dilution classification (0 occurrence) - regression so với architecture confirmed-vs-unexplained đã thiết kế. Ngoài ra health table hiển thị metric không áp dụng cho tổ chức tài chính.

## Acceptance Criteria

- [x] `MarginOfSafetyEngine.calculate` nhận `hard_rejects`; verdict luôn override sang `AVOID_QUALITY` / `AVOID_SOLVENCY` / `UNVALUABLE` khi có hard reject.
- [x] `LOW_QUALITY` + MOS satisfied không còn trả `ATTRACTIVE`.
- [x] Leverage penalty dựa trên `net_debt / debt_payback_years / net_debt_to_ebitda` thực (không chỉ overlay CAPITAL_INTENSIVE).
- [x] `QualityScorer.evaluate` chỉ hard-reject `EXCESSIVE_DILUTION` khi có bằng chứng event (`dilution_classification="EXCESSIVE_DILUTION"` hoặc confirmed >= 20%), không với `UNEXPLAINED_SHARE_CHANGE` / `NON_ECONOMIC_SHARE_CHANGE`.
- [x] `app/main.py` dùng `classify_share_change`; expose `dilution_classification`, `confirmed_economic_dilution_5y_pct`, `unexplained_share_change_5y_pct`, `non_economic_share_change_5y_pct`, `raw_share_change_5y_pct`, `dilution_breakdown`.
- [x] Capital-allocation `status = UNCERTAIN` khi có unexplained material; score bị cap <= 10.
- [x] Metric applicability registry: bank/securities/insurance -> `cash_conversion = N/A`, `debt_payback = N/A`.
- [x] Admin endpoint `POST /api/admin/activity/reanchor` để re-anchor chain BROKEN trong production.
- [x] Archetype refinement: BAF -> AGRICULTURE, AST -> AIRPORT_SERVICES (mới), VSC -> PORT_INFRASTRUCTURE.
- [x] P2: AI export overview header model-neutral (Archetype/Model/Model Status/Bear IV/Base IV/Bull IV/MOS/Req MOS/Confidence); RIM scenario expose `residual_income_pv` / `terminal_residual_income_pv`.
- [x] Toàn bộ contract tests `test_audit_integrity_verdict_exposure.py` pass (36).

## Constraints and Invariants

- Không rewrite activity history: re-anchor tạo genesis mới, legacy segment giữ `BROKEN_HISTORICAL`.
- Bất biến sổ cái Buy & Hold không đổi.
- IV/MOS public chỉ khi `MODEL_VERIFIED`.

## Implementation Tasks

- [x] `margin_of_safety.py`: hard_rejects override + LOW_QUALITY gate + leverage từ debt thực.
- [x] `quality_scorer.py`: dilution classification-aware hard reject + cap capital allocation.
- [x] `engine.py`: wire dilution evidence, hard_rejects, leverage vào scorer/MOS; public_* + diagnostic_fallback.
- [x] `models.py`: thêm `public_base_iv/bear/bull/mos/epv`, `diagnostic_fallback`, `residual_income_pv`, `terminal_residual_income_pv`.
- [x] `bank_valuation.py`: set semantic RIM fields.
- [x] `app/main.py`: `classify_share_change` + metric applicability registry + status UNCERTAIN + admin re-anchor endpoint.
- [x] `archetypes.py`/`vi_labels.py`: AIRPORT_SERVICES + BAF/AST/VSC.
- [x] `frontend/src/lib/aiExport.js`: model-neutral overview + null debt-payback.

## Related Notes

- docs/tasks/TASK-20260829-066, 068, 069, 070 (dilution & verdict design).
- docs/feedback.txt (audit 31/08).

## Validation Evidence

```
python -m pytest portfolio/tests/test_audit_integrity_verdict_exposure.py -q
36 passed in 4.86s

python -m pytest portfolio/tests/test_value_engine.py test_value_engine_audit_fixes.py
test_value_engine_audit_68_symbols.py test_buffett_munger_rule_engine.py ... -q
97 passed, 1 failed (pre-existing psycopg ModuleNotFoundError)

Full suite (excl. psycopg modules): 333 passed, 11 failed (pre-existing Windows/psycopg/env)
npm run build (frontend): built in 1.06s
```

## Decisions

- `AST` -> archetype mới `AIRPORT_SERVICES` (fee-for-service, dùng NORMALIZED_OWNER_EARNINGS_DCF, không CONCESSION_DCF vì không phải concession hữu hạn).
- `CTR`/`TNH` chưa đổi: thiếu bằng chứng phân loại; TNH là nhà sản xuất dược (PHARMACEUTICAL phù hợp hơn HEALTHCARE_SERVICES) — để ngỏ tới khi có dữ liệu chắc chắn.
- `economic_events` trong `classify_share_change` rỗng (finance DB chỉ lưu CASH/STOCK_DIVIDEND) -> residual trở thành `UNEXPLAINED_SHARE_CHANGE`, không hard-reject. Cần ingest ESOP/rights/placement để nâng lên `EXCESSIVE_DILUTION` khi hợp lệ.

## Result

P0 blocking issues đã đóng: hard-reject precedence, dilution classification schema, cơ chế re-anchor chain. Các P1 còn lại (Reserve/Fleet/Airline EBITDAR model, 7-10Y full-cycle normalization) cần model mới và dữ liệu lịch sử bổ sung.

## Addendum 3 — Feedback 03:56 (round 3): leverage unit bug + dilution residual rename

Theo priority của feedback 03:56 (valuation core 9.2/10; production ~8.9/10):

- **#1 — Fix `net_debt_to_ebitda` unit mismatch** (`app/main.py`): `net_debt_calc` đang ở VND nhưng `operating_profit`/`depreciation` từ finance DB ở TỶ đồng → chia trực tiếp ra số cực lớn (SCS 541Mx, FRT 9.1Bx). Đã scale EBITDA lên VND (`* 1e9`) trước khi chia + thêm invariant `0 <= ratio < 100` (ngoài range → None).
- **#2 — Rename residual dilution field** (`dilution.py`): `economic_dilution_pct` trong breakdown KHÔNG còn mang residual chưa xác nhận. Rename residual → `residual_share_change_pct`; `economic_dilution_pct` giờ chỉ bằng phần ĐÃ XÁC NHẬN (null khi UNEXPLAINED/NON_ECONOMIC). Cập nhật test `test_audit_integrity_verdict_exposure.py` (37 pass). Tránh consumer cũ tái tạo bug `UNEXPLAINED → EXCESSIVE_DILUTION`.
- **#3 — Re-anchor DB**: endpoint `POST /api/admin/activity/reanchor` đã sẵn sàng; cần EXECUTE trên production DB (chain đang BROKEN / PREV_HASH_MISMATCH / first_bad_id=73) → `VERIFIED_FROM_ANCHOR`.

Còn lại là model/data coverage gap (feature, không phải bug): #4 7–10Y full-cycle, #5 Reserve NAV, #6 Fleet NAV, #7 Airline EBITDAR, #8 Mid-cycle FCFF — cần dữ liệu lịch sử / nguồn đặc thù.

## Addendum 6 — VSDC (official depository) ingestion

Implement VSDC data ingestion (user-test.md: VSDC = Canonical corporate-action source):

- **`python/portfolio/vsdc.py`** (mới):
  - `VsdcClient`: session-bound `__VPToken` (từ `<meta>`), `search_security` (ticker→security_id), `search_announcements` (`/isuisser-tcdk/search`), `search_rights` (`/isuisser-thq/search`), `get_announcement` (`/vi/ad/{id}`).
  - `parse_announcement`: extract ticker, record date, payment date, reason, ratio, cash/stock ratio; robust Vietnamese diacritic handling; `_classify_vsdc` phân biệt CASH_DIVIDEND ("bằng tiền"/"tiền mặt") vs STOCK_DIVIDEND ("bằng cổ phiếu") vs RIGHTS_ISSUE ("quyền mua")…
  - `parse_share_registration_history`: parse bảng "Thông tin đăng ký chứng khoán" (`#Detail_TCPH_TTDKCK`) → danh sách {reason, quantity_delta, date} để reconcile NON_ECONOMIC vs ECONOMIC share change.
  - `VsdcCorporateActionProvider` (protocol `name/events/health`).
  - `default_corporate_action_provider()`: VSDC-first, fallback multi-source (VPS/FireAnt/CafeF/Vietcap+vnstock).
- **`institutional.py`**: default `ca_provider` = VSDC-first.
- **Test**: `test_vsdc.py` (6 pass). Live verify: SBT→security_id 707, phân loại đúng CASH_DIVIDEND/STOCK_DIVIDEND/RIGHTS_ISSUE.
- Full suite: 340 pass (11 fail pre-existing Windows/psycopg).

## Addendum 5 — user-test.md: screener không dùng diagnostic MOS để xếp hạng

`docs/user-test.md` chỉ ra: overview screener xếp IDC/HAH/HPG/DGC/BMP như có MOS rất cao (IDC +82%) trong khi detail là `MODEL_INCOMPLETE / MOS N/A`. Đã sửa:

- **`screener.py`**: tách MOS chính vs diagnostic. Mã `MODEL_VERIFIED` → `margin_of_safety`/`intrinsic_value` là MOS THẬT. Mã `MODEL_INCOMPLETE / MODEL_ESTIMATED / ARCHETYPE_UNKNOWN` → `margin_of_safety`/`intrinsic_value` = null; giá trị simplified chuyển sang `diagnostic_mos`/`diagnostic_intrinsic_value` (chỉ tham khảo). `valuation_status` = MODEL_INCOMPLETE/MODEL_ESTIMATED/ARCHETYPE_UNKNOWN tương ứng (kèm tiếng Việt).
  - Filter `buffett_qualified`/`positive`/`undervalued` giờ chỉ nhận mã MODEL_VERIFIED (INVESTABLE SCREEN).
  - Sort theo MOS chỉ xếp hạng mã verified; diagnostic không tham gia.
- **`ScreenerPage.jsx`**: section 2 (research candidates) hiển thị `diagnostic_mos` với nhãn "MOS tham khảo (chưa xác thực)"; score-badge hiển thị model status (Mô hình Ước tính / Thiếu dữ liệu model). CSV thêm cột `MOS tham khảo (%)` + `Model Status`.
- **`aiExport.js`**: export AI đánh dấu MOS "(tham khảo)" cho non-verified.

Kết quả: INVESTABLE SCREEN = chỉ MODEL_VERIFIED; RESEARCH CANDIDATES = MODEL_INCOMPLETE/ESTIMATED với diagnostic IV/MOS tham khảo — không còn cảm giác IDC/HAH rẻ 50–80% khi model chưa đủ dữ liệu.

## Addendum 4 — Screener: 2 section theo model coverage

User yêu cầu chia kết quả bộ lọc theo mức đầy đủ dữ liệu định giá:
- **Section 1**: mã `MODEL_VERIFIED` + có MOS (đầy đủ dữ liệu để tính Giá trị Thực).
- **Section 2**: mã thiếu dữ liệu vì `MODEL_INCOMPLETE` ("Thiếu dữ liệu mô hình đặc thù"), `MODEL_ESTIMATED` ("Mô hình Ước tính — giả định chưa có nguồn"), `ARCHETYPE_UNKNOWN`.

Thay đổi:
- `screener.py`: thêm `model_status` + `valuation_gap` (lý do tiếng Việt) cho từng mã, tính theo archetype/recommended_model (RESERVE_NAV/FLEET_NAV/AIRLINE_EBITDAR/MID_CYCLE_FCFF/RNAV/SOTP/LEASE_CASHFLOW_DCF → MODEL_INCOMPLETE; CONCESSION_DCF + AIRPORT → MODEL_ESTIMATED; ARCHETYPE_UNKNOWN → chưa xác định; còn lại → MODEL_VERIFIED).
- `ScreenerPage.jsx`: `fullyValued = model_status==='MODEL_VERIFIED' && margin_of_safety!=null`; section 2 = phần còn lại; card section 2 hiển thị `valuation_gap` (label in đậm).
- `aiExport.js`: `screenerFullyValued` dùng `model_status`; export AI ghi `valuation_gap`.

## Addendum 2 — Feedback 03:28 (round 2): P1 report semantics & confidence cap

Theo priority list của feedback vòng 2 (P0 decision-layer đã đóng), đã sửa:

- **P1#3 — Cap confidence <= LOW** khi `UNEXPLAINED_SHARE_CHANGE >= 20%` (`engine.py`): trước chỉ hạ HIGH→MEDIUM, giờ cap thẳng xuống LOW → SCS/FRT không còn ngang confidence với công ty có share history sạch.
- **P1#5 — Bỏ từ "full-cycle" cho MID_CYCLE_MEDIAN < 7 năm** (`engine.py` model_label + oe_label): 3-5 năm chỉ là "Ước tính giữa chu kỳ tạm thời (X năm; chưa đạt chuẩn full-cycle 7–10 năm)", không còn gọi là "full-cycle".
- **P1#2 — Tách bạch model-gating vs quality-gating** trong AI export (`aiExport.js` Analyst Verdict / Owner Earnings Bridge): MODEL_VERIFIED nhưng bị chặn chất lượng → message "Model VERIFIED nhưng không đạt chuẩn Buffett → IV/MOS bị ẩn (quality gate)", không còn nhầm thành "Mô hình chưa verified".
- **P1#4 — Tách ROE status khỏi capital-allocation UNCERTAIN** trong Health table (`aiExport.js`): thêm cột "Capital Allocation" riêng; cột "5Y Avg ROE" chỉ hiển thị giá trị ROE (ROE bản thân không uncertain).
- **P0/P1#1 — Re-anchor activity chain**: endpoint `POST /api/admin/activity/reanchor` đã sẵn sàng; đây là việc VẬN HÀNH cần chạy trên production DB (chain đang BROKEN / PREV_HASH_MISMATCH / first_bad_id=73).

Còn lại là **model/data coverage gap** (không phải bug):
- **#6 7–10Y normalization**: engine code (MID_CYCLE_MEDIAN) đã có; thiếu dữ liệu lịch sử ≥7 năm trong finance DB.
- **#7–9 Reserve NAV / Fleet NAV / Airline EBITDAR**: cần nguồn dữ liệu đặc thù (trữ lượng, giá trị đội tàu, thuê máy bay) chưa được ingest — không nên tạo model giả khi thiếu dữ liệu thật.
- **#10 Mid-cycle FCFF (PVD/PVS)**: cần model mới + dữ liệu chu kỳ.

## Addendum 1 — Buffett-standard valuation gating (user yêu cầu sau feedback)

Cổ phiếu KHÔNG đạt chuẩn Buffett/Munger hoặc điểm chất lượng quá tệ sẽ KHÔNG được tính/công bố MOS và Giá trị Thực (IV); thay vào đó đưa ra cảnh báo kèm nguyên nhân:

- `value_engine/engine.py`: `is_public_verified = model_status == "MODEL_VERIFIED" and not quality_blocked`, với `quality_blocked = bool(hard_rejects) or tier == LOW_QUALITY`. IV/MOS public trả null; số raw vẫn giữ trong `diagnostic_fallback` (AUDIT_ONLY).
- `models.py`: thêm `valuation_warning` (lý do tiếng Việt: hard reject mapping hoặc điểm quá thấp).
- `screener.py`: không tính `intrinsic_value`/`margin_of_safety` khi `quality_blocked`; set `valuation_status=AVOID_QUALITY` + `valuation_warning`.
- `vi_labels.py`: `HARD_REJECT_VI` mapping tiếng Việt + `hard_reject_vi()`.
- Frontend: banner cảnh báo ⚠ trên ScreenerPage, ValuationDetailOverlay (`v-warning-banner`), ValuationPage (table + mobile card); aiExport hiển thị "⚠ Không công bố" + cột Warning. IV/MOS hero đọc `public_*` gated, không fallback về scenario raw.
- Test cập nhật: fixture nghèo (LOW_QUALITY / DATA_INSUFFICIENT) giờ bị chặn IV; thêm `test_low_quality_verified_model_does_not_expose_public_iv_mos`; test "verified exposes IV" dùng `_healthy_history()` (HIGH_QUALITY).