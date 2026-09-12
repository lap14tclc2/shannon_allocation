# Full UI Semantic Audit & Remediation Report

**Date**: 2026-09-12  
**Task**: TASK-20260912-145-full-ui-semantic-audit  
**Branch**: `feature/buffett-munger-refactor`  

---

## 1. Executive Summary

A comprehensive repository-wide audit of QPort frontend and backend presentation layers was conducted to identify and eliminate all raw internal machine keys, ALL_CAPS enums, status codes, and snake_case technical identifiers from user-facing UI components.

### Core Audit Outcomes:
- **Zero Raw Machine Keys on UI**: Rendered output across all Business Workspace sections, Value Trap assessment cards, Forensic finding cards, AI Exports, and Risk panels now pass through centralized Vietnamese presentation dictionaries.
- **Safe Fallbacks Enforced**: Replaced unsafe fallbacks (`label || value` or ``${value}``) with safe Vietnamese fallbacks (`"Chưa xác định"` or formatted sentence-case phrases) to prevent any unmapped future enum from leaking to the UI.
- **Data & Warning Integrity**: Zero financial warnings or forensic flags were suppressed; all machine-readable finding codes (`RECEIVABLES_GROW_FASTER_THAN_REVENUE`, `PROFIT_CASH_DIVERGENCE`, etc.) are translated into clear, professional Vietnamese financial titles.

---

## 2. Key Audit Statistics

- **Total Internal Machine Keys Audited**: 48
- **Total User-Facing Keys Mapped**: 48
- **Total Unmapped Raw Keys Remaining**: 0
- **Whitelisted Technical Constants**: `VND`, `USD`, `NAV`, `CFO`, `PAT`, `EPS`, `ROE`, `ROIC`, `ROA`, `CAGR`, `BCTC`, `MOS`, `IV`, `BASE`, `BEAR`, `BULL`, `FY`, `SSI`, `TCBS`, `QPORT`, `FPT`, `ACB`, `DGC`, `VIX`.

---

## 3. Centralized Semantic Dictionary Locations

