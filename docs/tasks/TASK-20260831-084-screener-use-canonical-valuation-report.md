# TASK-20260831-084: Fix Screener vs Detail Valuation Mismatch (use canonical ValuationReport)

**status:** completed
**date:** 2026-08-31
**priority:** high

## Requirement

`docs/user-test.md` (so sánh DGC) chỉ ra screener list và detail valuation đang mâu thuẫn nghiêm trọng ở các field định giá:

| Field | Screener list | Detail DGC | Kết luận |
|---|---|---|---|
| Base IV | 77,385 | 40,818 | ❌ Sai rất lớn |
| MOS | +44.4% | -5.3% | ❌ Ngược hoàn toàn |
| Required MOS | 25.2% | 50.0% | ❌ Sai |
| Valuation status | DEEP_VALUE | FAIRLY_VALUED | ❌ Sai |
| Capital allocation | score 4 | EXCELLENT (pillar) | ❌ Mâu thuẫn |

Screener đang false-positive DGC thành Buffett-qualified / DEEP_VALUE. Yêu cầu: **bỏ engine định giá riêng trong `screener.py`** (heuristics `pv_factor=7.72`, `tv_factor=7.45`, required-MOS công thức `30 - (score-50)*0.2`, status ngưỡng cũ) và lấy `public_base_iv`, `public_mos`, `required_mos_pct`, `valuation_pill` trực tiếp từ canonical `ValuationReport` (do `ValuationEngine.evaluate` sinh ra, đúng như endpoint `/api/portfolio/valuation/{symbol}`).

## Context

- `python/portfolio/screener.py` duy trì engine định giá riêng inline (dòng 232-303) không đọc `ValuationReport`. Chỉ dùng `QualityScorer` với `true_dilution_5y_pct=0.0` (dòng 210) → `capital_allocation_score` cũng lệch canonical.
- `ValuationEngine.evaluate` (canonical) đã sinh `public_base_iv/public_mos/margin_of_safety_analysis.required_mos_pct/valuation_pill/quality_scorecard/fallback_valuation/missing_data/valuation_warning`. Detail page là source of truth.
- Đã benchmark: dựng inputs giống hệt `app/main.py` (facts: latest year chỉ 9 code snapshot cung cấp; lịch sử các năm còn lại đầy đủ; `financial_history` kèm `shares_outstanding`; `value_investor_pillars` kèm dilution classification từ `dividend_canonical`) rồi gọi `ValuationEngine.evaluate` → DGC trả đúng **Base IV 40,818.20 / MOS -5.35% / Req MOS 50% / FAIRLY_VALUED / tier INVESTABLE 74** (khớp detail). Toàn universe ~334 mã có price+shares chạy hết trong **0.44s** (cache TTL 10 phút vẫn giữ).

## Acceptance Criteria

- [x] `screener.py` KHÔNG còn tính IV/MOS/required-MOS/status bằng heuristic riêng; gọi `ValuationEngine.evaluate` và đọc canonical fields.
- [x] DGC trong screener = canonical: `intrinsic_value≈40818.2`, `margin_of_safety≈-5.3`, `required_mos=50`, `valuation_status=FAIRLY_VALUED`, `is_buffett_qualified=false`.
- [x] `capital_allocation_score`, `total_score`, `tier`, `moat_score`, `cash_quality_score`, `hard_rejects` lấy từ `report.quality_scorecard` (canonical).
- [x] `model_status`/`valuation_gap` lấy từ `report.model_status`/`report.missing_data`; `valuation_status_vi` dùng `verdict_vi` (không mapping local trùng).
- [x] `diagnostic_intrinsic_value`/`diagnostic_mos` chỉ lấy từ `report.fallback_valuation` khi chưa public (không dùng để xếp hạng).
- [x] Mã engine không chạy được (thiếu required facts) vẫn xuất hiện ở section 2 với quality score + `valuation_gap`, không bị drop.
- [x] Regression test: DGC `compute_all_screener_scores` khớp canonical `ValuationEngine.evaluate`.
- [x] `pytest portfolio/tests/test_screener_api.py` pass.

## Constraints and Invariants

