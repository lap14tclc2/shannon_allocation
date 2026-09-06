# QPort Buffett-Thorp Factor Research

_run_id: res-e72a87ac6b | generated: 2026-09-06_

## 1. Data Readiness
- Universe candidates (securities): 1523
- Universe selected: 150
- Excluded reasons: {'ticker_pattern': 28, 'insufficient_recent_bars': 3}
- Price fetch: 150/150 symbols
- Failed fetches: none
- Benchmark rows: 2252 (VNINDEX, {'start': '2016-01-01', 'end': '2026-09-06'})
- Snapshot dates: 72 (monthly last-trading-day)
- Snapshots built: 10800
- Outcome rows: 10800

## 2. PIT Integrity
- Facts filtered by `available_from <= as_of` (inferred 45d quarter / 90d annual governance lags).
- `fetched_at` is never used as publication time.
- Verified publication metadata is absent in the DB -> 100% inferred availability.

## 3. Universe Definition
- HOSE/HNX/UPCOM, 3-4 letter tickers (warrants/derivatives excluded), active securities.
- Top 150 by 20D average traded value.
- `SURVIVORSHIP_BIAS_NOT_FULLY_CONTROLLED`: historical membership cannot be reconstructed.

## 4. Benchmark Coverage
- VNINDEX: 2252 sessions fetched from VNDIRECT.
- Index points (not VND); provider mapping verified at fetch time.

## 5. Cost Assumptions
- commission: 0.25% per side
- sell tax: 0.10%
- slippage: 0.10% per side
- round-trip cost: 0.80%
- note: Configurable research cost model. Not live-realistic; execution/slippage is simplified.

## Research periods
- research_start: 2019-01-31
- research_end: 2025-12-31
- train_years: 4 | validation_years: 1
- sealed_oos: 2024-01-01 -> 2025-12-31

## Factor Results (all horizons)

