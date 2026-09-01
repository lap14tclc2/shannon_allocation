# TASK-20260831-086: Compliance với user-test.md — DATA_STATUS, UNIT_OR_MAPPING_ERROR, coherence 0..100, materiality grades, normalization evidence

**status:** completed
**date:** 2026-08-31
**priority:** high

## Requirement

`docs/user-test.md` là spec acceptance của Numeric Validation & Regime Engine (TASK-085). Audit cho thấy vài điểm chưa khớp contract, cần bổ sung:

1. **DATA_STATUS taxonomy** (§5): `VALID / VALID_WITH_CLASSIFIED_EVENTS / SUSPICIOUS / CONFLICTED / INSUFFICIENT` — hiện chỉ có `numeric_confidence`, thiếu `data_status`.
2. **UNIT_OR_MAPPING_ERROR_CANDIDATE** (§6, §7, §17): unit/mapping error phải là classification RIÊNG (hiện đang gộp vào `UNRESOLVED_MATERIAL`); handling = block affected fact, `DATA_STATUS=CONFLICTED`.
3. **numeric_coherence_score 0..100** (§9): 5 component × 20 (Revenue/Profit/Cash-flow/Balance-sheet/Persistence); `>=80 HIGH, 60–79 MEDIUM, <60 LOW`.
4. **Materiality grade** (§16): `NON_MATERIAL / LOW_MATERIALITY / MATERIAL / CRITICAL` (hiện đang dùng `MATERIAL_LOW / MATERIAL_CRITICAL`).
5. **Normalization evidence** (§27, §38-Test C): expose `candidate_years / included_years / excluded_years / reason` bên cạnh `comparable_regime_start/end`, `normalization_years`.
6. **`cause_confidence`** (§31): đổi tên `event_cause_confidence` → `cause_confidence` (frontend không dùng field này).
7. **`regime_status`** (§35): screener expose `data_status`, `regime_status`.
8. **Handling matrix `use`** (§17): thêm semantic `YES / PARTIAL / NO`.

## Context

- TASK-085 đã implement: taxonomy 8 lớp, regime split, is_financial-aware, `numeric_confidence`, `normalization_window`.
- user-test.md §39 yêu cầu DGC: break 2018, regime 2018–2025 (>=7 FY), 2021/2022 CYCLICAL_EXTREME, numeric != cause confidence, không banner đỏ, screener == detail. Các điều này đã đạt; phần còn lại là contract field bổ sung.

## Acceptance Criteria

- [x] `data_status` trên `ValuationReport` + screener item; computed theo §32 (CONFLICTED → block; SUSPICIOUS khi unresolved; VALID_WITH_CLASSIFIED_EVENTS khi có classified events; VALID; INSUFFICIENT khi <2 năm).
- [x] Unit/mapping error → `UNIT_OR_MAPPING_ERROR_CANDIDATE` (không còn gộp UNRESOLVED_MATERIAL), block fact, `DATA_STATUS=CONFLICTED`.
- [x] `numeric_coherence_score` (0..100) trong resolution + class HIGH/MEDIUM/LOW.
- [x] Materiality grade: `NON_MATERIAL / LOW_MATERIALITY / MATERIAL / CRITICAL`.
- [x] `normalization_window` gồm `candidate_years / included_years / excluded_years / reason`.
- [x] `cause_confidence` (rename) + `regime_status` trên report + screener.
- [x] Screener expose `data_status`, `regime_status` (từ canonical report, không tự tính).
- [x] Tests acceptance (§38 universal + §39 DGC) pass; toàn bộ suite + build pass.

## Constraints and Invariants

- Giữ parity screener ↔ detail (không tự tính lại IV/MOS/quality/model).
- Không hardcode DGC; mọi mã cùng pipeline.
- TCBS-only: `cause_confidence` luôn UNKNOWN.
- Giữ schema `data_anomalies[].resolution` (backward-compat: `internal_coherence` 0..1 giữ nguyên, thêm `numeric_coherence_score`).

## Implementation Tasks

- [x] `validation_gate.py`: `data_status`, `regime_status`, `cause_confidence`, `UNIT_OR_MAPPING_ERROR_CANDIDATE`, `numeric_coherence_score`, `use` trong valuation_handling.
- [x] `coherence_checker.py`: `numeric_coherence_score(0..100)`.
- [x] `materiality_checker.py`: rename grades.
- [x] `models.py`: `data_status`, `regime_status`, `cause_confidence`.
- [x] `engine.py`: wire new fields; normalization evidence (candidate/included/excluded years).
- [x] `screener.py`: expose `data_status`, `regime_status`.
- [x] Frontend: hiển thị `data_status`/`regime_status` (regime strip) + banner đỏ gồm `UNIT_OR_MAPPING_ERROR_CANDIDATE`.
- [x] Tests mới + chạy toàn bộ suite + build.

## Related Notes

- docs/user-test.md (spec nguồn), docs/tasks/TASK-20260831-085 (implementation gốc).

## Validation Evidence

```
pytest test_value_engine.py audit_fixes audit_68_symbols buffett_munger_rule_engine
      audit_integrity_verdict_exposure value_engine_validation valuation_page_contract
      live_valuation_contract vi_labels screener_api -q
  116 passed in 47.83s   (thêm 5 acceptance test: data_status taxonomy, coherence score,
                          use semantics, materiality spec names, normalization evidence)

Screener universe (334 mã có giá):
  data_status:   VALID_WITH_CLASSIFIED_EVENTS 314 | VALID 20
  regime_status: SINGLE_REGIME 333 | SPLIT_REGIME 1 (DGC)
  DGC: VALID_WITH_CLASSIFIED_EVENTS · SPLIT_REGIME · numeric_confidence HIGH · cause UNKNOWN

Parity test DGC (user-test.md §36/§39):
  data_status == canonical, regime_status == canonical, numeric_confidence == canonical
  normalization_window: comparable_regime_start 2018 · end 2025 · normalization_years >= 7
  cause_confidence == UNKNOWN

npm run build (frontend): built in 1.11s
```

## Decisions

- Giữ `internal_coherence` (0..1) + thêm `numeric_coherence_score` (0..100) để không phá frontend/backward-compat.
- `cause_confidence` luôn UNKNOWN (TCBS-only); `data_status` là kết quả của validation pipeline, không phải model gate.
- `UNIT_OR_MAPPING_ERROR_CANDIDATE` + `UNRESOLVED_MATERIAL` đều là red/blocking trong UI; unit error → `DATA_STATUS=CONFLICTED` (chặn fact).

## Result

Đã đóng các gap contract so với `docs/user-test.md`: thêm `data_status` (VALID / VALID_WITH_CLASSIFIED_EVENTS / SUSPICIOUS / CONFLICTED / INSUFFICIENT), tách `UNIT_OR_MAPPING_ERROR_CANDIDATE` khỏi UNRESOLVED_MATERIAL, `numeric_coherence_score` 0..100 (5×20, HIGH/MEDIUM/LOW), rename materiality grade `LOW_MATERIALITY`/`CRITICAL`, normalization evidence (`candidate_years/included_years/excluded_years`), rename `cause_confidence`, thêm `regime_status`, screener expose `data_status`/`regime_status`/`numeric_confidence`. Toàn universe 334 mã đều có data_status tường minh; DGC khớp §39. 116 tests pass + build OK.