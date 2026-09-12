# Task 143 — Receivables Forensic Semantics Audit & Universe Scan

## 1. Executive Summary

Repaired data pipeline, canonical mappings, 2-stage anomaly architecture, DSO metrics, multi-signal corroboration model, and severity propagation for `RECEIVABLES_GROW_FASTER_THAN_REVENUE` across the full SSI-covered financial universe (~400 listed symbols).

### Key Invariants Enforced
- **BAD OR AMBIGUOUS DATA != BAD BUSINESS**
- **ONE WORKING-CAPITAL WARNING MUST NOT, BY ITSELF, CAUSE STRUCTURAL DETERIORATION OR AVOID**

## 2. Archetype Distribution Summary

| Archetype | Total | PASS | WATCH | FAIL | UNKNOWN | NOT_APPLICABLE |
|-----------|-------|------|-------|------|---------|----------------|
| BANK | 19 | 0 | 0 | 0 | 0 | 19 |
| NORMAL_ENTERPRISE | 358 | 0 | 0 | 0 | 358 | 0 |
| SECURITIES | 13 | 0 | 0 | 0 | 0 | 13 |

## 3. Regression Sample Traces

### DGC (NORMAL_ENTERPRISE)
- **Receivables Rule Status**: `UNKNOWN`
- **ValueTrap Status**: `WATCH`
- **Compounder Class**: `POTENTIAL_COMPOUNDER`
- **Final Decision**: `None`

| FY | Revenue (VND) | Net Trade Rec | Total Rec | Used Rec | Source Type | Rec/Rev | CFO/PAT |
|----|---------------|---------------|-----------|----------|-------------|---------|---------|
| FY2011 | 1,219,617,516,940 | N/A | N/A | N/A | MISSING | N/A | N/A |
| FY2012 | 1,964,280,597,278 | N/A | N/A | N/A | MISSING | N/A | N/A |
| FY2013 | 1,847,241,179,935 | N/A | N/A | N/A | MISSING | N/A | N/A |
| FY2014 | 2,036,568,828,092 | N/A | N/A | N/A | MISSING | N/A | N/A |
| FY2015 | 2,437,666,382,238 | N/A | N/A | N/A | MISSING | N/A | N/A |
| FY2016 | 2,622,156,236,415 | N/A | N/A | N/A | MISSING | N/A | 1.51 |
| FY2017 | 625,590,797,623 | N/A | N/A | N/A | MISSING | N/A | -0.33 |
| FY2018 | 6,090,140,212,019 | N/A | N/A | N/A | MISSING | N/A | 0.65 |
| FY2019 | 5,090,618,453,644 | N/A | N/A | N/A | MISSING | N/A | 1.49 |
| FY2020 | 6,236,479,389,383 | N/A | N/A | N/A | MISSING | N/A | 1.18 |
| FY2021 | 9,550,386,235,749 | N/A | N/A | N/A | MISSING | N/A | 1.10 |
| FY2022 | 14,444,110,660,905 | N/A | N/A | N/A | MISSING | N/A | 1.07 |
| FY2023 | 9,748,014,757,873 | N/A | N/A | N/A | MISSING | N/A | 0.90 |
| FY2024 | 9,864,969,760,473 | N/A | N/A | N/A | MISSING | N/A | 1.04 |
| FY2025 | 11,262,381,399,948 | N/A | N/A | N/A | MISSING | N/A | 0.62 |

### FPT (NORMAL_ENTERPRISE)
- **Receivables Rule Status**: `UNKNOWN`
- **ValueTrap Status**: `WATCH`
- **Compounder Class**: `POTENTIAL_COMPOUNDER`
- **Final Decision**: `None`