| Factor | Horizon | Obs | Mean IC | Pos IC | Q5-Q1 gross | after-cost | Sealed IC | Verdict |
|---|---|---|---|---|---|---|---|---|
| MOMENTUM_12M | 21 | 9000 | 0.0136 | 0.5333 | 0.0048 | -0.0032 | 0.0192 | WEAK |
| MOMENTUM_12M | 63 | 9000 | -0.0012 | 0.5833 | 0.0081 | 0.0001 | 0.0042 | REJECTED |
| MOMENTUM_12M | 126 | 9000 | -0.0535 | 0.4500 | -0.0133 | -0.0213 | -0.0502 | REJECTED |
| MOMENTUM_12M | 252 | 9000 | -0.1068 | 0.3500 | -0.0537 | -0.0617 | -0.1816 | REJECTED |
| MOMENTUM_12_1 | 21 | 9000 | 0.0050 | 0.5333 | 0.0008 | -0.0072 | -0.0301 | WEAK |
| MOMENTUM_12_1 | 63 | 9000 | -0.0257 | 0.4833 | -0.0049 | -0.0129 | -0.0283 | REJECTED |
| MOMENTUM_12_1 | 126 | 9000 | -0.0739 | 0.4167 | -0.0262 | -0.0342 | -0.0857 | REJECTED |
| MOMENTUM_12_1 | 252 | 9000 | -0.1175 | 0.3333 | -0.0836 | -0.0916 | -0.1976 | REJECTED |
| MOMENTUM_3M | 21 | 9000 | 0.0190 | 0.5667 | 0.0094 | 0.0014 | 0.0279 | WEAK |
| MOMENTUM_3M | 63 | 9000 | 0.0541 | 0.7000 | 0.0263 | 0.0183 | -0.0100 | UNSTABLE |
| MOMENTUM_3M | 126 | 9000 | 0.0433 | 0.6333 | 0.0292 | 0.0212 | 0.0048 | VALIDATED |
| MOMENTUM_3M | 252 | 9000 | -0.0065 | 0.4833 | 0.0370 | 0.0290 | -0.0502 | REJECTED |
| MOMENTUM_6M | 21 | 9000 | 0.0289 | 0.6000 | 0.0088 | 0.0008 | 0.0783 | WEAK |
| MOMENTUM_6M | 63 | 9000 | 0.0437 | 0.5833 | 0.0288 | 0.0208 | 0.0945 | UNSTABLE |
| MOMENTUM_6M | 126 | 9000 | 0.0213 | 0.6000 | 0.0426 | 0.0346 | 0.0315 | VALIDATED |
| MOMENTUM_6M | 252 | 9000 | -0.0704 | 0.3833 | 0.0074 | -0.0006 | -0.0846 | REJECTED |
| QUALITY | 21 | 9000 | 0.0114 | 0.4667 | -0.0006 | -0.0086 | 0.1072 | WEAK |
| QUALITY | 63 | 9000 | 0.0086 | 0.5167 | -0.0098 | -0.0178 | 0.1309 | WEAK |
| QUALITY | 126 | 9000 | 0.0278 | 0.5833 | -0.0191 | -0.0271 | 0.1190 | WEAK |
| QUALITY | 252 | 9000 | 0.0350 | 0.5500 | -0.0193 | -0.0273 | 0.0066 | WEAK |
| REVERSAL_1M | 21 | 9000 | -0.0222 | 0.4333 | -0.0111 | -0.0191 | -0.0562 | REJECTED |
| REVERSAL_1M | 63 | 9000 | -0.0400 | 0.3500 | -0.0353 | -0.0433 | 0.0104 | REJECTED |
| REVERSAL_1M | 126 | 9000 | -0.0465 | 0.3333 | -0.0454 | -0.0534 | 0.0006 | REJECTED |
| REVERSAL_1M | 252 | 9000 | -0.0262 | 0.4500 | -0.0985 | -0.1065 | 0.0111 | REJECTED |
| VALUE_SAFETY | 21 | 9000 | 0.0716 | 0.5965 | 0.0171 | 0.0091 | 0.0673 | UNSTABLE |
| VALUE_SAFETY | 63 | 9000 | 0.1049 | 0.7018 | 0.0418 | 0.0338 | 0.1280 | VALIDATED |
| VALUE_SAFETY | 126 | 9000 | 0.1601 | 0.7719 | 0.1316 | 0.1236 | 0.2343 | VALIDATED |
| VALUE_SAFETY | 252 | 9000 | 0.2516 | 0.8772 | 0.3526 | 0.3446 | 0.3608 | VALIDATED |

### Detail per factor
#### MOMENTUM_12M x 21 sessions
- mean IC: 0.0136 | median: 0.0157 | std: 0.1895 | positive ratio: 0.5333 | n_dates: 60
- Q1..Q5 excess: Q1=0.0097, Q2=0.0099, Q3=0.0202, Q4=0.0158, Q5=0.0145
- gross spread: 0.0048 | after-cost: -0.0032
- walk-forward windows: 1 | walk-forward mean IC: -0.0475
- sealed OOS mean IC: 0.0192 | sealed evaluated: True | sealed used for tuning: False
- **verdict: WEAK**

#### MOMENTUM_12M x 63 sessions
- mean IC: -0.0012 | median: 0.0132 | std: 0.2103 | positive ratio: 0.5833 | n_dates: 60
- Q1..Q5 excess: Q1=0.0377, Q2=0.0485, Q3=0.0495, Q4=0.0514, Q5=0.0458
- gross spread: 0.0081 | after-cost: 0.0001
- walk-forward windows: 1 | walk-forward mean IC: -0.0742
- sealed OOS mean IC: 0.0042 | sealed evaluated: True | sealed used for tuning: False
- **verdict: REJECTED**

#### MOMENTUM_12M x 126 sessions
- mean IC: -0.0535 | median: -0.0310 | std: 0.2568 | positive ratio: 0.4500 | n_dates: 60
- Q1..Q5 excess: Q1=0.1045, Q2=0.1235, Q3=0.1186, Q4=0.1071, Q5=0.0912
- gross spread: -0.0133 | after-cost: -0.0213
- walk-forward windows: 1 | walk-forward mean IC: -0.0898
- sealed OOS mean IC: -0.0502 | sealed evaluated: True | sealed used for tuning: False
- **verdict: REJECTED**

