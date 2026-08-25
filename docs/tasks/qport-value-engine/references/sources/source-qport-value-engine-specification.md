---
id: SRC-QVE-001
title: "QPort Buffett-Inspired Value Engine — original implementation specification"
type: source
status: verified
accessed: 2026-08-25
---

# QPort Buffett-Inspired Value Engine — Original Specification

This source note preserves the complete user-provided proposal. `verified` means the source was preserved faithfully; it does not promote proposed implementation decisions or time-sensitive market assumptions to verified facts.

## Source content

# QPort Buffett-Inspired Value Engine — Implementation Specification v1.0

**Status:** Proposed  
**Date:** 2026-08-25  
**Language:** Vietnamese  
**Target system:** QPort — Vietnamese buy-and-hold portfolio information system  
**AI dependency:** Optional; never required for valuation calculations

---

## 1. Mục tiêu

Xây dựng một hệ thống định giá cổ phiếu theo triết lý đầu tư giá trị của Warren Buffett, sử dụng dữ liệu tài chính có cấu trúc và các phép tính xác định (deterministic), có thể kiểm thử và audit.

Hệ thống phải trả lời năm câu hỏi:

1. Dữ liệu có đủ tin cậy để phân tích không?
2. Doanh nghiệp có đặc tính kinh tế đủ tốt để nắm giữ dài hạn không?
3. Lợi nhuận thực sự dành cho chủ sở hữu — Owner Earnings — là bao nhiêu?
4. Giá trị nội tại hợp lý nằm trong khoảng nào?
5. Giá thị trường hiện tại đang phản ánh những giả định tăng trưởng nào và có margin of safety hay không?

Đây là hệ thống **Buffett-inspired**, không phải tuyên bố tái tạo chính xác quy trình cá nhân của Warren Buffett. Buffett không sử dụng một công thức duy nhất; giá trị nội tại luôn phụ thuộc vào ước tính dòng tiền tương lai, chất lượng doanh nghiệp và sự hiểu biết của nhà đầu tư.

---

## 2. Nguyên tắc thiết kế

### 2.1 Deterministic first

Cùng dữ liệu, cùng policy version và cùng assumptions phải luôn tạo cùng một kết quả.

AI không được tham gia vào:

- phép tính tài chính;
- chuẩn hóa lợi nhuận;
- lựa chọn discount rate;
- tạo dữ liệu còn thiếu;
- thay đổi giả định;
- xác nhận giá trị nội tại;
- tạo giao dịch.

### 2.2 Information only

QPort Value Engine cung cấp dữ liệu, chẩn đoán và valuation report. Nó không được:

- tự động BUY/SELL;
- tự động thay thế cổ phiếu;
- tự động phân bổ danh mục;
- tự động tái đầu tư cổ tức;
- thay đổi shares hoặc cash;
- tạo ledger event.

Chỉ explicit ledger event do người dùng xác nhận mới được thay đổi portfolio state.

### 2.3 Range, not false precision

Hệ thống phải trả về Bear/Base/Bull range, sensitivity và confidence. Không được trình bày fair value như một con số chính xác tuyệt đối.

### 2.4 Per-share economics

Ưu tiên dữ liệu trên mỗi cổ phiếu:

- revenue/share;
- EPS;
- CFO/share;
- Owner Earnings/share;
- book value/share;
- dividend/share;
- diluted share count.

Tăng trưởng tổng lợi nhuận không đủ nếu số cổ phiếu tăng nhanh hơn lợi nhuận.

### 2.5 Sector-specific models

Không dùng một mô hình cho mọi ngành. Ngân hàng, bảo hiểm, bất động sản, holding và doanh nghiệp phi tài chính phải có model routing riêng.

### 2.6 Full lineage

Mỗi kết quả phải truy ngược được về:

- nguồn dữ liệu;
- kỳ báo cáo;
- report version;
- công thức;
- assumptions;
- policy version;
- valuation timestamp;
- kết quả trung gian.

---

## 3. Nền tảng triết lý Buffett

### 3.1 Intrinsic value

