# QPort User Test — TCBS-Only Numeric Validation & Valuation Gate

**Date:** 2026-08-31
**Scope:** Financial validation, anomaly classification, regime detection, normalization, model gating, valuation publication, screener consistency.

---

## 1. Objective

QPort phải có khả năng đánh giá toàn bộ universe cổ phiếu chỉ dựa trên:

```text
TCBS financial data
        ↓
Canonical DB
```

Không yêu cầu runtime phải:

* tìm kiếm web;
* đọc báo;
* đọc IR doanh nghiệp;
* crawl CafeF/Vietstock;
* xác minh thủ công nguyên nhân từng biến động.

Mục tiêu không phải xác định:

> “Tại sao doanh thu tăng 800%?”

Mà là xác định:

> “Biến động này có nhất quán với các chỉ tiêu tài chính khác không, có tạo structural break/cycle hay không, và valuation engine phải xử lý nó như thế nào?”

---

# 2. Fundamental Principle

Một biến động lớn:

```text
YoY +200%
YoY -70%
YoY +800%
```

KHÔNG đồng nghĩa:

```text
BAD_DATA
```

`DATA_ANOMALY` chỉ có nghĩa:

```text
UNUSUAL_MOVEMENT_DETECTED
```

Sau đó bắt buộc phải chạy resolver.

Pipeline:

```text
ANOMALY DETECTED
        ↓
CROSS-METRIC CHECK
        ↓
PERSISTENCE CHECK
        ↓
REGIME / CYCLE CLASSIFICATION
        ↓
MATERIALITY CHECK
        ↓
NORMALIZATION DECISION
```

---

# 3. Core Invariants

1. Public IV/MOS chỉ được lấy từ **Canonical Value Engine**.

2. Screener không được có valuation engine thứ hai.

3. Screener không được tự tính lại:

```text
Intrinsic Value
Required MOS
Quality Score
Model Status
Verdict
```

4. `DATA_ANOMALY` không đồng nghĩa với dữ liệu sai.

5. Valid peak/trough phải được giữ trong full-cycle normalization.

6. Structural break phải tạo một comparable regime mới.

7. Không được tự suy đoán nguyên nhân bên ngoài nếu TCBS không cung cấp evidence.

Sai:

```text
2018 = MERGER
```

Đúng:

```text
2018 = STRUCTURAL_REGIME_BREAK
external_cause = UNKNOWN
```

8. Data/model coverage gap không phải crash.

9. Không fabricate dữ liệu để làm model `VERIFIED`.

---

# 4. Validation Pipeline

```text
TCBS
 ↓
Canonical Financial Facts
 ↓
Basic Data Validation
 ↓
Numeric Anomaly Detector
 ↓
Cross-Metric Coherence
 ↓
Persistence / Mean Reversion
 ↓
Financial Regime Resolver
 ↓
Materiality Analysis
 ↓
Normalization Engine
 ↓
Archetype Router
 ↓
Model Requirement Gate
 ↓
Canonical Valuation Engine
 ↓
Publication Gate
 ↓
Screener / Valuation UI
```

Mọi mã đều phải chạy cùng pipeline.

Không hardcode:

```text
DGC
HPG
BMP
BSR
...
```

---

# 5. Status Taxonomy

Không trộn các loại status với nhau.

## 5.1 DATA_STATUS

```text
VALID
VALID_WITH_CLASSIFIED_EVENTS
SUSPICIOUS
CONFLICTED
INSUFFICIENT
```

Ý nghĩa:

### VALID

Không có vấn đề material.

### VALID_WITH_CLASSIFIED_EVENTS

Có biến động mạnh nhưng hệ thống đã xác định được pattern số liệu đủ nhất quán để sử dụng.

Ví dụ:

```text
STRUCTURAL_REGIME_BREAK
CYCLICAL_EXTREME
CASHFLOW_TIMING
SHARE_STRUCTURE_CHANGE
```

### SUSPICIOUS

Có biến động material nhưng thiếu cross-metric confirmation.

### CONFLICTED

Các financial facts tự mâu thuẫn hoặc có dấu hiệu unit/mapping problem.

### INSUFFICIENT

Thiếu dữ liệu cần thiết.

