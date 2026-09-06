---
id: TASK-20260906-098
title: Harden Sealed OOS Semantics and Run End-to-End Factor Research
status: verified
priority: high
created: 2026-09-06
updated: 2026-09-06
tags: [research, sealed-oos, walk-forward, factor, validation, data-readiness]
related: [TASK-20260906-097-pit-quant-research-foundation.md, BUY_AND_HOLD_SYSTEM_SPEC.md]
---

## Requirement

Two parts only:

**Part A — Harden sealed-OOS semantics.**

`walk_forward_windows(config)` may generate validation windows that overlap,
enter, or occur after the configured sealed OOS period. This violates the
intended meaning: `sealed OOS = final untouched test period`.

Required invariant: if `sealed_oos_start = S` and `sealed_oos_end = E`, then ALL
training/validation/tuning windows MUST satisfy `window.valid_end < S`. No
tuning/validation window may overlap [S, E], start inside [S, E], or continue
after E in the same run.

**Part B — Run end-to-end factor research on real QPort data and report the
truth.**

Produce a DATA READINESS report first, then run the research pipeline
(factor snapshots -> forward outcomes -> IC/quantiles -> walk-forward ->
sealed OOS) on REAL data only. No fabricated data for research evidence.

## Context

Research foundation T09–T13 is implemented (TASK-20260906-097). `walk_forward.py`
currently builds windows up to `research_end` (or today) without treating
`sealed_oos_start` as an upper boundary — this is the bug to fix.

Real-data audit (from the live `qport_finance` Postgres):

- `securities`: 1523 rows.
- `canonical_facts`: 521,005 rows, fiscal years 2016–2026 (period_end
  2016-12-31 → 2026-06-30). Sufficient for PIT Value/Quality from ~2017+.
- `documents`: 110,972 rows; `fetched_at` present, NO verified `published_at`
  -> PIT availability must use inferred governance lags (45d/90d).
- `market_prices` (finance schema): 47,185 rows, 1,499 symbols, span only
  2026-07-16 → 2026-09-04 (~2 months). 0 symbols have >= 260 bars.
  Historical OHLCV is NOT stored -> must be fetched from VNDIRECT for
  momentum/reversal/outcomes.
- VNDIRECT is reachable and returns full historical OHLCV + VNINDEX
  (verified empirically: VNINDEX 2023 H1 = 121 sessions, index points ~1044).

A shares-unit bug was found and fixed in
`research/valuation_adapter.build_financial_history` (shares outstanding were
being multiplied by `_BILLION`; now `shares_scale` keeps the share count as-is).
`canonical_pit_valuator` now returns sensible MOS/required-MOS on real PIT facts
(~0.01s per call).

## Acceptance Criteria

- [x] Part A: `walk_forward_windows` stops at `sealed_oos_start` (windows have `valid_end < S`).
- [x] Part A: config validation raises on invalid sealed ranges
      (S < E, research_start < S, sealed_oos_end <= research_end when given).
- [x] Part A: `research_cutoff(config)` = day before sealed_oos_start.
- [x] Part A: `partition_periods` returns `tuning_allowed` and `sealed_oos`
      (clear names, semantics documented; compatibility names retained).
- [x] Part A: `assert_not_sealed` remains a second defensive guard.
- [x] Part A: CLI prints walk-forward windows and SEALED OOS separately; no
      validation window after the sealed range.
- [x] Part A: research report identifies in-sample / walk-forward / sealed OOS
      periods and whether sealed was evaluated / ever used for tuning.
- [x] Part A: 10 sealed-OOS tests (no overlap, none after sealed, one-day-before
      valid, invalid ranges raise, short-training safety, research_end before
      sealed raises, assert_not_sealed blocks, partition never leaks sealed to
      tuning, CLI separation, determinism).
- [x] Part B: `audit-data` CLI produces a real DATA READINESS report.
- [x] Part B: run the research pipeline on a conservative real universe
      (150 liquid HOSE/HNX/UPCOM common equities), fetch real historical
      OHLCV + VNINDEX from VNDIRECT, persist to research store.
- [x] Part B: factor snapshots on a real monthly grid; forward outcomes for
      21/63/126/252; validation per factor x horizon; conservative verdicts.
- [x] Part B: deterministic Markdown report under `docs/research/`.
- [x] Expected Alpha and Kelly remain disabled; no production allocation change.
- [x] Record exact verification evidence; status `verified`.

## Constraints and Invariants

