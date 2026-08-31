# TASK-20260831-088: UFVS — Universal Financial Validation Standard (audit theo feedback.txt mới)

**status:** completed
**date:** 2026-08-31
**priority:** high

## Requirement

`docs/feedback.txt` đã được cập nhật thành **QPort Universal Financial Validation Standard (UFVS)**: một chuẩn numeric-validation DUY NHẤT cho toàn bộ ~1500 mã, không ticker-specific. Audit implementation TASK-085/086 so với công thức mới:

| § | Yêu cầu feedback.txt | Hiện trạng | Hành động |
|---|---|---|---|
| 1 | **Symmetric Percentage Change** `Δ=2(X_t−X_{t-1})/(|X_t|+|X_{t-1}|+ε)` + **Robust Z** `Z=0.6745(Δ−median Δ)/(MAD+ε)`; |Z|<2.5 NORMAL, 2.5–3.5 UNUSUAL, 3.5–5 STRONG, >5 EXTREME | đang dùng % change truyền thống | **rework** |
| 2 | **Anomaly Breadth A_t** = Σw·I(|Z_i|≥th)/Σw | chưa có | **thêm** |
| 3 | **Coherence C_t** = Σ w·DirectionMatch·MagnitudeSimilarity(exp(−|Zi−Zj|/k)) ; 0.40–0.69 MEDIUM, ≥0.70 HIGH | có coherence thô 0..1 | **rework pairwise** |
| 4 | **Persistence P_t** = Σw·I(Shift>th)/Σw; <0.30 temp, 0.30–0.60 mixed, >0.60 persistent | có boolean persistent | **thêm score 0..1** |
| 5 | **Mean-Reversion M_t** ∈ [0,1] | có boolean cycle | **thêm score 0..1** |
| 6 | **Universal classifier** decision table dùng Z,A,C,P,M | đang heuristic %change | **rework score-based** |
| 7-9 | **R=A×C×P**, **CY=A×C×M×(1−P)**, **D=Magnitude×(1−C)×(1−P)** | chưa có | **thêm score trace** |
| 10 | Materiality IV-based, grades **IMMATERIAL/LOW/MATERIAL/CRITICAL** | grade NON_MATERIAL/LOW_MATERIALITY | **align tên** (giữ proxy median-margin) |
| 11 | Policy: INCLUDE/SPLIT_REGIME/INCLUDE+PER_SHARE/DOWNWEIGHT_CFO/DOWNWEIGHT_EARNINGS/EXCLUDE_METRIC_YEAR/REJECT_FACT/BLOCK_MODEL | `use` YES/PARTIAL/NO | **align tên policy** |
| 12 | Comparable window = {t | t > latest structural break} | đã có latest regime | giữ |
| 14 | **Validation confidence V** 0–100 (0.2Dq+0.2C+0.15Pq+0.15Ar+0.15Ms+0.15Hc); 90–100 HIGH, 75–89 MEDIUM, 60–74 LOW, <60 UNVERIFIED | numeric_confidence string | **thêm score 0..100** |
| 15 | **Publication gate**: model VERIFIED + validation_confidence ≥ MIN_CONFIDENCE + no critical unresolved + no quality block | chưa có MIN_CONFIDENCE | **thêm** |
| 16 | Event schema: anomaly_score(Z), breadth_score(A), coherence_score(C), persistence_score(P), mean_reversion_score(M) | chưa có | **thêm vào event** |
| 17 | No `if symbol ==` trong detector | đúng (không ticker-specific) | giữ |

## Context

- `value_engine/validation/` hiện có: detector (%change), coherence thô, regime boolean, cycle boolean, materiality proxy, gate heuristic.
- DGC phải giữ kết quả: 2018 STRUCTURAL_REGIME_BREAK, 2021/22 CYCLICAL_EXTREME, regime 2018–2025, screener==detail.
- Unit/mapping error → UNIT_MAPPING_ERROR_CANDIDATE + data_status CONFLICTED.

## Acceptance Criteria

- [x] Detector dùng symmetric % change + robust Z; mọi event có Z (anomaly_score), A (breadth), C (coherence), P (persistence), M (mean-reversion).
- [x] Classifier dùng decision table §6 (Z/A/C/P/M), KHÔNG heuristic %change.
- [x] `validation_confidence` (0–100) trên report + publication gate MIN_CONFIDENCE.
- [x] Materiality grade: IMMATERIAL/LOW/MATERIAL/CRITICAL; policy: INCLUDE/SPLIT_REGIME/... (feedback §10/§11).
- [x] DGC vẫn đúng: break 2018, cycle 2021/22, regime 2018–2025, screener==detail.
- [x] Không ticker-specific; unit error vẫn UNIT_MAPPING_ERROR_CANDIDATE + CONFLICTED.
- [x] Toàn bộ suite pass + build; cập nhật task/index.

