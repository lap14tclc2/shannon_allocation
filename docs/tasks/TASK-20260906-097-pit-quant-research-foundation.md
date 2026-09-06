---
id: TASK-20260906-097
title: Implement PIT Quant Research Foundation for Buffett-Thorp Allocation
status: verified
priority: high
created: 2026-09-06
updated: 2026-09-06
tags: [research, point-in-time, benchmark, factor, validation, walk-forward, oos]
related: [TASK-20260906-095-buffett-thorp-allocation.md, TASK-20260906-096-refactor-allocation-remove-composite-weights.md, BUY_AND_HOLD_SYSTEM_SPEC.md]
---

## Requirement

Implement the RESEARCH FOUNDATION (T09–T13) for the Buffett Core + Thorp Overlay
allocation architecture. This milestone builds the evidence layer that answers:

> "Do Value, Quality, Momentum, or Reversal factors actually predict future
> excess returns versus VNIndex, using only information available at the time?"

Scope (exactly):

- T09 — Point-in-Time fundamental availability model (PIT).
- T10 — VNIndex benchmark abstraction.
- T11 — Reproducible factor snapshots.
- T12 — Forward benchmark-relative outcomes.
- T13 — Factor validation: rank IC, quantiles, chronological walk-forward,
  sealed OOS, conservative verdict.

Explicitly OUT of scope (remain LOCKED):
Expected Alpha, Kelly sizing, ML models, auto trading, daily rotation, new
allocation heuristics, arbitrary factor weights. Expected Alpha and Kelly stay
locked until T13 demonstrates a robust OOS edge after costs.

## Context

Allocation V1 is implemented (TASK-095) and corrected to use explicit gates
(TASK-096). The research layer validates investment hypotheses only; it does NOT
generate production BUY/SELL actions in this milestone.

Current data model audit (T09 input):

- Finance facts live in `qport_finance.canonical_facts`
  (`symbol, statement_type, line_item_code, value, period_type, fiscal_year,
  fiscal_quarter, period_end, provider, quality_status, observed_at,
  source_document_id`). UNIQUE on the logical fact key -> one reconciled version
  per logical fact today.
- `qport_finance.documents` has `period_end`, `fetched_at`, `source_url`,
  `status`, `content_hash` — no `published_at` / `available_from`.
- `financial_data.models.CanonicalFact` already declares optional
  `published_at`, `valid_from`, `valid_to`, `superseded_by`, but the persisted
  `canonical_facts` table does NOT store them.
- `fetched_at` / `observed_at` are crawl times, NOT market-known dates. They must
  never be treated as publication time.
- Market prices (stocks) persist in per-schema `market_prices`
  (portfolio stores) and `qport_finance.market_prices` (screener). OHLCV is
  available from VNDIRECT/Vnstock via `portfolio.market_data` providers.

Architecture target:

```text
Raw data -> PIT-safe snapshots -> factor snapshots -> forward stock returns
-> forward VNIndex returns -> forward excess returns -> IC / quantiles
-> walk-forward -> sealed OOS -> factor verdict
```

## Acceptance Criteria

- [x] T09: canonical availability model (published_at/known_at/received_at/available_from/availability_source/availability_confidence); `get_facts_as_of(symbol, as_of)` guarantees `available_from <= as_of`; verified publication overrides inferred lag; restatements version-safe; `fetched_at` never grants visibility.
- [x] T10: `research/benchmark.py` with `history("VNINDEX", start, end)`; reuses existing market-data providers; VNINDEX treated as index points (no VND scaling); deterministic return math; trading-date alignment; missing-date policy; persist benchmark prices in research storage.
- [x] T11: `research/` package (`pit.py benchmark.py factors.py snapshots.py outcomes.py validation.py walk_forward.py`); reproducible factor snapshots with `run_id`, `factor_version`, `data_hash`, `created_at`; Value & Quality use PIT facts only; Momentum/Reversal use OHLCV <= snapshot_date; NaN policy; minimum history.
- [x] T12: forward returns for horizons 21/63/126/252 sessions; `forward_stock_return_H`, `forward_vnindex_return_H`, `forward_excess_return_H`; unresolved horizon stays missing; no future outcome feeds factor computation.
- [x] T13: rank IC (Spearman), IC summary (mean/median/std/positive-ratio/count), quantiles Q1–Q5, top-bottom spread, turnover, after-cost spread, chronological walk-forward (no random split), sealed OOS excluded from tuning, conservative verdict rules (VALIDATED/WEAK/UNSTABLE/REJECTED/INSUFFICIENT_DATA).
- [x] Transaction-cost model: configurable research cost model (commission + sell tax + slippage) with clearly marked assumptions (not live-realistic).
- [x] Research universe reuses existing securities/screener infrastructure; no separate master; historical-universe-membership limitation documented.
- [x] CLI: `research-build-snapshots`, `research-build-outcomes`, `research-validate-factor`, `research-run-walk-forward` (no user-facing UI).
- [x] Deterministic research report (no marketing language, limitations stated).
- [x] 30 required tests (PIT, benchmark, factors, outcomes, validation, architecture).
- [x] Expected Alpha and Kelly remain disabled; no `expected_alpha` exposed to production allocation APIs.