#### MOMENTUM_12M x 252 sessions
- mean IC: -0.1068 | median: -0.1028 | std: 0.2602 | positive ratio: 0.3500 | n_dates: 60
- Q1..Q5 excess: Q1=0.2582, Q2=0.2968, Q3=0.2466, Q4=0.2333, Q5=0.2046
- gross spread: -0.0537 | after-cost: -0.0617
- walk-forward windows: 1 | walk-forward mean IC: -0.1097
- sealed OOS mean IC: -0.1816 | sealed evaluated: True | sealed used for tuning: False
- **verdict: REJECTED**

#### MOMENTUM_12_1 x 21 sessions
- mean IC: 0.0050 | median: 0.0378 | std: 0.1852 | positive ratio: 0.5333 | n_dates: 60
- Q1..Q5 excess: Q1=0.0119, Q2=0.0170, Q3=0.0154, Q4=0.0133, Q5=0.0127
- gross spread: 0.0008 | after-cost: -0.0072
- walk-forward windows: 1 | walk-forward mean IC: -0.0576
- sealed OOS mean IC: -0.0301 | sealed evaluated: True | sealed used for tuning: False
- **verdict: WEAK**

#### MOMENTUM_12_1 x 63 sessions
- mean IC: -0.0257 | median: -0.0015 | std: 0.2102 | positive ratio: 0.4833 | n_dates: 60
- Q1..Q5 excess: Q1=0.0452, Q2=0.0614, Q3=0.0454, Q4=0.0411, Q5=0.0403
- gross spread: -0.0049 | after-cost: -0.0129
- walk-forward windows: 1 | walk-forward mean IC: -0.0914
- sealed OOS mean IC: -0.0283 | sealed evaluated: True | sealed used for tuning: False
- **verdict: REJECTED**

#### MOMENTUM_12_1 x 126 sessions
- mean IC: -0.0739 | median: -0.0764 | std: 0.2603 | positive ratio: 0.4167 | n_dates: 60
- Q1..Q5 excess: Q1=0.1101, Q2=0.1316, Q3=0.1231, Q4=0.0981, Q5=0.0839
- gross spread: -0.0262 | after-cost: -0.0342
- walk-forward windows: 1 | walk-forward mean IC: -0.1199
- sealed OOS mean IC: -0.0857 | sealed evaluated: True | sealed used for tuning: False
- **verdict: REJECTED**

#### MOMENTUM_12_1 x 252 sessions
- mean IC: -0.1175 | median: -0.1100 | std: 0.2447 | positive ratio: 0.3333 | n_dates: 60
- Q1..Q5 excess: Q1=0.2776, Q2=0.3035, Q3=0.2379, Q4=0.2301, Q5=0.1940
- gross spread: -0.0836 | after-cost: -0.0916
- walk-forward windows: 1 | walk-forward mean IC: -0.1122
- sealed OOS mean IC: -0.1976 | sealed evaluated: True | sealed used for tuning: False
- **verdict: REJECTED**

#### MOMENTUM_3M x 21 sessions
- mean IC: 0.0190 | median: 0.0509 | std: 0.1730 | positive ratio: 0.5667 | n_dates: 60
- Q1..Q5 excess: Q1=0.0070, Q2=0.0162, Q3=0.0103, Q4=0.0206, Q5=0.0165
- gross spread: 0.0094 | after-cost: 0.0014
- walk-forward windows: 1 | walk-forward mean IC: 0.0544
- sealed OOS mean IC: 0.0279 | sealed evaluated: True | sealed used for tuning: False
- **verdict: WEAK**