Giá trị nội tại là giá trị hiện tại của dòng tiền có thể được rút khỏi doanh nghiệp trong phần đời còn lại của doanh nghiệp.

Nguồn: [Berkshire Hathaway 1994 Shareholder Letter](https://www.berkshirehathaway.com/letters/1994.html).

### 3.2 Owner Earnings

Owner Earnings được xấp xỉ bằng:

```text
Net Income
+ Depreciation, Amortization and other non-cash charges
− Maintenance CAPEX
− Additional working capital required to maintain the business
```

Nguồn: [Berkshire Hathaway 1986 Shareholder Letter](https://www.berkshirehathaway.com/letters/1986.html).

### 3.3 Business quality

Các đặc tính được ưu tiên:

- earning power đã được chứng minh;
- lợi nhuận trên vốn tốt;
- ít hoặc không phụ thuộc vào nợ quá mức;
- hoạt động kinh doanh có thể hiểu được;
- quản trị và phân bổ vốn hợp lý;
- lợi thế cạnh tranh bền vững;
- khả năng tái đầu tư vốn ở tỷ suất cao.

Nguồn: [Berkshire Hathaway 1986 Letter](https://www.berkshirehathaway.com/letters/1986.html) và [1992 Letter](https://www.berkshirehathaway.com/letters/1992.html).

### 3.4 Capital allocation

Retained earnings chỉ tạo giá trị khi được tái đầu tư ở tỷ suất hấp dẫn. Một hoạt động cốt lõi tốt có thể che giấu việc phân bổ vốn kém ở các thương vụ hoặc dự án khác.

Nguồn: [Berkshire Hathaway 1984 Shareholder Letter](https://www.berkshirehathaway.com/letters/1984.html).

---

## 4. Kiến trúc tổng thể

```text
Financial Data Sources
        ↓
Raw Financial Statements
        ↓
Validation & Normalization
        ↓
Canonical Financial Snapshots
        ↓
Sector Classification
        ↓
Business Quality Diagnostics
        ↓
Normalized Earnings / Owner Earnings
        ↓
Sector-Specific Valuation Models
        ↓
Bear / Base / Bull Scenarios
        ↓
Sensitivity & Reverse Valuation
        ↓
Margin of Safety & Confidence
        ↓
Immutable Valuation Report
        ↓
Optional AI Explanation
```

### 4.1 Module boundaries

```text
fundamental_data/
  ingestion
  canonicalization
  validation

fundamental_analysis/
  per_share_metrics
  profitability
  balance_sheet
  capital_allocation
  dilution
  quality_diagnostics

valuation/
  normalization
  owner_earnings
  dcf
  earnings_power
  dividend_discount
  residual_income
  justified_pb
  sum_of_parts
  rnav
  reverse_valuation
  sensitivity

valuation_policy/
  assumptions
  sector_routing
  thresholds
  versioning

reporting/
  valuation_report
  evidence
  warnings
  history

ai_optional/
  document_extraction
  report_summary
  grounded_chat
```

---

## 5. Data contract

### 5.1 Metadata bắt buộc

```yaml
ticker: FPT
exchange: HOSE
sector_code: technology_services
fiscal_period: 2026-Q2
period_start: 2026-01-01
period_end: 2026-06-30
report_type: interim
consolidated: true
audit_status: reviewed
restated: false
currency: VND
unit_multiplier: 1000000000
source: official_disclosure
published_at: 2026-07-30T00:00:00+07:00
retrieved_at: 2026-08-25T00:00:00+07:00
```

Không được trộn:

- báo cáo riêng và hợp nhất;
- quarterly và year-to-date;
- dữ liệu đã điều chỉnh và chưa điều chỉnh;
- VND, nghìn VND, triệu VND và tỷ VND;
- basic shares và diluted shares.

### 5.2 Income statement

```text
revenue
cost_of_goods_sold
gross_profit
operating_expenses
operating_profit
ebit
interest_income
interest_expense
profit_before_tax
income_tax
net_income
net_income_parent
eps_basic
eps_diluted
```

### 5.3 Balance sheet

```text
cash
cash_equivalents
short_term_investments
receivables
inventory
current_assets
fixed_assets
intangible_assets
total_assets
short_term_debt
long_term_debt
total_debt
total_liabilities
minority_interest
shareholders_equity
```

### 5.4 Cash-flow statement

```text
cash_flow_operations
capital_expenditure
cash_flow_investing
cash_flow_financing
acquisitions
asset_disposals
dividends_paid
share_issuance_cash
share_buyback_cash
debt_issuance
debt_repayment
```

### 5.5 Share and corporate-action data

```text
weighted_average_basic_shares
weighted_average_diluted_shares
ending_shares
treasury_shares
esop_shares
rights_issue_shares
private_placement_shares
stock_dividend_ratio
cash_dividend_per_share
split_ratio
```

### 5.6 Market data

```text
market_price
price_timestamp
price_source
price_freshness
market_cap
```

Nếu giá thiếu hoặc stale, hệ thống vẫn có thể tính intrinsic value nhưng không được tính margin of safety bằng giá giả định không được khai báo.

---

## 6. Data Quality Gate

### 6.1 Trạng thái

```text
PASS
PASS_WITH_WARNINGS
INSUFFICIENT_DATA
INCONSISTENT_DATA
STALE_DATA
UNSUPPORTED_SECTOR
```

### 6.2 Kiểm tra bắt buộc

1. Có ít nhất 5 năm dữ liệu annual để định giá; ưu tiên 10 năm.
2. Balance sheet reconciliation nằm trong tolerance cho phép.
3. Đơn vị tiền tệ nhất quán.
4. Không trộn báo cáo riêng và hợp nhất.
5. Không double-count dữ liệu year-to-date.
6. Share count phản ánh stock dividend, split và issuance.
7. Phát hiện kỳ bị restated.
8. Không tự thay missing value bằng 0.
9. Không tính trailing twelve months khi thiếu kỳ thành phần.
10. Gắn audit/review status cho từng kỳ.

### 6.3 Điều kiện chặn valuation

Valuation phải bị chặn khi:

- thiếu share count đáng tin cậy;
- đơn vị tiền tệ không xác định;
- dữ liệu lợi nhuận và dòng tiền không khớp kỳ;
- sector chưa được hỗ trợ;
- không đủ dữ liệu cho model được chọn;
- normalized earnings không thể xác định hợp lý.

---

## 7. Sector routing

| Nhóm doanh nghiệp | Primary model | Cross-check model |
|---|---|---|
| Công nghệ và dịch vụ | Owner Earnings DCF | EPV, historical multiples |
| Sản xuất và hóa chất | Mid-cycle Owner Earnings DCF | EPV, EV/EBIT |
| Ngân hàng | Residual Income | Justified P/B |
| Bảo hiểm | Residual Income hoặc SOTP | P/B |
| Điện, nước, hạ tầng | FCFE hoặc DDM | SOTP |
| Holding | Sum of the Parts | Look-through earnings |
| Bất động sản | RNAV | Normalized earnings |
| Bán lẻ | Owner Earnings DCF | EPV, EV/EBIT |

Không được tự động fallback từ một model không phù hợp sang generic DCF mà không báo lỗi.

---

## 8. Business Quality Diagnostics

Quality diagnostics không được trực tiếp sinh BUY/SELL signal.

### 8.1 Circle of competence

Do người dùng xác nhận:

```text
UNDERSTOOD
PARTIALLY_UNDERSTOOD
NOT_UNDERSTOOD
UNREVIEWED
```

### 8.2 Earnings consistency

```text
positive_net_income_years
positive_cfo_years
revenue_cagr_5y
eps_cagr_5y
owner_earnings_cagr_5y
operating_margin_stability
earnings_volatility
```

### 8.3 Profitability

```text
roe
roic
roa
gross_margin
operating_margin
net_margin
fcf_margin
```

### 8.4 Return on incremental invested capital

```text
ROIIC =
Change in normalized NOPAT
/
Change in invested capital
```

ROIIC chỉ được tính khi hai đầu kỳ đủ xa và invested capital được chuẩn hóa nhất quán.

### 8.5 Financial resilience

```text
net_debt_to_ebitda
interest_coverage
debt_to_equity
current_ratio
cfo_to_debt
cash_to_short_term_debt
```

Ngưỡng phải theo ngành; không áp dụng các chỉ số này máy móc cho ngân hàng.

### 8.6 Earnings quality

```text
cfo_to_net_income
fcf_to_net_income
accrual_ratio
receivable_growth_vs_revenue
inventory_growth_vs_revenue
```

### 8.7 Per-share economics

```text
revenue_per_share
eps_basic
eps_diluted
cfo_per_share
owner_earnings_per_share
book_value_per_share
dividend_per_share
share_count_cagr
```

### 8.8 Capital-allocation diagnostics

Theo dõi chuỗi:

```text
Retained earnings / Capital raised
        ↓
Balance-sheet destination
        ↓
Productive operating assets
        ↓
Revenue, NOPAT, CFO and Owner Earnings
        ↓
Per-share outcome
```

### 8.9 Dilution warnings

Ví dụ rule:

```yaml
rule_id: DILUTION_001
condition: share_count_cagr_3y > net_income_cagr_3y
severity: warning
message: Share count is growing faster than net income.
```

```yaml
rule_id: CASH_QUALITY_001
condition: cfo_to_net_income_3y_average < configured_threshold
severity: warning
message: Operating cash flow has persistently lagged reported profit.
```

Ngưỡng phải nằm trong versioned policy, không hard-code rải rác trong application code.

---

## 9. Normalized Earnings Engine

### 9.1 Mục đích

Loại bỏ ảnh hưởng của:

- lợi nhuận bất thường;
- asset disposal;
- khoản thu nhập hoặc chi phí one-off;
- chu kỳ hàng hóa;
- tax benefit không lặp lại;
- biến động working capital ngắn hạn;
- năm đỉnh hoặc đáy bất thường.

### 9.2 Policy hỗ trợ

```yaml
normalization:
  method: weighted_average
  years: 5
  weights: [0.10, 0.15, 0.20, 0.25, 0.30]
  exclude_one_off_items: true
  cycle_adjustment: sector_specific
```

Các method tối thiểu:

- median 5Y;
- simple average 5Y;
- weighted average 5Y;
- mid-cycle margin;
- user-specified normalized value.

Mọi manual override phải có reason và audit trail.

---

## 10. Owner Earnings Engine

### 10.1 Công thức

```text
Owner Earnings
= Net Income attributable to parent
+ Depreciation and amortization
+ Approved non-cash charges
− Maintenance CAPEX
− Required increase in working capital
```

### 10.2 Maintenance CAPEX policies

#### Conservative

```text
maintenance_capex = total_capex
```

Thường dùng cho Bear scenario.

#### Depreciation proxy

```text
maintenance_capex = normalized_depreciation_and_amortization
```

Chỉ dùng khi business model và asset base tương đối ổn định.

#### User-defined

Người dùng nhập maintenance CAPEX từ nghiên cứu thuyết minh.

```yaml
maintenance_capex:
  method: user_defined
  amount: 1500000000000
  source_note: Annual report 2025, CAPEX section
  reason: Excludes disclosed expansion project
```

#### Scenario range

```text
Bear: total CAPEX
Base: normalized D&A or reviewed estimate
Bull: reviewed maintenance CAPEX estimate
```

### 10.3 Working-capital policy

```text
required_delta_nwc =
normalized_operating_working_capital_ratio
× change_in_revenue
```

Không dùng biến động working capital của một kỳ bất thường làm giả định dài hạn.

---

## 11. Valuation Models

### 11.1 Owner Earnings DCF

```text
Intrinsic operating value =
Σ OwnerEarnings(t) / (1 + r)^t
+ TerminalValue / (1 + r)^n
```

```text
TerminalValue =
OwnerEarnings(n+1) / (r − g)
```

```text
Equity value =
Operating value
+ Excess cash
+ Non-operating investments
− Debt
− Minority interest
− Other senior claims
```

```text
Intrinsic value per share =
Equity value / diluted shares
```

Guardrails:

- `terminal_growth < discount_rate`;
- terminal growth không được vượt quá giới hạn policy dài hạn;
- sử dụng diluted shares;
- không double-count cash và investment income;
- không trừ debt hai lần;
- cảnh báo nếu terminal value chiếm tỷ trọng quá lớn.

### 11.2 Earnings Power Value

```text
EPV operating value =
Normalized Owner Earnings / required_return
```

Điều chỉnh thêm excess cash, investments, debt và minority interest.

EPV phù hợp để định giá không tăng trưởng hoặc cross-check DCF.

### 11.3 Dividend Discount Model

```text
Value = Dividend(next_year) / (required_return − dividend_growth)
```

Chỉ áp dụng khi:

- cổ tức phản ánh khả năng phân phối tiền;
- payout policy ổn định;
- tăng trưởng cổ tức có thể ước tính;
- `dividend_growth < required_return`.

### 11.4 Residual Income Model — ngân hàng

```text
Residual Income(t) =
Net Income(t) − required_return × opening_equity(t)
```

```text
Equity value =
Current book value
+ present value of future residual income
```

Các input ngân hàng:

- book value;
- normalized ROE;
- cost of equity;
- equity growth;
- payout ratio;
- NPL;
- loan-loss coverage;
- credit cost;
- CAR;
- NIM và CASA nếu có.

Không dùng CFO hoặc EV/EBITDA truyền thống để định giá ngân hàng.

### 11.5 Justified P/B — ngân hàng

```text
Justified P/B =
(ROE − long_term_growth)
/
(cost_of_equity − long_term_growth)
```

Phải sử dụng normalized sustainable ROE, không dùng ROE đỉnh chu kỳ.

### 11.6 Sum of the Parts

```text
SOTP value =
Σ segment values
+ listed investments
+ unlisted investments
+ excess cash
− debt
− holding costs
− applicable holding discount
```

Mỗi segment phải lưu model và assumptions riêng.

### 11.7 RNAV

```text
RNAV =
Σ project net present values
+ cash and investments
− debt
− completion costs
− taxes
− execution discount
```

RNAV cần project-level evidence; nếu thiếu phải trả `INSUFFICIENT_DATA`.

---

## 12. Scenario Engine

### 12.1 Cấu hình mẫu

```yaml
scenarios:
  bear:
    growth_years_1_5: 0.04
    terminal_growth: 0.02
    discount_rate: 0.15
    maintenance_capex_policy: conservative

  base:
    growth_years_1_5: 0.08
    terminal_growth: 0.03
    discount_rate: 0.13
    maintenance_capex_policy: depreciation_proxy

  bull:
    growth_years_1_5: 0.12
    terminal_growth: 0.04
    discount_rate: 0.11
    maintenance_capex_policy: user_defined
```

Đây chỉ là cấu trúc minh họa, không phải default rate cho thị trường Việt Nam. Discount rate, inflation, risk-free rate và growth assumptions phải là dữ liệu cấu hình có ngày hiệu lực và được kiểm chứng hiện hành trước khi sử dụng.

### 12.2 Output

```text
Bear intrinsic value
Base intrinsic value
Bull intrinsic value
Weighted intrinsic value, nếu policy cho phép
Scenario spread
Terminal-value contribution
```

---

## 13. Margin of Safety

```text
Margin of Safety =
1 − Market Price / Intrinsic Value
```

Hệ thống chỉ trả valuation state:

```text
MATERIAL_DISCOUNT
MODERATE_DISCOUNT
NEAR_FAIR_VALUE
ABOVE_FAIR_VALUE
VALUATION_UNRELIABLE
PRICE_UNAVAILABLE
```

Các threshold phải do versioned policy định nghĩa. Không map trực tiếp state sang BUY/SELL.

---

## 14. Reverse DCF

Reverse DCF giải phương trình để tìm mức tăng trưởng mà giá thị trường đang yêu cầu.

Ví dụ output:

```yaml
market_price: 95000
required_return: 0.13
terminal_growth: 0.03
implied_owner_earnings_cagr_10y: 0.118
historical_owner_earnings_cagr_5y: 0.092
roiic_5y: 0.145
```

Reverse DCF phải trả lời:

- implied growth là bao nhiêu;
- implied margin là bao nhiêu nếu giữ growth cố định;
- assumptions nào nhạy cảm nhất;
- implied expectations có cao hơn lịch sử và khả năng tái đầu tư hay không.

Không tự kết luận giá cao/thấp nếu dữ liệu nền không đủ tin cậy.

---

## 15. Sensitivity Analysis

Tối thiểu phải có ma trận:

```text
Discount rate × Terminal growth
Discount rate × Near-term growth
Operating margin × Revenue growth
Maintenance CAPEX × Growth
```

Các cảnh báo:

```text
TERMINAL_VALUE_DOMINANT
HIGH_DISCOUNT_RATE_SENSITIVITY
HIGH_GROWTH_SENSITIVITY
MAINTENANCE_CAPEX_UNCERTAIN
NORMALIZED_EARNINGS_UNSTABLE
```

---

## 16. Valuation Confidence

### 16.1 Trạng thái

```text
HIGH
MEDIUM
LOW
UNRELIABLE
```

### 16.2 Thành phần

- data completeness;
- audit/review quality;
- earnings stability;
- cash-flow stability;
- cyclicality;
- maintenance CAPEX confidence;
- scenario spread;
- terminal-value dependence;
- agreement giữa các valuation models;
- sector-model suitability.

Confidence là đánh giá về độ tin cậy của valuation, không phải xác suất giá cổ phiếu tăng.

---

## 17. Valuation Report Contract

```yaml
report_id: val_FPT_20260825_v1
ticker: FPT
valuation_date: 2026-08-25
currency: VND
policy_version: buffet_value_policy_v1
financial_snapshot_version: fs_FPT_2026Q2_v2
sector_model: owner_earnings_dcf

data_quality:
  status: PASS
  annual_years: 10
  latest_report_audit_status: reviewed
  latest_period: 2026-Q2

business_quality:
  status: PASS_WITH_WARNINGS
  circle_of_competence: UNDERSTOOD
  earnings_consistency: HIGH
  balance_sheet_resilience: STRONG
  capital_allocation: REVIEW_REQUIRED

normalized_metrics:
  normalized_net_income: null
  normalized_owner_earnings: null
  owner_earnings_per_share: null
  normalized_roe: null
  normalized_roic: null

valuation:
  bear: null
  base: null
  bull: null
  market_price: null
  base_margin_of_safety: null
  confidence: MEDIUM

reverse_dcf:
  implied_owner_earnings_growth_10y: null

warnings:
  - MAINTENANCE_CAPEX_ESTIMATED

decision_boundary:
  informational_only: true
  trade_created: false
```

`null` phải được giữ nguyên khi chưa có dữ liệu; không thay bằng 0.

---

## 18. Storage model

Các bảng hoặc aggregate đề xuất:

```text
financial_report_sources
financial_statement_facts
financial_snapshots
corporate_actions
share_count_history
sector_classifications
normalization_adjustments
valuation_policies
valuation_assumption_sets
valuation_runs
valuation_results
valuation_sensitivities
valuation_warnings
thesis_records
thesis_evidence
```

### 18.1 Immutability

- Raw source facts không được sửa trực tiếp.
- Restatement tạo version mới.
- Manual override tạo adjustment record.
- Valuation run đã hoàn tất là immutable.
- Re-run tạo report mới với version mới.
- Phải lưu code version hoặc calculation-engine version.

---

## 19. API đề xuất

```text
GET  /api/fundamentals/{ticker}
GET  /api/fundamentals/{ticker}/history
GET  /api/fundamentals/{ticker}/quality
GET  /api/fundamentals/{ticker}/dilution

GET  /api/valuation/policies
POST /api/valuation/assumption-sets
POST /api/valuation/{ticker}/run
GET  /api/valuation/{ticker}/latest
GET  /api/valuation/{ticker}/history
GET  /api/valuation/reports/{report_id}
GET  /api/valuation/reports/{report_id}/sensitivity
```

`POST /run` chỉ tạo valuation report, không tạo portfolio transaction.

---

## 20. User experience

### 20.1 Company Value page

Các section:

1. Data quality and freshness.
2. Business quality.
3. Per-share economics.
4. Owner Earnings bridge.
5. Capital allocation and dilution.
6. Bear/Base/Bull valuation.
7. Reverse DCF.
8. Sensitivity table.
9. Margin of safety.
10. Warnings and evidence.

### 20.2 Bắt buộc giải thích được

Khi người dùng bấm vào một số liệu, UI phải hiển thị:

- công thức;
- input periods;
- raw inputs;
- adjustments;
- assumptions;
- source;
- policy version.

### 20.3 Không sử dụng màu như lệnh giao dịch

Không dùng giao diện tạo cảm giác:

```text
Green = Buy
Red = Sell
```

Màu chỉ thể hiện data quality, warning severity hoặc valuation state.

---

## 21. Optional AI module

AI có thể:

- trích xuất dữ liệu từ PDF chưa cấu trúc;
- tìm one-off items trong thuyết minh;
- tóm tắt báo cáo thường niên;
- so sánh thuyết minh giữa hai kỳ;
- tìm nội dung về ESOP, related parties và CAPEX;
- giải thích report bằng ngôn ngữ tự nhiên;
- chat dựa trên dữ liệu QPort đã lưu.

AI không được:

- sửa raw facts;
- tự tạo số liệu;
- tự chọn normalization adjustment;
- tự thay đổi discount rate;
- tự xác nhận moat hoặc management quality;
- tính fair value khác backend;
- tạo hoặc đề xuất trade như một hành động hệ thống.

Mọi AI output phải phân loại:

```text
REPORTED_FACT
CALCULATED_METRIC
USER_ASSUMPTION
AI_INFERENCE
MISSING_INFORMATION
```

Khi AI bị tắt hoặc hết quota, toàn bộ Value Engine vẫn hoạt động bình thường.

---

## 22. Testing strategy

### 22.1 Unit tests

Kiểm thử từng công thức:

- per-share metrics;
- ROE, ROIC và ROIIC;
- Owner Earnings bridge;
- DCF discounting;
- terminal value;
- EPV;
- Residual Income;
- Justified P/B;
- margin of safety;
- reverse DCF solver;
- sensitivity matrix.

### 22.2 Golden tests

Tạo các fixture cố định cho:

- doanh nghiệp phi tài chính ổn định;
- doanh nghiệp chu kỳ;
- ngân hàng;
- doanh nghiệp có pha loãng lớn;
- dữ liệu restated;
- dữ liệu thiếu;
- doanh nghiệp có net cash;
- doanh nghiệp có debt cao.

Mỗi fixture phải có expected intermediate calculations, không chỉ expected final fair value.

### 22.3 Invariant tests

Ví dụ:

```text
Higher discount rate must not increase DCF value.
Higher diluted share count must not increase value per share.
Higher debt must not increase equity value, all else equal.
Higher Owner Earnings must not reduce DCF value, all else equal.
Terminal growth must remain below discount rate.
Missing value must never silently become zero.
Valuation run must never mutate portfolio shares or cash.
```

### 22.4 Property-based tests

Sử dụng property-based testing cho DCF, reverse solver, currency scaling và share-count adjustments.

### 22.5 Reconciliation tests

- raw facts với canonical snapshot;
- annual với quarterly/TTM;
- stock dividend với per-share history;
- report restatement với valuation version;
- model result với rendered report.

---

## 23. Roadmap triển khai

### Phase 1 — Fundamental foundation

1. Canonical financial data schema.
2. Source metadata and lineage.
3. Validation engine.
4. Annual and TTM snapshots.
5. Share-count and corporate-action normalization.

### Phase 2 — Non-financial MVP

6. Per-share metrics.
7. Quality diagnostics.
8. Normalized earnings.
9. Owner Earnings engine.
10. Owner Earnings DCF.
11. EPV cross-check.
12. Bear/Base/Bull scenarios.
13. Margin of safety.
14. Reverse DCF.
15. Sensitivity matrix.

Mục tiêu đầu tiên: hỗ trợ các cấu trúc doanh nghiệp như FPT, DGC và các mảng phi tài chính của REE.

### Phase 3 — Banking model

16. Bank-specific data schema.
17. Bank quality metrics.
18. Normalized ROE.
19. Residual Income Model.
20. Justified P/B.

Mục tiêu: hỗ trợ ACB mà không sử dụng sai CFO hoặc generic enterprise DCF.

### Phase 4 — Capital allocation and monitoring

21. Capital-allocation timeline.
22. Dilution and ESOP diagnostics.
23. Fundamental change detection.
24. Investment thesis tracker.
25. Valuation history.

### Phase 5 — Portfolio integration

26. Portfolio look-through earnings.
27. Portfolio Owner Earnings.
28. Portfolio FCF yield.
29. Dividend-income projection.
30. Valuation distribution across holdings.

Mọi output vẫn informational only.

### Phase 6 — Optional AI

31. PDF extraction.
32. Note comparison.
33. Grounded explanation.
34. Gemini chat integration.

---

## 24. MVP Definition of Done

MVP hoàn thành khi:

- chạy được mà không có AI;
- hỗ trợ ít nhất một doanh nghiệp phi tài chính;
- dữ liệu thiếu không bị suy đoán;
- toàn bộ input có nguồn và kỳ báo cáo;
- Owner Earnings có bridge rõ ràng;
- Bear/Base/Bull có assumptions riêng;
- có DCF, EPV và reverse DCF;
- có sensitivity và confidence;
- kết quả reproducible;
- mọi valuation run có version;
- unit, golden và invariant tests pass;
- valuation không thay đổi portfolio ledger;
- UI giải thích được công thức và dữ liệu đầu vào.

---

## 25. Những điều không được triển khai

- Một `Buffett Score` duy nhất thay thế phân tích.
- Dùng P/E thấp làm bằng chứng cổ phiếu rẻ.
- Dùng ROE cao nhưng bỏ qua leverage.
- Dùng total profit mà bỏ qua dilution.
- Coi stock dividend là giá trị kinh tế miễn phí.
- Dùng cost basis của nhà đầu tư làm input định giá.
- Hard-code inflation hoặc discount rate vĩnh viễn.
- Dùng generic DCF cho ngân hàng.
- Tự điền dữ liệu thiếu bằng 0.
- Dùng dữ liệu ví dụ trong tài liệu như current facts.
- Chuyển valuation state thành giao dịch.
- Cho AI sửa dữ liệu hoặc phép tính.

---

## 26. Quyết định kiến trúc cuối cùng

QPort Value Engine phải tuân theo chuỗi:

```text
Data Quality
→ Business Quality
→ Normalized Per-Share Economics
→ Owner Earnings
→ Sector-Specific Valuation
→ Scenario Range
→ Reverse Expectations
→ Margin of Safety
→ Human Review
```

Hệ thống định giá là module độc lập với portfolio ledger. Thay đổi giá thị trường, fair value, margin of safety, quality warning hoặc investment thesis không được tự động thay đổi shares, cash hay transactions.

AI là lớp tùy chọn ở phía ngoài, không phải dependency của valuation core.

---

## 27. Tài liệu tham khảo chính

- [Berkshire Hathaway Shareholder Letters](https://www.berkshirehathaway.com/letters/letters.html)
- [1983 Letter — Economic Goodwill](https://www.berkshirehathaway.com/letters/1983.html)
- [1984 Letter — Capital Allocation](https://www.berkshirehathaway.com/letters/1984.html)
- [1986 Letter — Owner Earnings and Business Criteria](https://www.berkshirehathaway.com/letters/1986.html)
- [1992 Letter — Intrinsic Value and High-Return Reinvestment](https://www.berkshirehathaway.com/letters/1992.html)
- [1994 Letter — Definition of Intrinsic Value](https://www.berkshirehathaway.com/letters/1994.html)

---

**End of specification.**
