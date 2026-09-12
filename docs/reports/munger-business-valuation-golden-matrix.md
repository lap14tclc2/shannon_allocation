# Golden Symbol Munger Business & Valuation Matrix (Task 137)

Matrix verified against real PostgreSQL canonical financial facts (`qport_finance.canonical_facts`).

| Symbol | Archetype | History | Readiness | Financial Quality | Earnings Quality | Accounting | ValueTrap | Compounder | Current Price | Bear IV | Base IV | Bull IV | Actual MOS | Required MOS | MOS Gate | Decision | Primary Reason |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| ACB | BANK | FY2011-FY2025 (15Y) | READY | PASS | NOT_APPLICABLE | PASS | CLEAR | AVERAGE_BUSINESS | 22,050 đ | 18,117 đ | 27,056 đ | 35,051 đ | 18.5% | 30.0% | FAIL | **WAIT_FOR_MOS** | Doanh nghiệp có chất lượng tốt (AVERAGE_BUSINESS) nhưng mức giá hiện tại (MOS 18.5%) chưa đạt Biên an toàn yêu cầu (30.0%). |
| DGC | NORMAL_ENTERPRISE | FY2011-FY2025 (15Y) | READY | WATCH | PASS | PASS | HIGH_RISK | DETERIORATING_BUSINESS | 38,751 đ | 65,870 đ | 80,704 đ | 102,112 đ | 52.0% | 40.0% | PASS | **AVOID** | Phát hiện rủi ro tài chính nghiêm trọng (RECEIVABLES_GROW_FASTER_THAN_REVENUE). |
| FPT | NORMAL_ENTERPRISE | FY2011-FY2025 (15Y) | READY | PASS | PASS | WATCH | CLEAR | POTENTIAL_COMPOUNDER | 72,700 đ | 60,199 đ | 95,283 đ | 141,263 đ | 23.7% | 25.0% | FAIL | **WAIT_FOR_MOS** | Doanh nghiệp có chất lượng tốt (POTENTIAL_COMPOUNDER) nhưng mức giá hiện tại (MOS 23.7%) chưa đạt Biên an toàn yêu cầu (25.0%). |
| VIX | SECURITIES | FY2011-FY2025 (15Y) | READY | PASS | NOT_APPLICABLE | PASS | CLEAR | WEAK_BUSINESS | 13,250 đ | 16,246 đ | 29,398 đ | 38,552 đ | 54.9% | 40.0% | PASS | **WAIT_FOR_MOS** | Doanh nghiệp có chất lượng tài chính yếu, không đạt tiêu chí mua dài hạn. |
| AAA | NORMAL_ENTERPRISE | FY2011-FY2025 (15Y) | READY | WATCH | PASS | PASS | HIGH_RISK | WEAK_BUSINESS | 7,170 đ | 8,418 đ | 10,314 đ | 13,050 đ | 30.5% | 40.0% | FAIL | **AVOID** | Phát hiện rủi ro tài chính nghiêm trọng (WEAK_PROFITABILITY_ROE). |
| AAH | NORMAL_ENTERPRISE | FY2020-FY2025 (6Y) | READY | WATCH | PASS | PASS | HIGH_RISK | WEAK_BUSINESS | 1,900 đ | 311 đ | 381 đ | 482 đ | -398.8% | 40.0% | FAIL | **AVOID** | Phát hiện rủi ro tài chính nghiêm trọng (WEAK_PROFITABILITY_ROE, UNSTABLE_EARNINGS_HISTORY). |