## Constraints and Invariants

- Không hardcode ticker trong detector/classifier.
- Giữ parity screener ↔ detail.
- TCBS-only: cause_confidence UNKNOWN.
- Giữ backward-compat `internal_coherence` (0..1) + `numeric_coherence_score` (0..100).

## Implementation Tasks

- [x] Task note + index.
- [x] `anomaly_detector.py`: symmetric Δ + robust Z (cap ±10) + severity; giữ unit-jump/layer1.
- [x] `coherence_checker.py`: pairwise C_t (DirectionMatch × exp(−|Zi−Zj|/k)); `regime_detector.py`: P_t score; `cycle_detector.py`: M_t score.
- [x] `validation_gate.py`: A_t, R/CY/D scores, decision table, validation_confidence V (§14), event schema Z/A/C/P/M/R/CY/D, policy §11.
- [x] `models.py`/`engine.py`: `validation_confidence`, publication gate MIN_CONFIDENCE=60, materiality/policy names.
- [x] `screener.py`/frontend: `validation_confidence`, `UNIT_MAPPING_ERROR_CANDIDATE`, `IMMATERIAL`.
- [x] Tests mới (UFVS scores, decision table, confidence, DGC) + chạy toàn bộ suite + build.

## Related Notes

- docs/feedback.txt (UFVS mới), docs/user-test.md (acceptance), TASK-085/086/087.

## Validation Evidence

```
Gate DGC (dữ liệu thật, robust Z):
  Y2017 SUSPICIOUS_ISOLATED (Z 12.95) · Y2018 STRUCTURAL_REGIME_BREAK (Z 18.6, A .5, C .52, P 1.0)
  Y2021 CYCLICAL_EXTREME · Y2022 CYCLICAL_EXTREME
  regime 2018-2025 · validation_confidence 84 MEDIUM · data_status VALID_WITH_CLASSIFIED_EVENTS

Gate HPG: Y2017 SHARE_STRUCTURE · Y2021 CYCLICAL_EXTREME · Y2022 EARNINGS_ONE_OFF (no split)
Gate VBB (bank): SHARE_STRUCTURE + EARNINGS_ONE_OFF, không UNRESOLVED (CFO excluded)
Gate KSQ: UNIT_MAPPING_ERROR_CANDIDATE, data_status CONFLICTED, conf 44 UNVERIFIED

Universe (1482): model_status giữ nguyên; KHÔNG mã MODEL_VERIFIED nào bị publication gate
  chặn (validation_confidence min/median/max = 60/84/97); DGC vẫn MODEL_VERIFIED conf 84 IV 107169 MOS 59.9

pytest test_value_engine.py validation audit_fixes audit_68_symbols audit_integrity
      valuation_page_contract live_valuation_contract vi_labels -q : 104 passed (7.1s)
pytest test_screener_api.py: 5 passed (49.9s)
npm run build: OK
```

## Decisions

- Materiality giữ proxy median-margin (IV-based 2×valuation quá nặng cho bulk 1482 mã); đổi grade theo §10 (IMMATERIAL/LOW/MATERIAL/CRITICAL).
- Robust Z cần >=3 Δ (>=4 năm) — lịch sử ngắn hơn không detect (đúng, không đủ evidence).
- Branch đặc thù (one-off/timing/share) dùng ngưỡng STRONG (|Z|>=3.5) cho "operating ổn" để tránh blip nhỏ trên baseline ổn định gây false positive.
- `numeric_confidence` (string) giữ + thêm `validation_confidence` (0–100); publication gate dùng `validation_confidence ≥ 60`.

## Result

Đã audit & sửa theo feedback.txt (UFVS mới): detector chuyển sang **Symmetric % Change + robust Z** (universal, không ticker-specific); thêm **breadth A, pairwise coherence C, persistence P, mean-reversion M**; decision table §6 score-based; **regime R / cycle CY / bad-data D** score trace; **validation_confidence V 0–100** + publication gate MIN_CONFIDENCE; materiality IMMATERIAL/LOW/MATERIAL/CRITICAL; policy §11 (SPLIT_REGIME/INCLUDE/REJECT_FACT/...); event schema có Z/A/C/P/M. DGC vẫn đúng break 2018 + cycle 2021/22 + regime 2018–2025; unit error → UNIT_MAPPING_ERROR_CANDIDATE + CONFLICTED. Toàn universe không có verified symbol bị chặn mới. 104 + 5 tests pass, build OK.