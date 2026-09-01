# TASK-20260831-085: Numeric-Only Validation & Regime Engine (per feedback.txt)

**status:** completed
**date:** 2026-08-31
**priority:** high

## Requirement

Refactor logic định giá cổ phiếu theo bộ rule trong `docs/feedback.txt`: thay taxonomy `DATA_ANOMALY` nhị phân bằng **Numeric-Only Validation & Regime Engine** áp dụng cho toàn bộ cổ phiếu (TCBS-only, không web verification).

1. **Taxonomy mới** (`NORMAL / SUSPICIOUS_ISOLATED / STRUCTURAL_REGIME_BREAK / CYCLICAL_EXTREME / EARNINGS_ONE_OFF_CANDIDATE / CASHFLOW_TIMING_CANDIDATE / SHARE_STRUCTURE_CHANGE / UNRESOLVED_MATERIAL`). `DATA_ANOMALY` chỉ là output detector ban đầu → resolver phân loại thực.
2. **Layer 1** — kiểm lỗi số liệu thuần túy (unit jump `>100x` + related metrics không nhúc nhích, shares<=0, equity impossible…).
3. **Layer 2** — Cross-metric coherence (không nhìn 1 metric đơn lẻ; coherence score 0..1).
4. **Layer 3** — Structural regime break (>=3/5 metric đổi lớn + `new_level_persists >= 2 năm`); persistence test `pre_level=median(t-2,t-1)` vs `post_level=median(t,t+1,t+2)`.
5. **Regime-aware normalization**: split regime tại structural break; ưu tiên **latest comparable regime** cho mid-cycle normalization (DGC: 2018–2025, đủ >=7 năm full-cycle). Không hardcode DGC.
6. **Cycle extreme** (`CYCLICAL_EXTREME`): spike 1–3 năm rồi mean-revert, **GIỮ năm peak** trong normalization.
7. **Materiality test**: impact lên IV/normalization → `NON_MATERIAL / MATERIAL_LOW / MATERIAL / MATERIAL_CRITICAL`; unresolved/incoherent material → `MODEL_PARTIAL` / block public IV.
8. **2 confidence riêng**: `numeric_confidence` (tin số liệu) và `event_cause_confidence` (UNKNOWN vì TCBS không cho biết nguyên nhân).
9. **Schema resolution** per anomaly: `{year, metric(s), change_pct, detector_status, resolution{classification, confidence, external_verified, internal_coherence, persistent}, valuation_handling{include, split_regime}}`.
10. **UI**: banner "BIẾN ĐỘNG LỊCH SỬ ĐÃ PHÂN LOẠI" theo từng classification; chỉ banner đỏ cho `UNRESOLVED_MATERIAL` / `SUSPICIOUS_ISOLATED` có ảnh hưởng.

## Context

- Hiện `engine.py:detect_financial_anomalies` chỉ gắn nhãn nhị phân `DATA_ANOMALY/SUSPICIOUS_CHANGE`, KHÔNG resolve, KHÔNG gating (chỉ thêm confidence_reason). Normalization dùng toàn bộ trailing window 5/10 năm, không tách regime.
- `OwnerEarningsCalculator.calculate_cycle_normalized` (owner_earnings.py:99-250) dùng `range(latest-lookback+1, latest+1)`, mid-cycle median margin × median revenue.
- DGC: 2017→2018 revenue/LNST/equity/debt/shares cùng nhảy lớn & persists (regime break); 2021–2022 profit/CFO spike rồi mean-revert (cycle extreme). Cần split regime để normalization không trộn Regime A (2016–2017).
- Regression test `test_screener_matches_canonical_valuation_report` (TASK-084) đảm bảo screener == canonical report → phải giữ xanh.

## Acceptance Criteria

- [x] Tạo package `value_engine/validation/` (anomaly_detector, coherence_checker, regime_detector, cycle_detector, materiality_checker, validation_gate).
- [x] `data_anomalies` trong `ValuationReport` mang schema resolution mới (classification, confidence, external_verified, internal_coherence, persistent, valuation_handling).
- [x] Normalization dùng **latest comparable regime**: DGC → window 2018–2025 (dùng 7–8 năm), `normalization_years >= 7`, model vẫn `MODEL_VERIFIED`.
- [x] `numeric_confidence` / `event_cause_confidence` mới trên report; `UNRESOLVED_MATERIAL` trong normalization window → `confidence LOW` + `MODEL_PARTIAL` (không public IV).
- [x] `CYCLICAL_EXTREME` được giữ trong full-cycle (không exclude peak).
- [x] Không hardcode DGC; cùng engine xử lý HPG/HSG/BMP/BSR/PLX theo behavior dữ liệu.
- [x] Frontend: banner phân loại thay cho "BẤT THƯỜNG LỊCH SỬ — CẦN ĐỐI SOÁT NGUỒN"; đỏ chỉ khi UNRESOLVED_MATERIAL/SUSPICIOUS_ISOLATED.
- [x] `pytest` toàn bộ value-engine + screener suite pass; `npm run build` pass.