---

# 6. Numeric Event Classification

Resolver phải phân loại anomaly thành một trong các loại:

```text
NORMAL
SUSPICIOUS_ISOLATED
STRUCTURAL_REGIME_BREAK
CYCLICAL_EXTREME
EARNINGS_ONE_OFF_CANDIDATE
CASHFLOW_TIMING_CANDIDATE
SHARE_STRUCTURE_CHANGE
UNIT_OR_MAPPING_ERROR_CANDIDATE
UNRESOLVED_MATERIAL
```

---

# 7. Basic Data Validation

Trước khi phân tích business behavior phải bắt các lỗi cơ bản.

Kiểm tra:

```text
null
NaN
duplicate period
impossible zero
negative shares
negative equity where unsupported
unit mismatch
1000x scale mismatch
duplicate FY with conflicting values
period misalignment
```

Ví dụ:

```text
Revenue:
2022 = 10T
2023 = 10,500T

Profit:
2022 = 1T
2023 = 1.1T

Equity:
2022 = 8T
2023 = 8.5T
```

Revenue nhảy 1000 lần trong khi mọi thứ khác gần như không đổi.

Classification:

```text
UNIT_OR_MAPPING_ERROR_CANDIDATE
```

Không được coi là business growth.

---

# 8. Cross-Metric Coherence

Không đánh giá một metric độc lập.

Core financial vector:

```text
Revenue
Net Profit
Operating Cash Flow
Free Cash Flow
Equity
Assets
Debt
Cash
Shares Outstanding
```

Ví dụ A:

```text
Revenue +800%
Net Profit +600%
CFO +500%
Equity +250%
Debt +300%
Shares +100%
```

→ biến động có coherence cao.

Không nên gọi là bad data.

Ví dụ B:

```text
Revenue +800%
Net Profit +3%
CFO -5%
Equity +2%
Assets +1%
```

→ isolated anomaly.

Classification:

```text
SUSPICIOUS_ISOLATED
```

---

# 9. Coherence Score

Tạo:

```text
numeric_coherence_score = 0..100
```

Gợi ý:

```text
Revenue confirmation             20
Profit confirmation              20
Cash-flow confirmation           20
Balance-sheet confirmation       20
Persistence confirmation         20
```

Threshold:

```text
>= 80 HIGH
60–79 MEDIUM
< 60 LOW
```

Không cần các weight chính xác này là immutable; điều quan trọng là contract.

---

# 10. Structural Regime Break

Một structural break xảy ra khi quy mô kinh tế thay đổi mạnh và level mới tồn tại trong nhiều năm.

Điều kiện gợi ý:

```text
>= 3 major metrics change materially
AND
post-change level persists >= 2 fiscal years
```

Metrics ưu tiên:

```text
Revenue
Profit
Assets
Equity
Debt
Shares
```

Pattern:

```text
PRE REGIME

2016
2017

      ↓ break

POST REGIME

2018
2019
2020
2021...
```

Classification:

```text
STRUCTURAL_REGIME_BREAK
```

Normalization:

```text
split comparable regime
```

Không tự động exclude năm break.

---

# 11. Persistence Test

Ví dụ data error/spike:

```text
2019  5T
2020  50T
2021  5.2T
```

→ không persistent.

Ví dụ structural shift:

```text
2017  0.6T
2018  6.1T
2019  5.1T
2020  6.2T
2021  9.5T
```

→ new level persists.

Pseudo-rule:

```text
pre_level  = median(previous comparable years)
post_level = median(next comparable years)

if material difference persists:
    STRUCTURAL_REGIME_BREAK
```

---

# 12. Cyclical Extreme

Pattern:

```text
normal
 ↓
rapid expansion
 ↓
peak
 ↓
mean reversion
```

Ví dụ:

```text
Profit
2020   1T
2021   2.5T
2022   6T
2023   3.2T
2024   3.1T
2025   3.2T
```

Nếu:

```text
Revenue ↑
Profit ↑
CFO ↑
Margins ↑
```

cùng di chuyển và sau đó mean-revert:

```text
CYCLICAL_EXTREME
```

### Important

Không remove peak year.

Full-cycle normalization phải chứa:

```text
weak years
normal years
strong years
peak years
```

Nếu bỏ peak/trough thì không còn là full-cycle.

---

# 13. Earnings One-Off Candidate

Ví dụ:

```text
Revenue +5%
Profit +300%
CFO +2%
Assets +4%
```

Classification:

```text
EARNINGS_ONE_OFF_CANDIDATE
```

Handling:

```text
downweight/exclude abnormal profit
```

nếu ảnh hưởng material tới normalized earnings.

Không cần biết one-off đó là bán tài sản hay khoản khác.

---

# 14. Cash Flow Timing Candidate

Ví dụ:

```text
Revenue +7%
Profit +5%
CFO +350%
```

Classification:

```text
CASHFLOW_TIMING_CANDIDATE
```

Handling:

```text
do not extrapolate single-year CFO
use multi-year normalized CFO
```

---

# 15. Share Structure Change

Ví dụ:

```text
Shares +50%

Revenue +6%
Profit +7%
CFO +5%
Equity +5%
```

Classification:

```text
SHARE_STRUCTURE_CHANGE
```

Không coi là business regime break.

Dilution engine xử lý riêng:

```text
NON_ECONOMIC
CONFIRMED_ECONOMIC
UNEXPLAINED
```

nếu data cho phép.

---

# 16. Materiality Analysis

Mỗi anomaly phải được test theo tác động tới valuation.

Chạy:

```text
valuation_with_event
vs
valuation_without_event
```

Tạo:

```text
iv_impact_pct
normalized_earnings_impact_pct
quality_score_impact
```

Suggested levels:

```text
<5%      NON_MATERIAL
5–15%    LOW_MATERIALITY
15–25%   MATERIAL
>25%     CRITICAL
```

---

# 17. Handling Matrix

| Classification                  | Use in normalization | Action                          |
| ------------------------------- | -------------------- | ------------------------------- |
| NORMAL                          | Yes                  | Normal                          |
| CYCLICAL_EXTREME                | **Yes**              | Keep peak/trough                |
| STRUCTURAL_REGIME_BREAK         | Yes                  | Split regime                    |
| SHARE_STRUCTURE_CHANGE          | Yes                  | Per-share adjustment separately |
| CASHFLOW_TIMING_CANDIDATE       | Partial              | Downweight CFO year             |
| EARNINGS_ONE_OFF_CANDIDATE      | Partial              | Downweight affected metric      |
| SUSPICIOUS_ISOLATED             | No/Partial           | Exclude affected metric-year    |
| UNIT_OR_MAPPING_ERROR_CANDIDATE | No                   | Block affected fact             |
| UNRESOLVED_MATERIAL             | No                   | Downgrade/block valuation       |

---

# 18. Model Status

Separate from `DATA_STATUS`.

Allowed:

```text
MODEL_VERIFIED
MODEL_PARTIAL
MODEL_INCOMPLETE
MODEL_ESTIMATED
MODEL_UNVALUABLE
MODEL_UNSUPPORTED
```

## MODEL_VERIFIED

Model has:

```text
required financial data
valid archetype
sufficient normalization
no unresolved critical inconsistency
```

## MODEL_PARTIAL

Model can run but important evidence remains uncertain.

## MODEL_INCOMPLETE

Required data missing.

Example:

```text
commodity company
only 3 FY
requires >=7 FY
```

## MODEL_ESTIMATED

Model requires a non-TCBS specialized assumption that is estimated.

Example:

```text
ACV concession/right duration unavailable
```

## MODEL_UNVALUABLE

Economics cannot currently produce meaningful valuation.

Example:

```text
normalized Owner Earnings persistently negative
```

---

# 19. Current Universe Snapshot

Current observed result:

| Reason                 | Symbols | Interpretation                                    |
| ---------------------- | ------: | ------------------------------------------------- |
| MODEL_VERIFIED         |      99 | Model successfully validated                      |
| ARCHETYPE_UNKNOWN      |     173 | Industry/classification unavailable               |
| MODEL_INCOMPLETE       |      36 | Not enough 7–10Y full-cycle history               |
| MODEL_UNVALUABLE       |      12 | Owner Earnings negative/unusable                  |
| RNAV missing data      |       8 | Project/land-bank information unavailable         |
| KCN lease missing data |       5 | Lease/occupancy/project data unavailable          |
| MODEL_ESTIMATED        |       1 | ACV specialized concession/right data unavailable |

