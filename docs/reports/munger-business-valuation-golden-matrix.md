# Golden Symbol Munger Business & Valuation Matrix (Task 137)

Matrix verified against real PostgreSQL canonical financial facts (`qport_finance.canonical_facts`).

| Symbol | Archetype | History | Readiness | Financial Quality | Earnings Quality | Accounting | ValueTrap | Compounder | Current Price | Bear IV | Base IV | Bull IV | Actual MOS | Required MOS | MOS Gate | Decision | Primary Reason |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| ACB | BANK | FY2011-FY2025 (15Y) | READY | PASS | NOT_APPLICABLE | PASS | CLEAR | AVERAGE_BUSINESS | 24,000 d | 18,117 d | 27,056 d | 35,051 d | 11.3% | 30.0% | FAIL | **WAIT_FOR_MOS** | Doanh nghiệp có chất lượng tốt (AVERAGE_BUSINESS) nhưng mức giá hiện tại (MOS 11.3%) chưa đạt Biên an toàn yêu cầu (30.0%). |
| DGC | NORMAL_ENTERPRISE | FY2011-FY2025 (15Y) | READY | PASS | PASS | PASS | HIGH_RISK | DETERIORATING_BUSINESS | 100,000 d | 65,870 d | 80,704 d | 102,112 d | -23.9% | 40.0% | FAIL | **AVOID** | Phát hiện rủi ro tài chính nghiêm trọng (RECEIVABLES_GROW_FASTER_THAN_REVENUE). |
| FPT | NORMAL_ENTERPRISE | FY2011-FY2025 (15Y) | READY | PASS | PASS | PASS | CLEAR | POTENTIAL_COMPOUNDER | 130,000 d | 60,199 d | 95,283 d | 141,263 d | -36.4% | 25.0% | FAIL | **WAIT_FOR_MOS** | Doanh nghiệp có chất lượng tốt (POTENTIAL_COMPOUNDER) nhưng mức giá hiện tại (MOS -36.4%) chưa đạt Biên an toàn yêu cầu (25.0%). |
| VIX | SECURITIES | FY2011-FY2025 (15Y) | READY | PASS | NOT_APPLICABLE | PASS | CLEAR | WEAK_BUSINESS | 12,000 d | 16,246 d | 29,398 d | 38,552 d | 59.2% | 40.0% | PASS | **WAIT_FOR_MOS** | Doanh nghiệp có chất lượng tài chính yếu, không đạt tiêu chí mua dài hạn. |
| AAA | NORMAL_ENTERPRISE | FY2011-FY2025 (15Y) | READY | FAIL | PASS | PASS | HIGH_RISK | WEAK_BUSINESS | 10,000 d | 8,418 d | 10,314 d | 13,050 d | 3.0% | 40.0% | FAIL | **AVOID** | Phát hiện rủi ro tài chính nghiêm trọng (WEAK_PROFITABILITY_ROE). |
| AAH | NORMAL_ENTERPRISE | FY2020-FY2025 (6Y) | READY | FAIL | PASS | PASS | HIGH_RISK | WEAK_BUSINESS | 8,000 d | 12,272,287,582 d | 15,036,048,810 d | 19,024,540,406 d | 100.0% | 40.0% | PASS | **AVOID** | Phát hiện rủi ro tài chính nghiêm trọng (WEAK_PROFITABILITY_ROE, UNSTABLE_EARNINGS_HISTORY). |