## Constraints and Invariants

1. NO LOOK-AHEAD: for analysis time T, no fact with `available_from > T` may be used.
2. NO SURVIVORSHIP-BIAS CLAIM WITHOUT EVIDENCE: historical universe membership limitation must be documented.
3. NO FAKE BENCHMARK: VNINDEX provider mapping must be verified; do not assume provider naming semantics.
4. NO ALPHA CLAIM BEFORE OOS.
5. NO FACTOR WEIGHTS: factors tested independently first.
6. Research code must not mutate the ledger, auto-trade, or modify allocation decision output.
7. Preserve allocation V1 independence; allocation does not depend on research results yet.
8. Reproducible: same inputs -> same `data_hash` -> same snapshot.
9. Missing data -> NaN/MISSING, never zero, never forward-filled.
10. Follow Zettelkasten task-first workflow; commit atomically on
    `feature/buffett-thorp-allocation`; do not merge to main; do not squash.

## Implementation Tasks

- [x] Create + register this task; audit finance schema (canonical facts, documents, observed_at/fetched_at behavior, screener `_build_engine_inputs`).
- [x] T09 `research/pit.py`: availability model + `get_facts_as_of` + restatement version handling + configurable lag defaults (quarterly 45d, annual 90d) documented as governance assumptions.
- [x] T10 `research/benchmark.py`: VNIndex history via existing providers, point-normalization, verification helper, return math, alignment/missing-date policy, persistence in research storage.
- [x] T11 `research/factors.py` + `research/snapshots.py`: value (PIT valuation safety via canonical engine adapter), quality (PIT canonical quality), momentum 63/126/252, reversal 21, liquidity 20D, snapshot persistence with hash.
- [x] T12 `research/outcomes.py`: forward stock/VNIndex/excess returns for 21/63/126/252.
- [x] T13 `research/validation.py` + `research/walk_forward.py`: rank IC, IC summary, quantiles, spread, turnover, costs, walk-forward, sealed OOS, verdict rules; `research/report.py` report builder.
- [x] Research storage: `qport_research` schema tables (factor snapshots, outcomes, validation runs, walk-forward windows, factor results, benchmark prices) + Postgres/SQLite-compatible layer.
- [x] CLI commands; register no production recommendation dependency.
- [x] Tests for the 30 required points; run allocation regression + architecture + relevant backend suite + frontend build (no frontend files changed; build re-run to confirm).
- [x] Record exact verification evidence; set status `verified`.

## Related Notes

- `docs/QPORT_BUFFETT_THORP_SYSTEM_PLAN.md` (§11 research layer, §12 data truth)
- `docs/QPORT_BUFFETT_THORP_IMPLEMENTATION.md` (§6 PIT research foundation T09–T13)
- `docs/tasks/TASK-20260906-095-*`, `docs/tasks/TASK-20260906-096-*`
- `BUY_AND_HOLD_SYSTEM_SPEC.md`, `AGENTS.md`

## Validation Evidence

Research foundation implemented on branch `feature/buffett-thorp-allocation`
(no existing production file modified; only new `python/portfolio/research/`
package + tests + task docs).

Research unit tests:

```
$env:PYTHONPATH="python;." ; python -m pytest python/portfolio/tests/test_research_pit.py python/portfolio/tests/test_research_benchmark.py python/portfolio/tests/test_research_factors.py python/portfolio/tests/test_research_outcomes.py python/portfolio/tests/test_research_snapshots.py python/portfolio/tests/test_research_validation.py python/portfolio/tests/test_research_architecture.py -q
=> 75 passed in 1.45s
```

Allocation regression + architecture (unchanged, still passing):

```
$env:PYTHONPATH="python;." ; python -m pytest python/portfolio/tests/test_allocation_domain.py python/portfolio/tests/test_allocation_eligibility.py python/portfolio/tests/test_allocation_sizing.py python/portfolio/tests/test_allocation_opportunity.py python/portfolio/tests/test_allocation_service.py python/portfolio/tests/test_allocation_api.py python/portfolio/tests/test_allocation_architecture.py python/portfolio/tests/test_architecture.py -q
=> 101 passed in 2.29s
```

Full backend suite:

```
$env:PYTHONPATH="python;." ; python -m pytest python/portfolio/tests -q -p no:cacheprovider
=> 535 passed, 1 skipped, 15 failed in 82.40s
```

The 15 failures are the identical pre-existing set (auth_architecture,
cafef_financials, frontend_design_system_contract x2, mobile_app_shell,
mobile_iphone_shell, normal_user_guide_contract x3, quick_import_ui_contract,
value_engine_audit_68_symbols, value_engine_validation x4). They reproduce on
`abde669` (base before V1), `5380a78` (V1 HEAD), and `7d58eeb` (branch HEAD
before research). The research package is entirely new code and imports nothing
from the failing modules; it does not change these results.

CLI smoke test:

```
python -m portfolio.research.cli run-walk-forward --research-start 2016-01-01 --sealed-oos-start 2024-01-01 --sealed-oos-end 2025-12-31
=> prints deterministic chronological windows (train 2016-01-01.. -> validate 2021-.., ..., train ..2025-12-31 -> validate 2026-01-01..2026-09-06)
```

Frontend production build (no frontend files changed; re-run to confirm):

```
cd frontend ; npm run build
=> vite v6.4.3 · ✓ built in ~1.15s (chunk-size warning only)
```

Required test-point coverage (30/30):

1. future report blocked — `test_quarterly_report_invisible_before_available_from`
2. published report visible — `test_quarterly_report_visible_after_available_from`
3. inferred availability tagged — `test_inferred_lag_correctly_tagged`
4. restatement version-safe — `test_restatement_is_versioned`
5. VNIndex fetch/normalize contract — `test_vnindex_fetch_normalize_contract`, `test_vnindex_points_not_vnd_scaled`
6. date alignment — `test_trading_date_alignment_and_missing_day_policy`
7. deterministic return math — `test_deterministic_return_math`
8. no future OHLCV — `test_no_future_ohlcv_after_snapshot_date`, `test_no_future_ohlcv_used_in_snapshot`
9. exact momentum lookback — `test_exact_momentum_lookback`
10. reversal formula — `test_reversal_formula`
11. insufficient history missing — `test_momentum_insufficient_history_is_missing_not_zero`
12. Value uses PIT valuation only — `test_snapshot_uses_only_pit_facts_for_value_and_quality`
13. Quality uses PIT facts only — same test (quality scorer capture)
14. future return horizon exact — `test_future_return_horizon_exact`
15. unresolved future remains missing — `test_unresolved_future_remains_missing`, `test_outcomes_never_forward_filled`
16. excess return exact — `test_excess_return_exact`
17. IC calculation — `test_rank_ic_is_spearman`
18. quantile assignment — `test_quantile_assignment_and_spread`
19. top-minus-bottom spread — `test_top_minus_bottom_spread_positive_for_positive_factor`
20. chronological walk-forward — `test_chronological_walk_forward_no_random_split`
21. sealed OOS excluded from tuning — `test_sealed_oos_excluded_from_tuning`, `test_tuning_on_sealed_oos_is_guarded`
22. factor verdict rules — `test_factor_verdict_direct_rules`, `test_validate_factor_verdict_rules`
23. cost-adjusted output — `test_cost_adjusted_output`
24. research does not mutate ledger — `test_research_never_mutates_ledger`
25. research does not auto-trade — `test_research_never_auto_trades`
26. allocation V1 independent — `test_allocation_v1_does_not_depend_on_research`
27. no expected_alpha in production allocation — `test_no_expected_alpha_exposed_to_production_allocation_api`
28. no Kelly — `test_no_expected_alpha_or_kelly_in_research_and_allocation`
29. no random train/test split — `test_no_random_train_test_split_for_time_series`
30. no fetched_at-as-publication shortcut — `test_no_fetched_at_as_publication_shortcut`