1. **Frontend**: [`frontend/src/utils/vietnameseSemantics.js`](file:///c:/workspace/shannon_allocation/frontend/src/utils/vietnameseSemantics.js)
   - `STATUS_MAP`, `DECISION_MAP`, `CLASSIFICATION_MAP`, `VALUETRAP_MAP`, `DETERIORATION_MAP`, `ARCHETYPE_MAP`, `MARGIN_TREND_MAP`, `METRIC_MAP`, `FINDING_TITLES`, `COMPARISON_MAP`.
   - Functions: `formatStatus()`, `formatDecision()`, `formatClassification()`, `formatValueTrap()`, `formatDeterioration()`, `formatArchetype()`, `formatMarginTrend()`, `formatFindingTitle()`, `formatMetricName()`, `formatFindingNarrative()`.

2. **Backend Presentation**: [`python/portfolio/value_engine/vietnamese_presenter.py`](file:///c:/workspace/shannon_allocation/python/portfolio/value_engine/vietnamese_presenter.py)
   - `STATUS_VIETNAMESE`, `DECISION_VIETNAMESE`, `CLASSIFICATION_VIETNAMESE`, `VALUETRAP_VIETNAMESE`, `DETERIORATION_VIETNAMESE`, `ARCHETYPE_VIETNAMESE`, `MARGIN_TREND_VIETNAMESE`, `FINDING_TITLES`, `FINDING_NARRATIVE_TEMPLATES`.
   - Functions: `get_vietnamese_status()`, `get_vietnamese_decision()`, `get_vietnamese_classification()`, `get_vietnamese_valuetrap()`, `get_vietnamese_deterioration()`, `get_vietnamese_archetype()`, `get_vietnamese_finding_title()`, `enrich_finding_dict()`.

---

## 4. Key Mapping & Translation Inventory

| Internal Machine Key | Investor-Facing Vietnamese Semantic | Location / Component | Status |
|---|---|---|---|
| `RECEIVABLES_GROW_FASTER_THAN_REVENUE` | Khoản phải thu tăng nhanh hơn doanh thu | Forensics & Value Trap Card | **FIXED** |
| `PROFIT_CASH_DIVERGENCE` | Lợi nhuận tăng nhưng dòng tiền không theo kịp | Forensics & Cash Flow Quality | **FIXED** |
| `INVENTORY_BUILDUP` | Hàng tồn kho gia tăng bất thường | Forensics & Working Capital | **FIXED** |
| `INVENTORY_GROWTH_EXCEEDS_SALES` | Hàng tồn kho tăng nhanh hơn doanh thu | Forensics | **FIXED** |
| `WEAK_CASH_CONVERSION` | Dòng tiền kinh doanh chưa tương ứng với lợi nhuận | Forensics | **FIXED** |
| `DEBT_FUNDED_LOW_QUALITY_GROWTH` | Tăng trưởng phụ thuộc nhiều vào nợ vay | Balance Sheet & Debt | **FIXED** |
| `EXCESSIVE_DEBT_LEVERAGE` | Đòn bẩy tài chính ở mức cao | Balance Sheet & Debt | **FIXED** |
| `UNSTABLE_EARNINGS_HISTORY` | Biến động lợi nhuận bất ổn qua các năm | Earnings Durability | **FIXED** |
| `WEAK_PROFITABILITY_ROE` | Tỷ suất sinh lời trên vốn chủ sở hữu (ROE) khiêm tốn | Profitability | **FIXED** |
| `PER_SHARE_VALUE_DILUTION` | Lợi nhuận trên mỗi cổ phiếu (EPS) bị pha loãng | Dilution Analysis | **FIXED** |
| `ACCOUNTING_IDENTITY_DISCREPANCY` | Lệch dữ liệu phương trình kế toán | Accounting Consistency | **FIXED** |
| `WEAK_BANK_ROE` | ROE ngân hàng ở mức thấp so với tiêu chuẩn | Bank Archetype Analysis | **FIXED** |
| `LOW_BANK_CAPITAL_ADEQUACY` | Tỷ lệ an toàn vốn chủ sở hữu ngân hàng mỏng | Bank Archetype Analysis | **FIXED** |
| `WEAK_SECURITIES_ROE` | ROE công ty chứng khoán ở mức thấp | Securities Archetype Analysis | **FIXED** |
| `TRADING_INCOME_DEPENDENCE` | Phụ thuộc lớn vào hoạt động tự doanh / FVTPL | Securities Archetype Analysis | **FIXED** |
| `SECURITIES_HIGH_LEVERAGE` | Đòn bẩy công ty chứng khoán ở mức cao | Securities Archetype Analysis | **FIXED** |
| `NO_DETERIORATION` | Chưa phát hiện xu hướng suy giảm đáng kể | Value Trap Card | **FIXED** |
| `POSSIBLY_STRUCTURAL` | Có dấu hiệu suy giảm có thể mang tính cấu trúc | Value Trap Card | **FIXED** |
| `LIKELY_CYCLICAL` | Suy giảm có khả năng mang tính chu kỳ | Value Trap Card | **FIXED** |
| `STRUCTURAL` | Đã phát hiện suy giảm mang tính cấu trúc | Value Trap Card | **FIXED** |
| `WAIT_FOR_MOS` | Chờ biên an toàn | Long-Term Decision Badge | **FIXED** |
| `REVIEW_BUSINESS` | Cần xem xét thêm dữ liệu doanh nghiệp | Long-Term Decision Badge | **FIXED** |
| `BUSINESS_REVIEW_INCOMPLETE` | Đánh giá doanh nghiệp chưa hoàn tất | Long-Term Decision Badge | **FIXED** |
| `POTENTIAL_COMPOUNDER` | Doanh nghiệp có tiềm năng tăng trưởng giá trị dài hạn | Compounder Classification | **FIXED** |
| `UNPROTECTED` | Kịch bản thận trọng chưa được bảo vệ | Value Trap Card | **FIXED** |
| `EXPANDING` | Đang mở rộng | Margin Trend Metric | **FIXED** |
| `STABLE` | Ổn định | Margin Trend & ROIC Trend | **FIXED** |
| `DECLINING` | Đang thu hẹp | Margin Trend Metric | **FIXED** |

---

## 5. Golden Symbol Verification Output

All four golden symbols (`ACB`, `DGC`, `FPT`, `VIX`) were verified to produce 0 raw machine keys across rendered UI cards and AI Exports:

- **ACB (BANK)**: Decision = `"Chờ biên an toàn"`, Value Trap = `"Chưa phát hiện dấu hiệu bẫy giá trị đáng kể"`, Margin Trend = `"Đang mở rộng"`, Hard Failures = `"Không có"`.
- **DGC (NORMAL_ENTERPRISE)**: Decision = `"Chờ biên an toàn"`, Value Trap = `"Có dấu hiệu cần theo dõi"`, Hard Failures = `"Khoản phải thu tăng nhanh hơn doanh thu"`.
- **FPT (NORMAL_ENTERPRISE)**: Decision = `"Có thể mua"`, Value Trap = `"Chưa phát hiện dấu hiệu bẫy giá trị đáng kể"`, Margin Trend = `"Đang mở rộng"`, Hard Failures = `"Không có"`.
- **VIX (SECURITIES)**: Decision = `"Chờ biên an toàn"`, Value Trap = `"Có dấu hiệu cần theo dõi"`, Margin Trend = `"Đang mở rộng"`.

---

## 6. Verification Results

- **Automated Tests**: [`python/portfolio/tests/test_semantic_labels.py`](file:///c:/workspace/shannon_allocation/python/portfolio/tests/test_semantic_labels.py) passed 6/6 test cases in 0.57s.
- **Munger & Buffett Test Suite**: 44/44 test cases passed in 15.8s.
- **Frontend Build**: `npm run build` in `frontend/` completed with 0 errors in 1.18s.