For the 99 `MODEL_VERIFIED`:

```text
72 → public IV/MOS available

remaining →
quality gate / hard reject / AVOID_QUALITY
therefore public valuation intentionally hidden
```

This behavior is expected.

---

# 20. ARCHETYPE_UNKNOWN

173 symbols currently cannot be routed because:

```text
securities.industry = UNKNOWN
```

Expected:

```text
ARCHETYPE_UNKNOWN
```

This is:

```text
CLASSIFICATION_DATA_GAP
```

not:

```text
VALIDATION_ENGINE_FAILURE
```

Acceptance:

```text
no crash
no fabricated archetype
no fabricated valuation model
no public IV/MOS
```

---

# 21. MODEL_INCOMPLETE

36 symbols lack enough history.

Example:

```text
Commodity / cyclical model
required >=7 FY
available 1–6 FY
```

Expected:

```text
MODEL_INCOMPLETE
```

This is correct behavior.

Do not fallback to:

```text
LATEST_FY DCF
```

just to generate a valuation.

---

# 22. MODEL_UNVALUABLE

12 symbols have unusable Owner Earnings or economics.

Expected:

```text
MODEL_UNVALUABLE
```

Do not force positive IV.

Do not replace negative OE with:

```text
net income
EBITDA
arbitrary multiple
```

unless the selected archetype explicitly requires another model.

---

# 23. RNAV / KCN Coverage Gaps

Examples:

```text
Real Estate:
land bank
projects
remaining inventory
ASP
legal progress
project debt

Industrial Park:
commercial land
available land
lease price
occupancy
lease duration
```

TCBS financial statements do not necessarily contain these.

Therefore:

```text
MODEL_INCOMPLETE
```

is acceptable.

This is a model-data coverage limitation.

It is not a numeric-validation bug.

---

# 24. ACV

ACV currently:

```text
MODEL_ESTIMATED
```

because specialized airport/concession/right information is unavailable.

Expected behavior:

```text
financial validation still runs
anomaly/regime classification still runs
normalization still shown

BUT

specialized valuation remains MODEL_ESTIMATED
```

Do not invent:

```text
concession_end_date
```

Do not hardcode:

```text
15 years
20 years
30 years
```

without data.

---

# 25. DGC Regression Fixture

DGC must be retained as the canonical numeric-validation regression case.

Historical data includes:

```text
2017 revenue
2.622T → 0.626T
-76.1%

2017 net profit
320B → 128B
-60%

2018 revenue
626B → 6.090T
+872.8%

2018 net profit
128B → 873B
+582%
```

Later:

```text
2021 net profit
948B → 2.514T
+165.2%

2021 CFO
1.073T → 2.620T
+144.2%

2022 net profit
2.514T → 6.037T
+140.1%

2022 CFO
2.620T → 5.937T
+126.6%
```

Expected classification must NOT simply be:

```text
DATA_ANOMALY → BAD DATA
```

---

# 26. Expected DGC Structural Resolution

2017→2018 shows simultaneous changes across:

```text
Revenue
Profit
Equity
Debt
Shares
```

and new scale persists after 2018.

Expected:

```text
classification:
STRUCTURAL_REGIME_BREAK

numeric_confidence:
HIGH

external_cause:
UNKNOWN
```

Do not label:

```text
MERGER
ACQUISITION
RESTRUCTURING
```

unless event metadata exists.

---

# 27. DGC Comparable Regime

Once structural break is detected:

```text
old regime:
2016–2017

new regime:
2018–2025
```

Current valuation should prioritize the economically comparable current regime:

```text
2018–2025
```

This provides:

```text
8 FY
```

which satisfies a >=7Y full-cycle requirement.

Expected normalization evidence:

```text
normalization_method
comparable_regime_start
comparable_regime_end
candidate_years
included_years
excluded_years
normalization_years
```

Example:

```json
{
  "normalization_method": "MID_CYCLE_MEDIAN",
  "comparable_regime_start": 2018,
  "comparable_regime_end": 2025,
  "included_years": [
    2018,
    2019,
    2020,
    2021,
    2022,
    2023,
    2024,
    2025
  ],
  "normalization_years": 8
}
```

---

# 28. DGC 2021–2022

Expected:

```text
CYCLICAL_EXTREME
```

because:

```text
profit ↑
CFO ↑
revenue ↑
then earnings mean-revert
```

Handling:

```text
include = true
```

Do not exclude 2021/2022 merely because growth exceeded an anomaly threshold.

These years are useful full-cycle observations.

---

# 29. DGC Expected UI

Do NOT display:

```text
⚠ BẤT THƯỜNG LỊCH SỬ BCTC
CẦN ĐỐI SOÁT NGUỒN
```

for every classified movement.

Instead:

## BIẾN ĐỘNG LỊCH SỬ ĐÃ PHÂN LOẠI

Example:

```text
2018
Thay đổi chế độ/quy mô tài chính
STRUCTURAL_REGIME_BREAK
Numeric confidence: HIGH

2021
Biến động chu kỳ mạnh
CYCLICAL_EXTREME

2022
Đỉnh chu kỳ
CYCLICAL_EXTREME
```

Banner red is reserved for:

```text
UNRESOLVED_MATERIAL
UNIT_OR_MAPPING_ERROR_CANDIDATE
DATA_CONFLICT
```

when material.

---

# 30. UI Severity

### Green / neutral

```text
NORMAL
VALID
```

### Blue

```text
STRUCTURAL_REGIME_BREAK
```

Informational, not error.

### Orange

```text
CYCLICAL_EXTREME
EARNINGS_ONE_OFF_CANDIDATE
CASHFLOW_TIMING_CANDIDATE
```

Requires context but not necessarily invalid.

### Red

Only:

```text
UNRESOLVED_MATERIAL
DATA_CONFLICT
UNIT_OR_MAPPING_ERROR_CANDIDATE
```

with material impact.

---

# 31. Numeric Confidence vs Cause Confidence

Separate:

```text
numeric_confidence
cause_confidence
```

Example:

```text
DGC 2018

numeric_confidence = HIGH
cause_confidence   = UNKNOWN
```

Meaning:

> QPort has strong evidence from the financial series that the scale changed materially and persistently, but the exact corporate cause cannot be determined from TCBS numbers alone.

This is acceptable.

---

# 32. Validation Gate

Pseudo-code:

```text
if data_is_fundamentally_invalid:
    DATA_STATUS = CONFLICTED
    block valuation

elif unresolved_material_anomaly:
    DATA_STATUS = SUSPICIOUS

    if IV impact is critical:
        MODEL_STATUS = MODEL_PARTIAL
        block public IV/MOS
    else:
        confidence downgrade

elif structural_break:
    split normalization regime

elif cycle_extreme:
    retain observation

continue model validation
```

---

# 33. Public Valuation Gate

Public valuation may be displayed only when:

```text
model_status == MODEL_VERIFIED
AND
no critical unresolved data issue
AND
quality gate permits publication
```

Otherwise:

```text
public_bear_iv = null
public_base_iv = null
public_bull_iv = null
public_mos = null
```

Diagnostic valuation may exist internally but must not be presented as an investable valuation.

---

# 34. Quality Gate

Quality and valuation reliability are different dimensions.

Example:

```text
MODEL_VERIFIED
Quality = LOW_QUALITY
```

Expected:

```text
AVOID_QUALITY
public IV/MOS hidden
```

This is correct.

`MODEL_VERIFIED` only means the model can be computed reliably.

It does not mean:

```text
BUY
ATTRACTIVE
HIGH QUALITY
```

---

# 35. Screener Contract

Screener must consume canonical report fields:

```text
symbol
archetype
model
model_status
confidence

quality_score
quality_status

bear_iv
base_iv
bull_iv

public_mos
required_mos

valuation_status
investment_status

data_status
regime_status
```

It must NOT independently calculate:

```text
DCF
RIM
fair P/B
Owner Earnings
Required MOS
quality score
```

---

# 36. Screener Regression Invariant

For every symbol:

```text
Screener.base_iv
==
ValuationDetail.base_iv
```

and:

```text
Screener.mos
==
ValuationDetail.mos
```

and:

```text
Screener.required_mos
==
ValuationDetail.required_mos
```

and:

```text
Screener.quality_score
==
ValuationDetail.quality_score
```

and:

```text
Screener.model_status
==
ValuationDetail.model_status
```

Any mismatch is:

```text
P0 DATA CONSISTENCY FAILURE
```

---

# 37. No-Crash Requirement

Every universe symbol must resolve to an explicit gate state.

Examples:

```text
MODEL_VERIFIED
ARCHETYPE_UNKNOWN
MODEL_INCOMPLETE
MODEL_ESTIMATED
MODEL_UNVALUABLE
MODEL_UNSUPPORTED
AVOID_QUALITY
```

No symbol should crash valuation because data is incomplete.

Expected:

```text
missing data
→ explicit status
```

not:

```text
exception
500
silent fallback
fabricated valuation
```

---

# 38. Acceptance Tests — Universal

For every symbol:

### Test A — basic validity

```text
no invalid numeric types
no impossible shares
no uncontrolled unit jumps
```

### Test B — anomaly classification

Every material detector hit must resolve to:

```text
classified event
OR
unresolved
```

Never remain only:

```text
DATA_ANOMALY
```

without handling semantics.

### Test C — normalization trace

For normalized models expose:

```text
method
window
candidate years
included years
excluded years
reason
```

### Test D — materiality

For unresolved anomaly:

```text
valuation impact measured
```

### Test E — model gate

Model status must derive from actual requirements.

### Test F — publication gate

No public IV/MOS if canonical gate blocks publication.

---

# 39. Acceptance Tests — DGC

Required:

```text
DGC structural break detected around 2017/2018
```

Required:

```text
2018–2025 current comparable regime
```

Required:

```text
2021 and 2022 retained as cycle extremes
```

Required:

```text
numeric confidence != external cause confidence
```

Required:

```text
no red unresolved-data banner
```

unless another genuinely unresolved material inconsistency exists.

Required:

```text
full-cycle normalization >= 7 comparable FY
```

Required:

```text
screener valuation == detail valuation
```

---

# 40. Acceptance Tests — Coverage Gaps

### ARCHETYPE_UNKNOWN

Expected:

```text
no valuation fabrication
```

### Insufficient history

Expected:

```text
MODEL_INCOMPLETE
```

### Negative normalized economics

Expected:

```text
MODEL_UNVALUABLE
```

where appropriate.

### RNAV/KCN missing specialized input

Expected:

```text
MODEL_INCOMPLETE
```

### ACV missing specialized concession/right data

Expected:

```text
MODEL_ESTIMATED
```

These states are successful gating behavior, not failures.

---

# 41. Definition of Success

QPort is correct when it can process the entire universe and for every stock answer:

```text
1. Is the numeric history internally usable?
2. Are unusual movements coherent or suspicious?
3. Is there a structural regime break?
4. Is there a cycle extreme?
5. Which years/metrics belong in normalization?
6. Is the anomaly material to valuation?
7. Is enough data available for this archetype/model?
8. Can valuation be published?
9. What is the confidence?
10. What is the investment verdict?
```

Without needing to know the real-world narrative behind every financial movement.

---

# 42. Final Architecture

```text
TCBS
 │
 ▼
Canonical Facts
 │
 ▼
Numeric Validation
 │
 ├── Basic Integrity
 ├── Anomaly Detection
 ├── Cross-Metric Coherence
 ├── Persistence
 ├── Regime Detection
 ├── Cycle Detection
 └── Materiality
 │
 ▼
Normalization Policy
 │
 ▼
Archetype / Model Requirements
 │
 ▼
Canonical Value Engine
 │
 ▼
Publication Gate
 │
 ├── Screener
 ├── Valuation Detail
 └── Portfolio Analytics
```

## Final Principle

> **QPort does not need to know why every anomaly happened. It must know whether the financial behavior is internally coherent, economically comparable, material to valuation, and safe to use.**

DGC is the reference implementation for this principle, but the rules must remain generic and deterministic for the full Vietnamese equity universe.