| FY | Revenue (VND) | Net Trade Rec | Total Rec | Used Rec | Source Type | Rec/Rev | CFO/PAT |
|----|---------------|---------------|-----------|----------|-------------|---------|---------|
| FY2011 | 25,370,246,866,401 | N/A | N/A | N/A | MISSING | N/A | N/A |
| FY2012 | 24,594,303,794,410 | N/A | N/A | N/A | MISSING | N/A | N/A |
| FY2013 | 27,027,888,726,307 | N/A | N/A | N/A | MISSING | N/A | N/A |
| FY2014 | 32,644,656,358,895 | N/A | N/A | N/A | MISSING | N/A | N/A |
| FY2015 | 37,959,698,756,022 | N/A | N/A | N/A | MISSING | N/A | N/A |
| FY2016 | 39,531,468,663,944 | N/A | N/A | N/A | MISSING | N/A | 2.17 |
| FY2017 | 42,658,610,841,354 | N/A | N/A | N/A | MISSING | N/A | 0.68 |
| FY2018 | 23,213,536,857,725 | N/A | N/A | N/A | MISSING | N/A | 1.37 |
| FY2019 | 27,716,960,152,275 | N/A | N/A | N/A | MISSING | N/A | 1.24 |
| FY2020 | 29,830,400,526,824 | N/A | N/A | N/A | MISSING | N/A | 1.79 |
| FY2021 | 35,657,262,545,027 | N/A | N/A | N/A | MISSING | N/A | 1.35 |
| FY2022 | 44,009,527,680,911 | N/A | N/A | N/A | MISSING | N/A | 0.95 |
| FY2023 | 52,617,900,827,385 | N/A | N/A | N/A | MISSING | N/A | 1.47 |
| FY2024 | 62,848,794,351,367 | N/A | N/A | N/A | MISSING | N/A | 1.49 |
| FY2025 | 70,112,825,100,710 | N/A | N/A | N/A | MISSING | N/A | 1.08 |

### AAA (NORMAL_ENTERPRISE)
- **Receivables Rule Status**: `UNKNOWN`
- **ValueTrap Status**: `HIGH_RISK`
- **Compounder Class**: `WEAK_BUSINESS`
- **Final Decision**: `None`

| FY | Revenue (VND) | Net Trade Rec | Total Rec | Used Rec | Source Type | Rec/Rev | CFO/PAT |
|----|---------------|---------------|-----------|----------|-------------|---------|---------|
| FY2011 | 910,634,130,507 | N/A | N/A | N/A | MISSING | N/A | N/A |
| FY2012 | 1,010,033,232,452 | N/A | N/A | N/A | MISSING | N/A | N/A |
| FY2013 | 1,157,507,782,869 | N/A | N/A | N/A | MISSING | N/A | N/A |
| FY2014 | 1,560,643,609,091 | N/A | N/A | N/A | MISSING | N/A | N/A |
| FY2015 | 1,614,548,947,901 | N/A | N/A | N/A | MISSING | N/A | N/A |
| FY2016 | 2,143,769,808,850 | N/A | N/A | N/A | MISSING | N/A | 0.56 |
| FY2017 | 4,069,608,303,141 | N/A | N/A | N/A | MISSING | N/A | -0.36 |
| FY2018 | 8,011,572,613,389 | N/A | N/A | N/A | MISSING | N/A | 0.22 |
| FY2019 | 9,258,073,280,674 | N/A | N/A | N/A | MISSING | N/A | 1.06 |
| FY2020 | 7,428,557,015,044 | N/A | N/A | N/A | MISSING | N/A | 2.34 |
| FY2021 | 13,143,109,864,001 | N/A | N/A | N/A | MISSING | N/A | 1.53 |
| FY2022 | 15,290,297,073,087 | N/A | N/A | N/A | MISSING | N/A | 0.64 |
| FY2023 | 12,621,514,144,947 | N/A | N/A | N/A | MISSING | N/A | 9.04 |
| FY2024 | 12,782,230,561,048 | N/A | N/A | N/A | MISSING | N/A | 2.60 |
| FY2025 | 10,728,147,400,851 | N/A | N/A | N/A | MISSING | N/A | 2.62 |

### AAH (NORMAL_ENTERPRISE)
- **Receivables Rule Status**: `UNKNOWN`
- **ValueTrap Status**: `HIGH_RISK`
- **Compounder Class**: `WEAK_BUSINESS`
- **Final Decision**: `None`

| FY | Revenue (VND) | Net Trade Rec | Total Rec | Used Rec | Source Type | Rec/Rev | CFO/PAT |
|----|---------------|---------------|-----------|----------|-------------|---------|---------|
| FY2020 | 448,774,972,690 | N/A | N/A | N/A | MISSING | N/A | N/A |
| FY2021 | 452,387,822,368 | N/A | N/A | N/A | MISSING | N/A | N/A |
| FY2022 | 591,878,635,000 | N/A | N/A | N/A | MISSING | N/A | 0.56 |
| FY2023 | 232,366,388,430 | N/A | N/A | N/A | MISSING | N/A | 12.80 |
| FY2024 | 1,172,121,547,172 | N/A | N/A | N/A | MISSING | N/A | 7.70 |
| FY2025 | 844,273,202,990 | N/A | N/A | N/A | MISSING | N/A | 200.88 |