#### MOMENTUM_3M x 63 sessions
- mean IC: 0.0541 | median: 0.0829 | std: 0.1667 | positive ratio: 0.7000 | n_dates: 60
- Q1..Q5 excess: Q1=0.0306, Q2=0.0375, Q3=0.0406, Q4=0.0634, Q5=0.0569
- gross spread: 0.0263 | after-cost: 0.0183
- walk-forward windows: 1 | walk-forward mean IC: 0.1009
- sealed OOS mean IC: -0.0100 | sealed evaluated: True | sealed used for tuning: False
- **verdict: UNSTABLE**

#### MOMENTUM_3M x 126 sessions
- mean IC: 0.0433 | median: 0.0977 | std: 0.2040 | positive ratio: 0.6333 | n_dates: 60
- Q1..Q5 excess: Q1=0.0860, Q2=0.0942, Q3=0.0969, Q4=0.1413, Q5=0.1152
- gross spread: 0.0292 | after-cost: 0.0212
- walk-forward windows: 1 | walk-forward mean IC: 0.1611
- sealed OOS mean IC: 0.0048 | sealed evaluated: True | sealed used for tuning: False
- **verdict: VALIDATED**

#### MOMENTUM_3M x 252 sessions
- mean IC: -0.0065 | median: -0.0148 | std: 0.1996 | positive ratio: 0.4833 | n_dates: 60
- Q1..Q5 excess: Q1=0.2021, Q2=0.2449, Q3=0.2470, Q4=0.2794, Q5=0.2391
- gross spread: 0.0370 | after-cost: 0.0290
- walk-forward windows: 1 | walk-forward mean IC: 0.0688
- sealed OOS mean IC: -0.0502 | sealed evaluated: True | sealed used for tuning: False
- **verdict: REJECTED**

#### MOMENTUM_6M x 21 sessions
- mean IC: 0.0289 | median: 0.0520 | std: 0.2198 | positive ratio: 0.6000 | n_dates: 60
- Q1..Q5 excess: Q1=0.0094, Q2=0.0122, Q3=0.0133, Q4=0.0164, Q5=0.0183
- gross spread: 0.0088 | after-cost: 0.0008
- walk-forward windows: 1 | walk-forward mean IC: -0.0288
- sealed OOS mean IC: 0.0783 | sealed evaluated: True | sealed used for tuning: False
- **verdict: WEAK**

#### MOMENTUM_6M x 63 sessions
- mean IC: 0.0437 | median: 0.0507 | std: 0.2133 | positive ratio: 0.5833 | n_dates: 60
- Q1..Q5 excess: Q1=0.0344, Q2=0.0396, Q3=0.0429, Q4=0.0482, Q5=0.0632
- gross spread: 0.0288 | after-cost: 0.0208
- walk-forward windows: 1 | walk-forward mean IC: -0.0182
- sealed OOS mean IC: 0.0945 | sealed evaluated: True | sealed used for tuning: False
- **verdict: UNSTABLE**

#### MOMENTUM_6M x 126 sessions
- mean IC: 0.0213 | median: 0.0487 | std: 0.2358 | positive ratio: 0.6000 | n_dates: 60
- Q1..Q5 excess: Q1=0.0875, Q2=0.1124, Q3=0.1012, Q4=0.1041, Q5=0.1302
- gross spread: 0.0426 | after-cost: 0.0346
- walk-forward windows: 1 | walk-forward mean IC: 0.0144
- sealed OOS mean IC: 0.0315 | sealed evaluated: True | sealed used for tuning: False
- **verdict: VALIDATED**

#### MOMENTUM_6M x 252 sessions
- mean IC: -0.0704 | median: -0.0860 | std: 0.2243 | positive ratio: 0.3833 | n_dates: 60
- Q1..Q5 excess: Q1=0.2281, Q2=0.2754, Q3=0.2512, Q4=0.2280, Q5=0.2355
- gross spread: 0.0074 | after-cost: -0.0006
- walk-forward windows: 1 | walk-forward mean IC: -0.0817
- sealed OOS mean IC: -0.0846 | sealed evaluated: True | sealed used for tuning: False
- **verdict: REJECTED**