1. No look-ahead: `available_from <= as_of` always; `fetched_at` never publication time.
2. Sealed OOS is the FINAL untouched period; no tuning after it.
3. No fabricated data in research evidence (synthetic data only in tests).
4. No expected alpha, no Kelly, no ML, no auto trading, no production allocation change.
5. Each factor tested independently; no composite/weights.
6. Universe reuses existing securities infrastructure; no new master.
7. Report all horizons; do not cherry-pick; truth over attractive backtest.
8. Document survivorship limitation (`SURVIVORSHIP_BIAS_NOT_FULLY_CONTROLLED`).
9. STOP/BLOCKED/PARTIAL if data is too sparse; never paper over.

## Implementation Tasks

- [x] Part A: rewrite `walk_forward_windows` with sealed boundary + `research_cutoff`.
- [x] Part A: add `validate_config`; wire into `ResearchConfig.__post_init__`.
- [x] Part A: update `partition_periods` (tuning_allowed / sealed_oos).
- [x] Part A: CLI separation of walk-forward vs sealed OOS; report period identification.
- [x] Part A: sealed-OOS tests (10 points) + hardened verdict rules (median IC, min after-cost spread 50bps, walk-forward persistence).
- [x] Part B: fix + verify `valuation_adapter` shares unit (regression covered by real-run sanity).
- [x] Part B: `audit-data` command + DATA READINESS report from real DB.
- [x] Part B: universe builder (securities + liquidity) + price/VNINDEX fetch & persist.
- [x] Part B: full research run (snapshots, outcomes, validation).
- [x] Part B: `docs/research/THORP_FACTOR_RESEARCH_20260906.md` report.
- [x] Run research tests + sealed-OOS tests + allocation regression + architecture + relevant backend suite.
- [x] Record evidence; set `verified`; commit atomically; push branch.

## Related Notes

- `docs/tasks/TASK-20260906-097-*` (research foundation)
- `docs/QPORT_BUFFETT_THORP_SYSTEM_PLAN.md` (§11, §12)
- `docs/QPORT_BUFFETT_THORP_IMPLEMENTATION.md` (§6, §7, §8)
- `BUY_AND_HOLD_SYSTEM_SPEC.md`, `AGENTS.md`

## Validation Evidence

Part A + Part B on branch `feature/buffett-thorp-allocation`.

Part A tests (sealed-OOS hardening):

```
$env:PYTHONPATH="python;." ; python -m pytest python/portfolio/tests/test_research_sealed_oos.py -q
=> 14 passed in 0.66s
```

Research + allocation + architecture (combined):

```
$env:PYTHONPATH="python;." ; python -m pytest python/portfolio/tests/test_research_pit.py python/portfolio/tests/test_research_benchmark.py python/portfolio/tests/test_research_factors.py python/portfolio/tests/test_research_outcomes.py python/portfolio/tests/test_research_snapshots.py python/portfolio/tests/test_research_validation.py python/portfolio/tests/test_research_architecture.py python/portfolio/tests/test_research_sealed_oos.py python/portfolio/tests/test_allocation_*.py python/portfolio/tests/test_architecture.py -q
=> 191 passed in 4.53s
```

Full backend suite:

```
$env:PYTHONPATH="python;." ; python -m pytest python/portfolio/tests -q -p no:cacheprovider
=> 550 passed, 1 skipped, 15 failed in 85.42s
```

The 15 failures are the identical pre-existing set (auth_architecture,
cafef_financials, frontend_design_system_contract x2, mobile_app_shell,
mobile_iphone_shell, normal_user_guide_contract x3, quick_import_ui_contract,
value_engine_audit_68_symbols, value_engine_validation x4), reproduced on
`abde669`, `5380a78`, `7d58eeb`. No new failures introduced.

Frontend build: not run (no frontend files changed).

Part B real-data run (real `qport_finance` Postgres + live VNDIRECT):

```
python -m portfolio.research.cli audit-data
=> securities 1523 (HOSE 405 / HNX 299 / UPCOM 819); facts 521,005 (FY 2016-2026);
   verified publication facts 0 -> 100% inferred; stored OHLCV 1499 symbols but
   only 2026-07-16..2026-09-04 (~2 months, 0 symbols >= 260 bars);
   VNINDEX fetchable (2023 H1 = 121 sessions, points ~1044); survivorship NOT controlled.

python -m portfolio.research.cli run-full-research --top-n 150 --min-recent-bars 20 --report-path docs/research/THORP_FACTOR_RESEARCH_20260906.md
=> run_id res-e72a87ac6b; universe 150 (HOSE 125 / HNX 14 / UPCOM 11);
   fetched 150/150 symbols + VNINDEX 2252 sessions; 72 monthly snapshot dates;
   10,800 snapshots; 10,800 outcome rows; 28 factor x horizon validations.
```

Report: `docs/research/THORP_FACTOR_RESEARCH_20260906.md`.

Final factor results (mean IC / after-cost spread / sealed OOS IC / verdict), all horizons reported:

| Factor | 21 | 63 | 126 | 252 |
|---|---|---|---|---|
| VALUE_SAFETY | UNSTABLE (0.0716 / +0.0091 / +0.0673) | VALIDATED (0.1049 / +0.0338 / +0.1280) | VALIDATED (0.1601 / +0.1236 / +0.2343) | VALIDATED (0.2516 / +0.3446 / +0.3608) |
| MOMENTUM_3M | WEAK | UNSTABLE | VALIDATED | REJECTED |
| MOMENTUM_6M | WEAK | UNSTABLE | VALIDATED | REJECTED |
| MOMENTUM_12M | WEAK | REJECTED | REJECTED | REJECTED |
| MOMENTUM_12_1 | WEAK | REJECTED | REJECTED | REJECTED |
| QUALITY | WEAK | WEAK | WEAK | WEAK |
| REVERSAL_1M | REJECTED | REJECTED | REJECTED | REJECTED |

Verdict counts: VALIDATED 5, WEAK 8, UNSTABLE 3, REJECTED 12.

Production readiness: VALUE_SAFETY is the only factor VALIDATED across >= 3
horizons (63/126/252) — a research candidate, NOT connected to production and
subject to PIT/cost/survivorship hardening. Momentum_3M/6M are VALIDATED at the
126-session horizon only -> treated as WEAK/UNSTABLE (not robust). QUALITY and
REVERSAL show no robust edge. No factor is connected to production allocation.

## Decisions

1. Sealed OOS is the final untouched period; `walk_forward_windows` uses
   `research_cutoff(config)` = day before `sealed_oos_start` as its effective
   upper boundary, so `window.valid_end < S` always.
2. `validate_config` enforces: S < E, research_start < S, and when
   `research_end` is given, E <= research_end.
3. `partition_periods` returns `tuning_allowed` / `sealed_oos` (new explicit
   names) and retains `in_sample` / `sealed` as compatibility aliases with
   documented semantics.
4. `assert_not_sealed` remains a second defensive guard.
5. Real research uses fetched VNDIRECT historical OHLCV + VNINDEX (the finance
   DB stores only ~2 months of prices); persisted into the research store so
   the run is reproducible.
6. Conservative universe: HOSE/HNX/UPCOM common equities with sufficient
   OHLCV + PIT facts + liquidity (existing 20D turnover concept). Historical
   membership cannot be reconstructed -> SURVIVORSHIP_BIAS_NOT_FULLY_CONTROLLED.
7. PIT publication dates are inferred (45d quarter / 90d annual) — verified
   publication metadata is absent in the DB.
8. All horizons (21/63/126/252) reported; no cherry-picking; verdicts are
   conservative governance rules.
9. Expected Alpha and Kelly stay disabled.

## Result

Part A: sealed-OOS semantics hardened. `walk_forward_windows` now stops at
`research_cutoff(config)` (the day before `sealed_oos_start`), so every window
satisfies `valid_end < S`. `validate_config` rejects structurally invalid
ranges; `partition_periods` returns explicit `tuning_allowed` / `sealed_oos`;
`assert_not_sealed` remains a defensive guard; CLI separates walk-forward
windows and the sealed period; the report identifies in-sample / walk-forward /
sealed periods and whether sealed was evaluated or ever used for tuning.
14 sealed-OOS tests added. Verdict rules hardened (median IC > 0, after-cost
spread >= 50bps, walk-forward persistence) so sub-bps noise cannot be VALIDATED.

Part B: real end-to-end research executed on real QPort data (150 liquid VN
common equities, real VNDIRECT historical OHLCV + VNINDEX, PIT-safe canonical
value/quality from real facts, monthly 2019-01..2024-12, horizons 21/63/126/252,
sealed OOS 2024). Honest conclusion: VALUE_SAFETY is the strongest candidate
(VALIDATED 63/126/252, monotonic IC, positive after-cost spread, positive sealed
OOS) but is NOT production-ready (survivorship bias not fully controlled,
inferred publication dates, simplified cost model); momentum is not robustly
validated (only the 126-session horizon passes); quality is WEAK; reversal is
REJECTED. No factor is connected to production. Expected Alpha and Kelly remain
disabled.

Known limitations (documented in the report): SURVIVORSHIP_BIAS_NOT_FULLY_CONTROLLED;
inferred publication dates; simplified cost model; missing data -> missing
factor values (never fabricated); historical OHLCV had to be fetched from
VNDIRECT because the finance DB stores only ~2 months of prices.

No STOP conditions triggered. Status is `verified`.

## STOP conditions

Mark BLOCKED/PARTIAL (do not paper over) if: actual VNIndex data cannot be
verified; historical finance data is too sparse; PIT valuation cannot be
reconstructed; sealed OOS cannot be kept untouched; factor sample too small;
the database/environment required for real research is unavailable.