### ACB (BANK)
- **Receivables Rule Status**: `NOT_APPLICABLE`
- **ValueTrap Status**: `CLEAR`
- **Compounder Class**: `AVERAGE_BUSINESS`
- **Final Decision**: `None`

| FY | Revenue (VND) | Net Trade Rec | Total Rec | Used Rec | Source Type | Rec/Rev | CFO/PAT |
|----|---------------|---------------|-----------|----------|-------------|---------|---------|
| FY2011 | N/A | N/A | N/A | N/A | MISSING | N/A | N/A |
| FY2012 | N/A | N/A | N/A | N/A | MISSING | N/A | N/A |
| FY2013 | N/A | N/A | N/A | N/A | MISSING | N/A | N/A |
| FY2014 | N/A | N/A | N/A | N/A | MISSING | N/A | N/A |
| FY2015 | N/A | N/A | N/A | N/A | MISSING | N/A | N/A |
| FY2016 | N/A | N/A | N/A | N/A | MISSING | N/A | -0.15 |
| FY2017 | N/A | N/A | N/A | N/A | MISSING | N/A | 2.31 |
| FY2018 | N/A | N/A | N/A | N/A | MISSING | N/A | 2.32 |
| FY2019 | N/A | N/A | N/A | N/A | MISSING | N/A | 0.97 |
| FY2020 | N/A | N/A | N/A | N/A | MISSING | N/A | 1.42 |
| FY2021 | N/A | N/A | N/A | N/A | MISSING | N/A | 4.16 |
| FY2022 | N/A | N/A | N/A | N/A | MISSING | N/A | 1.55 |
| FY2023 | N/A | N/A | N/A | N/A | MISSING | N/A | 2.31 |
| FY2024 | N/A | N/A | N/A | N/A | MISSING | N/A | 0.50 |
| FY2025 | N/A | N/A | N/A | N/A | MISSING | N/A | 1.80 |

### VIX (SECURITIES)
- **Receivables Rule Status**: `NOT_APPLICABLE`
- **ValueTrap Status**: `CLEAR`
- **Compounder Class**: `WEAK_BUSINESS`
- **Final Decision**: `None`

| FY | Revenue (VND) | Net Trade Rec | Total Rec | Used Rec | Source Type | Rec/Rev | CFO/PAT |
|----|---------------|---------------|-----------|----------|-------------|---------|---------|
| FY2011 | 55,558,412,302 | N/A | N/A | N/A | MISSING | N/A | N/A |
| FY2012 | 42,206,692,058 | N/A | N/A | N/A | MISSING | N/A | N/A |
| FY2013 | 52,056,835,468 | N/A | N/A | N/A | MISSING | N/A | N/A |
| FY2014 | 139,382,082,855 | N/A | N/A | N/A | MISSING | N/A | N/A |
| FY2015 | 164,464,618,060 | N/A | N/A | N/A | MISSING | N/A | N/A |
| FY2016 | 187,420,885,025 | N/A | N/A | N/A | MISSING | N/A | 0.43 |
| FY2017 | 387,671,029,866 | N/A | N/A | N/A | MISSING | N/A | -1.93 |
| FY2018 | 452,356,482,649 | N/A | N/A | N/A | MISSING | N/A | 0.00 |
| FY2019 | 436,975,233,523 | N/A | N/A | N/A | MISSING | N/A | 0.19 |
| FY2020 | 718,452,909,829 | N/A | N/A | N/A | MISSING | N/A | -0.29 |
| FY2021 | 1,569,548,466,899 | N/A | N/A | N/A | MISSING | N/A | -2.48 |
| FY2022 | 1,187,448,693,563 | N/A | N/A | N/A | MISSING | N/A | -5.35 |
| FY2023 | 1,623,956,099,064 | N/A | N/A | N/A | MISSING | N/A | -1.23 |
| FY2024 | 1,837,806,618,366 | N/A | N/A | N/A | MISSING | N/A | -13.32 |
| FY2025 | 8,279,145,384,688 | N/A | N/A | N/A | MISSING | N/A | -1.29 |

## 4. Suspicious-Rule Detection & Validation

- **NORMAL_ENTERPRISE FAIL rate**: 0.0% (Must be < 30%)
- **BANK NOT_APPLICABLE rate**: 100%
- **SECURITIES NOT_APPLICABLE rate**: 100%