## Constraints and Invariants

- TCBS-only: không nói "do sáp nhập" — chỉ "thay đổi chế độ/quy mô" (event_cause_confidence = UNKNOWN).
- Không hardcode DGC.
- Giữ parity screener ↔ detail (TASK-084).
- Bất biến sổ cái Buy & Hold không đổi.

## Implementation Tasks

- [x] Task note + index.
- [x] `value_engine/validation/` package.
- [x] `models.py`: thêm `numeric_confidence`, `event_cause_confidence`, `regime_analysis`, `normalization_window`.
- [x] `owner_earnings.py`: thêm `included_years` (latest comparable regime).
- [x] `engine.py`: wire ValidationGate; regime-aware normalization; confidence downgrade; báo cáo regime/window.
- [x] Frontend `ValuationDetailOverlay.jsx` + `aiExport.js`.
- [x] Tests mới + cập nhật test cũ.
- [x] Chạy toàn bộ test + build; verify DGC; cập nhật task/index.

## Related Notes

- docs/feedback.txt (bộ rule nguồn).
- docs/tasks/TASK-20260831-084 (screener parity), TASK-20260831-083 (backfill lịch sử).
- python/portfolio/tests/test_value_engine.py (anomaly tests cũ).

## Validation Evidence

```
Gate DGC (dữ liệu thật): latest_regime_years = [2018..2025]
  regimes: A 2016-2017 (break@2018 HIGH) -> B 2018-2025
  Y2018 STRUCTURAL_REGIME_BREAK (coh 1.0, persistent)
  Y2021/2022 CYCLICAL_EXTREME (giữ trong full-cycle)
  numeric_confidence HIGH | event_cause UNKNOWN
  -> Normalization window 2018-2025, MID_CYCLE_MEDIAN 7-8 năm, MODEL_VERIFIED

Gate HPG: KHÔNG split (2021 là CYCLICAL_EXTREME, không phải break); full 10 năm.
Gate VNM: không break, single regime.

ValuationEngine.evaluate DGC (real path): base_iv ~107,169 | MOS +59.9% | ATTRACTIVE
  (kết quả HỢP LỆ của regime-aware normalization — trước refactor 40,818/FAIRLY_VALUED
   do trộn Regime A 2016-2017; feedback.txt §6 yêu cầu split regime)

=== UNIVERSE VERIFICATION (toàn bộ 1523 securities, không chỉ DGC) ===
securities=1523 | symbols_with_2y+ (gate chạy được)=1482 | 0 lỗi
Classification distribution (per-year, gate):
  SUSPICIOUS_ISOLATED 2459 | CASHFLOW_TIMING 1123 | EARNINGS_ONE_OFF 1116 |
  SHARE_STRUCTURE_CHANGE 674 | CYCLICAL_EXTREME 90 | STRUCTURAL_REGIME_BREAK 1 |
  UNRESOLVED_MATERIAL 1 (KSQ 2018 — dữ liệu thật sự rời rạc, revenue=0)
Engine evaluate: ok=334 (có price+shares) err=0 | skip=1148 (không có giá)
  model_status: ARCHETYPE_UNKNOWN 173 | MODEL_VERIFIED 99 | MODEL_INCOMPLETE 49 |
               MODEL_UNVALUABLE 12 | MODEL_ESTIMATED 1 | public_iv 75 | public_mos 72
Regime split: chỉ DGC (2016-2017 -> 2018-2025) — đúng vì chỉ DGC có persistent
  scale change; HPG/DCM/BSR/PLX đều CYCLICAL_EXTREME / EARNINGS_ONE_OFF (chu kỳ,
  không split nhầm).

Financial-aware gate (is_financial=True bỏ CFO — metric applicability TASK-082):
  VBB/ACB/BID/VCB/SSI: numeric_confidence HIGH, 0 UNRESOLVED_MATERIAL (trước khi sửa
  VBB 2022 bị false UNRESOLVED_MATERIAL do CFO ngân hàng)

pytest test_value_engine.py audit_fixes audit_68_symbols buffett_munger_rule_engine
      audit_integrity_verdict_exposure value_engine_validation valuation_page_contract
      live_valuation_contract vi_labels screener_api -q
  111 passed (49.52s) | riêng 5 suite sau khi thêm is_financial: 54 passed (40.08s)

npm run build (frontend): built in 1.10s
```