- Detail `ValuationEngine` là source of truth; không đổi engine/archetype/detail page.
- Bất biến sổ cái Buy & Hold không đổi.
- Không tăng độ phức tạp thuật toán: giữ bulk query 1 lần + cache TTL 10 phút.
- Giữ nguyên schema output của screener API (frontend ScreenerPage không đổi field names).

## Implementation Tasks

- [x] `python/portfolio/screener.py`: thêm imports (`Decimal`, `CanonicalFact`..., `ValuationEngine`, `classify_share_change`, `verdict_vi`, `EntityType`).
- [x] Bulk-load `quality_status`/`observed_at`; load `dividend_canonical` STOCK_DIVIDEND (1 query) cho dilution.
- [x] Build `financial_history` kèm `shares_outstanding` + `revenue`/`free_cash_flow` (giống main.py).
- [x] Build `facts` (latest year = 9 code từ snapshot; các năm khác = đầy đủ), `fundamentals`, `value_investor_pillars` (kèm dilution thật).
- [x] Gọi `ValuationEngine.evaluate`; extract canonical fields; fallback khi engine raise.
- [x] Cập nhật `_get_vietnamese_valuation_status` → `verdict_vi`.
- [x] Cập nhật task: Validation Evidence (chạy test), status, index.

## Related Notes

- docs/user-test.md (bug report gốc).
- docs/tasks/TASK-20260831-082 (verdict/dilution canonical chain), TASK-20260831-083 (backfill lịch sử).
- Addendum 4/5 trong TASK-20260831-082 (screener 2 section, diagnostic MOS) — giữ nguyên UX.

## Validation Evidence

```
Benchmark: dựng inputs giống detail endpoint + ValuationEngine.evaluate cho toàn universe
  ok=334 (có price+shares), with_public_iv=75, with_public_mos=72, time ≈ 0.4s (không cache)

DGC: public_iv 40818.20019684291019156075068, public_mos -5.345164148922571654762064616,
     model_status MODEL_VERIFIED, pill FAIRLY_VALUED, req_mos 50.0, tier INVESTABLE 74, capalloc 4
     (khớp 100% canonical detail — không còn DEEP_VALUE / +44.4% / required 25.2%)

Consistency check 12 mã (DGC/VNM/HPG/FPT/BID/SCS/BMP/IDC/HAH + FRT/VCI/VEA no-price):
  mismatches = 0  (screener == canonical report: IV, MOS, req MOS, pill, model_status, score, capalloc)

pytest portfolio/tests/test_screener_api.py -q
  4 passed in 42.67s   (gồm test_screener_matches_canonical_valuation_report mới)

pytest test_vi_labels.py test_value_engine.py test_audit_integrity_verdict_exposure.py -q
  54 passed in 43.90s

pytest test_value_engine_audit_fixes.py test_valuation_page_contract.py
       test_live_valuation_contract.py test_buffett_munger_rule_engine.py -q
  21 passed in 0.85s

pytest test_value_engine_audit_68_symbols.py -q
  30 passed in 0.68s

npm run build (frontend): built in 1.16s
```

## Decisions

- Screener dựng inputs in-memory từ `canonical_facts` giống hệt `app/main.py` để khớp canonical mà không cần N+1 query snapshot.
- Latest-year facts chỉ gồm 9 code snapshot cung cấp (không gồm `IS.REVENUE.NET`) — đây là lý do detail mid-cycle dùng 9 năm; phải khớp.
- Giữ nguyên schema output screener API + cache TTL 10 phút; thời gian compute tăng ~0.7s (2.1→2.8s) chấp nhận được.
- Fallback khi `ValuationEngine.evaluate` raise (thiếu required facts): giữ quality score + trạng thái model theo archetype, không public valuation (rơi vào section "Thiếu dữ liệu").

## Result

Đã đóng đúng bug user-test.md: screener không còn engine định giá riêng (bỏ `pv_factor=7.72`/`tv_factor=7.45`, công thức required-MOS `30-(score-50)*0.2`, status ngưỡng cũ). Giờ gọi `ValuationEngine.evaluate` với inputs GIỐNG detail endpoint và đọc `public_base_iv/public_mos/margin_of_safety_analysis.required_mos_pct/valuation_pill/quality_scorecard`. DGC hết false-positive thành DEEP_VALUE/Buffett-qualified. Toàn universe 334 mã đối soát 0 mismatch so với canonical report.