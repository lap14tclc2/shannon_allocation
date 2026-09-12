# QPort Repository Enum & UI Leakage Audit Report

- **Date**: 2026-09-12
- **Branch**: `feature/buffett-munger-refactor`
- **Scope**: Repository-wide audit of Backend/Domain Enums, API Serialization, and Frontend UI Leakage.

---

## 1. Executive Summary

Audit toàn bộ hệ thống QPort để phát hiện và loại bỏ triệt để các mã máy (internal machine codes / raw enums) như `RECEIVABLES_GROW_FASTER_THAN_REVENUE`, `POSSIBLE_VALUE_TRAP`, `BUILD_RESERVE_FIRST`, `NOT_APPLICABLE`, `UNKNOWN` khỏi giao diện người dùng.

---

## 2. Complete Enum & Status Code Inventory

| Enum / Status | Defined At | Used At | UI Leakage Risk | Centralized Semantic Mapping | Action Taken |
|---|---|---|---|---|---|
| `DimensionStatus` | `munger_models.py` | `munger_analyzer.py` | **USER-FACING** | `STATUS_VIETNAMESE` / `STATUS_MAP` | Mapped to "Đạt", "Cần theo dõi", "Không đạt", "Chưa đủ dữ liệu" |
| `ConfidenceLevel` | `munger_models.py` | `munger_analyzer.py` | API INTERNAL CONTRACT | `STATUS_VIETNAMESE` / `STATUS_MAP` | Mapped to "Độ tin cậy cao", "Độ tin cậy trung bình" |
| `FindingSeverity` | `munger_models.py` | `munger_forensics.py` | **USER-FACING** | `STATUS_VIETNAMESE` / `STATUS_MAP` | Mapped to "Rủi ro rất cao", "Rủi ro cao", "Cần theo dõi" |
| `DeteriorationClassification` | `munger_models.py` | `munger_forensics.py` | **USER-FACING (f-string interpolation)** | `DETERIORATION_VIETNAMESE` / `DETERIORATION_MAP` | Fixed backend string interpolation & mapped in presentation layer |
| `CompounderClassification` | `munger_models.py` | `munger_analyzer.py` | **USER-FACING (f-string interpolation)** | `CLASSIFICATION_VIETNAMESE` / `CLASSIFICATION_MAP` | Fixed backend string interpolation & mapped in presentation layer |
| `HistoryDepthClass` | `munger_models.py` | `munger_history_builder.py` | API INTERNAL CONTRACT | `STATUS_VIETNAMESE` | Mapped to "Lịch sử sâu", "Dữ liệu khả thi" |
| `QualityTier` | `quality_scorer.py` | `quality_scorer.py` | **USER-FACING** | `QUALITY_TIER_VIETNAMESE` | Fixed string formatting in `quality_scorer.py` |
| `HardRejectReason` | `quality_scorer.py` | `quality_scorer.py` | **USER-FACING** | `HARD_REJECT_REASON_VIETNAMESE` | Added Vietnamese mapping dictionary |
| `EconomicArchetype` | `archetypes.py` | `munger_analyzer.py` | **USER-FACING** | `ARCHETYPE_VIETNAMESE` / `ARCHETYPE_MAP` | Mapped to "Doanh nghiệp thông thường", "Ngân hàng thương mại", "Công ty chứng khoán" |
| `InvestmentDecisionState` | `policy/decision_engine.py` | `munger_analyzer.py` | **USER-FACING** | `DECISION_VIETNAMESE` / `DECISION_MAP` | Mapped to "Có thể mua", "Chờ biên an toàn", "Ưu tiên củng cố quỹ dự phòng" |
| `ValueTrapStatus` | `value_trap.py` | `munger_analyzer.py` | **USER-FACING (f-string interpolation)** | `VALUETRAP_VIETNAMESE` / `VALUETRAP_MAP` | Fixed backend string interpolation & mapped in presentation layer |
| `MOSGate` | `canonical_valuation.py` | `munger_analyzer.py` | **USER-FACING** | `STATUS_VIETNAMESE` / `STATUS_MAP` | Mapped to "Đạt", "Không đạt", "Chưa xác định" |
| `Q7Classification` | `munger_thesis_challenge.py` | `munger_thesis_challenge.py` | **USER-FACING (f-string interpolation)** | `Q7_CLASSIFICATION_VIETNAMESE` | Fixed string interpolation in `munger_thesis_challenge.py` line 430 |
| `SurvivalReserveStatus` | `personal_finance/domain.py` | `CapitalPage.jsx` | **DANGEROUS FALLBACK** | `STATUS_VIETNAMESE` / `STATUS_MAP` | Fixed raw fallback in `CapitalPage.jsx` |
| `ForensicFindingCode` (20 codes) | `munger_forensics.py` | `munger_analyzer.py` | **USER-FACING** | `FINDING_TITLES` / `FINDING_NARRATIVE_TEMPLATES` | Mapped 100% 20 codes to Vietnamese financial titles & narrative objects |

---

## 3. UI Leakage Locations & Actions Taken

1. **`munger_analyzer.py`**:
   - Fixed `explanation` string at line 218: `f"Đánh giá Bẫy giá trị: {get_vietnamese_valuetrap(vt_status)}. Trạng thái cấu trúc: {get_vietnamese_deterioration(structural_class)}."`
   - Fixed `fail_reasons` string at line 284: Replaced raw enum interpolation with `get_vietnamese_valuetrap` & `get_vietnamese_deterioration`.
   - Fixed `decision_reason` at line 307: Replaced raw `compounder_class` interpolation with `get_vietnamese_classification(compounder_class)`.

2. **`munger_thesis_challenge.py`**:
   - Fixed `q7_detail` string at line 430: Replaced raw `q7_class` interpolation (e.g. `POSSIBLE_VALUE_TRAP`) with `Q7_CLASSIFICATION_VIETNAMESE[q7_class]`.

3. **`quality_scorer.py`**:
   - Added `QUALITY_TIER_VIETNAMESE` & `HARD_REJECT_REASON_VIETNAMESE` dictionary to format scorecard narrative summaries into investor-facing Vietnamese.

4. **`CapitalPage.jsx`**:
   - Fixed line 107 raw fallback `Dự phòng: {data.durability?.survival_reserve_status || 'UNKNOWN'}` by wrapping in `formatStatus(data.durability?.survival_reserve_status)`.

5. **`vietnamese_presenter.py` & `vietnameseSemantics.js`**:
   - Added complete coverage for all 16 Enum groups and 20 forensic finding codes.

---

## 4. Verification

- Automated Semantic Coverage Test: `python/portfolio/tests/test_enum_semantic_coverage.py` passed 100%.
- UI Raw-Enum Regression Test: `python/portfolio/tests/test_ui_raw_enum_regression.py` passed 100%.
- Frontend Production Build `npm run build`: Exit code 0.