#### QUALITY x 21 sessions
- mean IC: 0.0114 | median: -0.0098 | std: 0.1545 | positive ratio: 0.4667 | n_dates: 60
- Q1..Q5 excess: Q1=0.0148, Q2=0.0170, Q3=0.0121, Q4=0.0127, Q5=0.0142
- gross spread: -0.0006 | after-cost: -0.0086
- walk-forward windows: 1 | walk-forward mean IC: 0.0306
- sealed OOS mean IC: 0.1072 | sealed evaluated: True | sealed used for tuning: False
- **verdict: WEAK**

#### QUALITY x 63 sessions
- mean IC: 0.0086 | median: 0.0169 | std: 0.1502 | positive ratio: 0.5167 | n_dates: 60
- Q1..Q5 excess: Q1=0.0459, Q2=0.0619, Q3=0.0453, Q4=0.0424, Q5=0.0361
- gross spread: -0.0098 | after-cost: -0.0178
- walk-forward windows: 1 | walk-forward mean IC: 0.0563
- sealed OOS mean IC: 0.1309 | sealed evaluated: True | sealed used for tuning: False
- **verdict: WEAK**

#### QUALITY x 126 sessions
- mean IC: 0.0278 | median: 0.0514 | std: 0.1349 | positive ratio: 0.5833 | n_dates: 60
- Q1..Q5 excess: Q1=0.1040, Q2=0.1368, Q3=0.1088, Q4=0.1015, Q5=0.0849
- gross spread: -0.0191 | after-cost: -0.0271
- walk-forward windows: 1 | walk-forward mean IC: 0.1057
- sealed OOS mean IC: 0.1190 | sealed evaluated: True | sealed used for tuning: False
- **verdict: WEAK**

#### QUALITY x 252 sessions
- mean IC: 0.0350 | median: 0.0166 | std: 0.1157 | positive ratio: 0.5500 | n_dates: 60
- Q1..Q5 excess: Q1=0.2184, Q2=0.3125, Q3=0.2348, Q4=0.2464, Q5=0.1991
- gross spread: -0.0193 | after-cost: -0.0273
- walk-forward windows: 1 | walk-forward mean IC: 0.1700
- sealed OOS mean IC: 0.0066 | sealed evaluated: True | sealed used for tuning: False
- **verdict: WEAK**

#### REVERSAL_1M x 21 sessions
- mean IC: -0.0222 | median: -0.0325 | std: 0.1735 | positive ratio: 0.4333 | n_dates: 60
- Q1..Q5 excess: Q1=0.0204, Q2=0.0161, Q3=0.0147, Q4=0.0107, Q5=0.0093
- gross spread: -0.0111 | after-cost: -0.0191
- walk-forward windows: 1 | walk-forward mean IC: -0.0768
- sealed OOS mean IC: -0.0562 | sealed evaluated: True | sealed used for tuning: False
- **verdict: REJECTED**

#### REVERSAL_1M x 63 sessions
- mean IC: -0.0400 | median: -0.0801 | std: 0.1799 | positive ratio: 0.3500 | n_dates: 60
- Q1..Q5 excess: Q1=0.0640, Q2=0.0480, Q3=0.0471, Q4=0.0433, Q5=0.0287
- gross spread: -0.0353 | after-cost: -0.0433
- walk-forward windows: 1 | walk-forward mean IC: -0.0681
- sealed OOS mean IC: 0.0104 | sealed evaluated: True | sealed used for tuning: False
- **verdict: REJECTED**

#### REVERSAL_1M x 126 sessions
- mean IC: -0.0465 | median: -0.0442 | std: 0.1636 | positive ratio: 0.3333 | n_dates: 60
- Q1..Q5 excess: Q1=0.1349, Q2=0.1071, Q3=0.1052, Q4=0.0974, Q5=0.0895
- gross spread: -0.0454 | after-cost: -0.0534
- walk-forward windows: 1 | walk-forward mean IC: -0.1035
- sealed OOS mean IC: 0.0006 | sealed evaluated: True | sealed used for tuning: False
- **verdict: REJECTED**