## Decisions

- Gate hoạt động trên `financial_history` (đầy đủ mọi năm, có revenue) để phát hiện regime; OE bridge nhận `included_years` = window của latest comparable regime, tự bỏ qua năm thiếu fact.
- Structural break yêu cầu REVENUE đổi lớn (>=60%) + >=3/4 scale metric đổi + persistence + post-level ổn định (max/min<=2.5) + không phải cycle-pattern (profit revert >=40%) → tránh flag nhầm đáy (DGC 2017) và đỉnh chu kỳ (HPG 2021).
- `CYCLICAL_EXTREME` ưu tiên khi có spike + mean-reversion (keep peak theo feedback §7).
- Materiality dùng proxy rẻ: so median net margin trong window có/không có năm anomalous (không re-run toàn engine).
- `event_cause_confidence` luôn `UNKNOWN` (TCBS-only); numeric_confidence HIGH trừ khi có unresolved/incoherent material.
- `is_financial=True` cho tổ chức tài chính (RIM): gate BỎ CFO (CFO ngân hàng = dòng tiền huy động/cho vay, vô nghĩa) — tránh false UNRESOLVED_MATERIAL (VBB 2022) theo metric applicability registry TASK-082.
- Giữ `detect_financial_anomalies` cũ (compat, test cũ dùng); engine giờ dùng `run_validation_gate`.

## Result

Đã refactor logic định giá theo feedback.txt: taxonomy mới 8 lớp (STRUCTURAL_REGIME_BREAK / CYCLICAL_EXTREME / SHARE_STRUCTURE_CHANGE / CASHFLOW_TIMING / EARNINGS_ONE_OFF / SUSPICIOUS_ISOLATED / UNRESOLVED_MATERIAL / NORMAL), Layer 1-3 (unit-jump, coherence, regime persistence), materiality, 2 confidence (numeric/event-cause), và **regime-aware normalization** — mid-cycle chỉ dùng latest comparable regime. DGC tự resolve: break 2018 (split Regime A 2016-2017), giữ peak 2021-2022, window 2018-2025, model VERIFIED. HPG 2021 được phân loại CYCLICAL_EXTREME (không break nhầm). UI đổi sang banner "BIẾN ĐỘNG LỊCH SỬ ĐÃ PHÂN LOẠI", chỉ đỏ khi UNRESOLVED_MATERIAL.

## Addendum — Đưa Regime Engine lên trang "Định giá" + fix CSS section

- **`ValuationDetailOverlay.jsx`**: export `HistoricalResolutionsBlock`; thêm khối **Window chuẩn hóa (latest comparable regime)** + **Phân tích regime (structural break)** ngay trong section; bỏ inline `<style>` cho `.v-anomaly-*` (chuyển sang CSS global).
- **`ValuationPage.jsx`**: render `<HistoricalResolutionsBlock/>` trên cả card **đủ chuẩn** (sau Value Investor Pillars, trước technical details) và card **bị chặn** (sau missing-data) — đưa logic định giá đã refactor vào trang "định giá".
- **`valuation-page.css`**: chuyển toàn bộ CSS section "BIẾN ĐỘNG LỊCH SỬ ĐÃ PHÂN LOẠI" (`.v-anomaly-box` xanh/resolved, `.v-anomaly-box-blocking` đỏ, `.v-anomaly-box-info`, `.v-anomaly-tag.resolved/watch/blocking/material`, `.v-regime-strip/.v-regime-item/.v-regime-chip`) vào file global (import qua `entry-client.jsx`/`entry-vercel.jsx`) → áp dụng đồng nhất cho cả ValuationPage và overlay; thêm responsive `<720px`.
- Build: `npm run build` OK (CSS bundle tăng do thêm section); contract tests `test_valuation_page_contract.py` / `test_live_valuation_contract.py` pass.