## Decisions

1. Availability fallback is a governance assumption: quarterly report assumed
   known 45 days after period_end, annual 90 days after period_end. These are
   conservative INFERRED defaults, configurable, and never claimed as exact
   filing dates. Verified `published_at` overrides them when present.
2. `fetched_at` / `observed_at` are never used as publication time.
3. Restatement versioning: the PIT layer accepts multiple fact rows per logical
   fact (keyed by availability + version) and selects the latest available as of
   the analysis date; frozen research snapshots preserve historical state, so a
   later restatement cannot rewrite history silently. Current `canonical_facts`
   stores one reconciled version per logical fact; documented limitation.
4. VNINDEX is an index POINTS series, not VND; benchmark normalization must not
   apply `canonical_vnd_price` scaling. Provider symbol mapping is verified at
   runtime and not assumed.
5. Factors are tested independently. No weighted factor combination in this
   milestone. Momentum lookbacks are exact trading sessions (63/126/252);
   reversal is 21-session return with reversed sign; both documented.
6. Forward horizons are trading sessions 21/63/126/252; unresolved horizons stay
   NULL/MISSING; outcomes never feed factor computation.
7. Sealed OOS is protected by config (`sealed_oos_start/end`) and separated from
   any tuning path; the code makes tuning on sealed OOS difficult by construction.
8. Verdict rules are conservative, explicit, and documented; a factor is never
   called VALIDATED merely because mean IC > 0.

## Result

Research foundation (T09–T13) implemented and verified:

- `python/portfolio/research/`: `pit.py`, `benchmark.py`, `factors.py`,
  `snapshots.py`, `outcomes.py`, `validation.py`, `walk_forward.py`,
  `store.py`, `report.py`, `cli.py`, `valuation_adapter.py`.
- PIT availability model with `get_facts_as_of` guaranteeing
  `available_from <= as_of`, inferred governance lags (45d/90d) documented as
  assumptions, verified `published_at` override, version-safe restatements, and
  a hard rule that `fetched_at`/`observed_at` are never publication time.
- VNIndex benchmark abstraction (index points, not VND; runtime verify; exact
  session return math; last-available-before alignment).
- Reproducible factor snapshots (source_hash, factor_version) with PIT-only
  Value/Quality via canonical engines and session-exact Momentum/Reversal.
- Forward benchmark-relative outcomes for 21/63/126/252 sessions; unresolved
  horizons stay NULL; outcomes never feed factor computation.
- Factor validation: rank IC, IC summary, quantiles Q1–Q5, top-bottom spread,
  turnover, after-cost spread, chronological walk-forward, sealed OOS guarded
  by `assert_not_sealed`, conservative verdict rules.
- `qport_research` schema (Postgres production / SQLite tests) with run
  provenance and idempotent writes.
- Research CLI (no production recommendation dependency; not exposed as a user
  BUY/SELL endpoint).

Known limitations (documented, not papered over):
- Historical universe membership is not reconstructible from current data —
  survivorship-bias-free results are NOT claimed.
- Inferred publication dates are governance assumptions, not verified filing dates.
- Cost model is a configurable research simplification, not live-realistic.
- The canonical value/quality adapters require a populated finance DB to run in
  production; unit tests use injected deterministic evaluators.

No STOP conditions triggered. Status is `verified` for the research-foundation
scope. T14 (expected-alpha calibration) and T15 (fractional Kelly) remain LOCKED
until T13 demonstrates a robust OOS edge after costs.

## STOP conditions

Mark BLOCKED (do not paper over) if:
- PIT correctness cannot be guaranteed;
- VNIndex provider semantics cannot be verified;
- historical fundamentals lack metadata and no conservative fallback is definable;
- factor snapshots cannot be reproduced;
- sealed OOS cannot be protected from tuning.

None triggered in this milestone.