#### REVERSAL_1M x 252 sessions
- mean IC: -0.0262 | median: -0.0159 | std: 0.1777 | positive ratio: 0.4500 | n_dates: 60
- Q1..Q5 excess: Q1=0.2818, Q2=0.2502, Q3=0.2561, Q4=0.2383, Q5=0.1833
- gross spread: -0.0985 | after-cost: -0.1065
- walk-forward windows: 1 | walk-forward mean IC: -0.0784
- sealed OOS mean IC: 0.0111 | sealed evaluated: True | sealed used for tuning: False
- **verdict: REJECTED**

#### VALUE_SAFETY x 21 sessions
- mean IC: 0.0716 | median: 0.0704 | std: 0.2165 | positive ratio: 0.5965 | n_dates: 57
- Q1..Q5 excess: Q1=0.0109, Q2=0.0091, Q3=0.0160, Q4=0.0154, Q5=0.0279
- gross spread: 0.0171 | after-cost: 0.0091
- walk-forward windows: 1 | walk-forward mean IC: -0.0066
- sealed OOS mean IC: 0.0673 | sealed evaluated: True | sealed used for tuning: False
- **verdict: UNSTABLE**

#### VALUE_SAFETY x 63 sessions
- mean IC: 0.1049 | median: 0.0992 | std: 0.2178 | positive ratio: 0.7018 | n_dates: 57
- Q1..Q5 excess: Q1=0.0374, Q2=0.0380, Q3=0.0612, Q4=0.0609, Q5=0.0792
- gross spread: 0.0418 | after-cost: 0.0338
- walk-forward windows: 1 | walk-forward mean IC: 0.0510
- sealed OOS mean IC: 0.1280 | sealed evaluated: True | sealed used for tuning: False
- **verdict: VALIDATED**

#### VALUE_SAFETY x 126 sessions
- mean IC: 0.1601 | median: 0.1399 | std: 0.2393 | positive ratio: 0.7719 | n_dates: 57
- Q1..Q5 excess: Q1=0.0453, Q2=0.1026, Q3=0.1881, Q4=0.1634, Q5=0.1769
- gross spread: 0.1316 | after-cost: 0.1236
- walk-forward windows: 1 | walk-forward mean IC: 0.1298
- sealed OOS mean IC: 0.2343 | sealed evaluated: True | sealed used for tuning: False
- **verdict: VALIDATED**

#### VALUE_SAFETY x 252 sessions
- mean IC: 0.2516 | median: 0.2116 | std: 0.2323 | positive ratio: 0.8772 | n_dates: 57
- Q1..Q5 excess: Q1=0.0289, Q2=0.2084, Q3=0.4944, Q4=0.3836, Q5=0.3815
- gross spread: 0.3526 | after-cost: 0.3446
- walk-forward windows: 1 | walk-forward mean IC: 0.2285
- sealed OOS mean IC: 0.3608 | sealed evaluated: True | sealed used for tuning: False
- **verdict: VALIDATED**

## 12. Factor Verdicts
- verdict counts: {'UNSTABLE': 3, 'VALIDATED': 5, 'WEAK': 8, 'REJECTED': 12}
- VALIDATED horizons per factor: {'VALUE_SAFETY': 3, 'MOMENTUM_3M': 1, 'MOMENTUM_6M': 1}

## 13. Limitations
- Historical universe membership not reconstructible; survivorship bias not fully controlled.
- Inferred publication dates are governance assumptions, not verified filing dates.
- Cost model is a research simplification, not live-realistic.
- Missing/late data yields missing factor values (never fabricated).

## 14. Production Readiness Decision
- No factor is connected to production allocation in this milestone.
- Expected Alpha and Kelly remain disabled.
- Robustly validated across horizons (>=3 of 4): ['VALUE_SAFETY']. Subject to further PIT/cost/survivorship validation before any production calibration.
- VALIDATED at only a subset of horizons (NOT robust): ['MOMENTUM_3M', 'MOMENTUM_6M']. Treated as WEAK/UNSTABLE for production purposes.
