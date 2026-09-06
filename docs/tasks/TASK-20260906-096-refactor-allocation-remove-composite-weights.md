---
id: TASK-20260906-096
title: Refactor Allocation V1 to Remove Unvalidated Composite Opportunity Weights
status: verified
priority: high
created: 2026-09-06
updated: 2026-09-06
tags: [allocation, buffett, thorp, refactor, architecture, risk, screener]
related: [TASK-20260906-095-buffett-thorp-allocation.md, BUY_AND_HOLD_SYSTEM_SPEC.md, AGENTS.md]
---

## Requirement

Perform a focused architecture correction on the Allocation V1 module
(`python/portfolio/allocation/`) before merge.

Primary goal:

**Remove the unvalidated composite opportunity score from V1 allocation
decisions** and replace it with a deterministic sequence of explicit rule gates.

The current implementation uses heuristic weights and score thresholds:

```text
QUALITY_WEIGHT = 0.45
VALUATION_WEIGHT = 0.30
FIT_WEIGHT = 0.20
TECHNICAL_WEIGHT = 0.05

full_opportunity_score(...)
WEAK_HOLDING_SCORE = 0.50
ROTATION_ADVANTAGE_THRESHOLD = 0.15
```

These have NOT been validated by point-in-time historical data, VNIndex-relative
forward returns, IC analysis, walk-forward, or sealed OOS validation. V1 must
therefore NOT use an arbitrary composite score to decide whether a holding is
weak or whether rotation should occur.

This is a refactor of existing decision logic only — it is NOT a feature
addition and does not change the V1 scope.

## Context

Allocation V1 was implemented and verified in `TASK-20260906-095`. The module
reuses the canonical Value Engine, canonical `portfolio_risk()`, and the
existing Screener. This correction removes the one piece of V1 logic that was
not architecturally sound: a weighted scalar "opportunity score" used to gate
HOLD vs REDUCE and rotation.

Architecture invariant:

```text
Buffett Core decides WHAT TO OWN.
Thorp Overlay decides HOW MUCH TO OWN.
Opportunity-cost logic decides WHETHER capital should move.
HOLD is the default action.
Cash is valid.
No fake alpha model.
```

Dimensions that must remain separate (never collapsed into one weighted score):

1. Eligibility
2. Business Quality (ordinal tier: EXCEPTIONAL > HIGH_QUALITY > INVESTABLE > WATCH > LOW_QUALITY)
3. Valuation Safety (`actual_mos_pct - required_mos_pct`, in percentage points)
4. Portfolio Fit / Risk (categorical: GOOD / MODERATE / WEAK / UNAVAILABLE)
5. Replacement Advantage (explicit gates + conservative valuation-safety delta)
6. Technical confirmation (secondary evidence only; never required; never a weighted input)

Also includes documentation audit corrections from the prior V1 verification:

- reconcile the reported allocation/architecture test counts;
- clarify the true base commit used for the pre-existing-failure reproduction;
- do not claim a test count that does not match recorded command output.

## Acceptance Criteria

- [ ] Remove `QUALITY_WEIGHT`, `VALUATION_WEIGHT`, `FIT_WEIGHT`, `TECHNICAL_WEIGHT` from allocation decision code.
- [ ] Remove `full_opportunity_score` and any composite-score path for BUY/HOLD/REDUCE/SELL.
- [ ] Remove `WEAK_HOLDING_SCORE` and `ROTATION_ADVANTAGE_THRESHOLD` (score-delta rotation).
- [ ] Replace decision logic with an explicit gate hierarchy:
      A hard reject -> SELL; B fundamental deterioration (LOW_QUALITY) -> REDUCE;
      C excessive risk contribution (canonical thresholds) -> REDUCE;
      D normal good holding -> HOLD; E new candidate gates; F rotation gates.
- [ ] Rotation only when explicit gates all pass (holding genuinely weaker by
      explicit rules, candidate INVESTABLE, candidate quality not worse,
      candidate valuation safety materially better, candidate fit not WEAK,
      hysteresis buffer passed).
- [ ] Use a configurable, documented conservative threshold
      `VALUATION_SAFETY_REPLACEMENT_DELTA` (default 10 pp) — never described as alpha.
- [ ] Quality comparisons use ordinal tiers, not weighted scalars.
- [ ] Portfolio fit remains categorical; never a weighted input.
- [ ] Technical confirmation may only downgrade BUY_MORE -> WATCH / add a reason
      code; it must not be a weighted input and must never override eligibility.
- [ ] Add/update reason codes so each action is explainable
      (`VALUATION_SAFETY_INSUFFICIENT`, `VALUATION_SAFETY_IMPROVES`,
      `PORTFOLIO_FIT_IMPROVES`, `PORTFOLIO_FIT_WEAK`).
- [ ] Add/update tests proving the 15 requirements in the task brief
      (no weights, no composite score, HOLD default, no rank-only reduction,
      hard-reject precedence, excessive-risk REDUCE, weak-fit not BUY_MORE,
      good-fit BUY_MORE, gate-only rotation, hysteresis, missing-risk
      UNAVAILABLE, technical cannot override eligibility, existing API tests,
      frontend build, valuation/risk/screener unchanged).
- [ ] Reconcile prior documentation test-count claims and clarify the base commit.
- [ ] Fix the duplicate `TASK-20260906-095` row in `docs/tasks/README.md`.

## Constraints and Invariants

1. Follow root `AGENTS.md` Zettelkasten task-first workflow; do not reuse
   `TASK-20260906-095` for scope expansion.
2. Preserve the canonical Value Engine and canonical `portfolio_risk()`.
3. Preserve Screener as candidate discovery only.
4. Preserve multi-portfolio isolation, DB-first behavior, advisory-only output,
   simulate endpoint no-persistence, and `/valuation` `/risk` `/screener`
   separation.
5. No Kelly, no expected alpha, no ML, no new provider calls, no auto execution,
   no ledger-behavior changes.
6. Do not redesign the UI beyond reflecting changed decision reasons.
7. Missing data must degrade safely and explicitly; never fabricate fallback
   values (e.g., missing risk history stays `UNAVAILABLE`, never zero risk).
8. Do not claim empirically optimal thresholds; document governance defaults.

## Implementation Tasks

- [ ] Create this task and register it in `docs/tasks/README.md`; fix the duplicate TASK-095 row.
- [ ] Refactor `opportunity.py`: remove weights/composite score; add ordinal tier helpers, gate functions, rotation gates, configurable governance thresholds.
- [ ] Refactor `service.py`: remove composite-score usage; drive rotation through explicit `rotation_gates`.
- [ ] Update `models.py` / `candidate_service.py`: rename discovery ranking to `discovery_score` (research ordering only); keep `bands` as separate transparent dimensions.
- [ ] Update `reason_codes.py` (+ frontend `allocationLabels.js`) with new explainable codes.
- [ ] Update allocation unit/service tests to the gate model.
- [ ] Add architecture tests proving no weights/composite remain and all 15 requirements are covered.
- [ ] Run allocation tests, architecture tests, backend regression, `npm run build`.
- [ ] Reconcile prior test-count documentation; record exact verification evidence.
- [ ] Commit atomically and push branch (no merge to main, no squash).

## Related Notes

- `docs/QPORT_BUFFETT_THORP_SYSTEM_PLAN.md`
- `docs/QPORT_BUFFETT_THORP_IMPLEMENTATION.md`
- `docs/tasks/TASK-20260906-095-buffett-thorp-allocation.md`
- `BUY_AND_HOLD_SYSTEM_SPEC.md`
- `AGENTS.md`

## Validation Evidence

Refactor implemented on branch `feature/buffett-thorp-allocation`.

Allocation + architecture tests (7 allocation files + `test_architecture.py`):

```
$env:PYTHONPATH="python;." ; python -m pytest python/portfolio/tests/test_allocation_domain.py python/portfolio/tests/test_allocation_eligibility.py python/portfolio/tests/test_allocation_sizing.py python/portfolio/tests/test_allocation_opportunity.py python/portfolio/tests/test_allocation_service.py python/portfolio/tests/test_allocation_api.py python/portfolio/tests/test_allocation_architecture.py python/portfolio/tests/test_architecture.py -q
=> 101 passed in 1.99s
```

Allocation tests only (the 7 `test_allocation_*.py` files):

```
=> 91 passed in 1.82s
```

Core sqlite backend regression (no network):

```
cd python ; python -m pytest portfolio/tests/test_service.py portfolio/tests/test_accounting.py portfolio/tests/test_analytics.py portfolio/tests/test_validation.py portfolio/tests/test_price_units.py portfolio/tests/test_locale.py portfolio/tests/test_vi_labels.py -q
=> 51 passed in 13.54s
```

Full backend suite:

```
$env:PYTHONPATH="python;." ; python -m pytest python/portfolio/tests -q -p no:cacheprovider
=> 460 passed, 1 skipped, 15 failed in 81.13s
```

The 15 failures are the SAME set reproduced on a clean worktree of BOTH:
- `abde669` (base commit before the V1 implementation; HEAD when the prior task's
  reproduction ran), and
- `5380a78` (pushed V1 HEAD before this refactor; re-verified in this task,
  15 failed, 11 passed for the failing subset).

None are caused by the Allocation V1 work or by this refactor.

Frontend production build:

```
cd frontend ; npm run build
=> vite v6.4.3 · ✓ built in ~1.2s (chunk-size warning only)
```

All 15 required testing points are covered:

1. No `QUALITY_WEIGHT`/`VALUATION_WEIGHT`/`FIT_WEIGHT`/`TECHNICAL_WEIGHT` in
   allocation decision code -> `test_no_composite_opportunity_weights_in_decision_code`.
2. No `full_opportunity_score` used for BUY/HOLD/REDUCE/SELL ->
   `test_no_composite_opportunity_weights_in_decision_code`,
   `test_no_composite_score_in_decision_models_or_bands`.
3. High-quality holding -> HOLD when no explicit rule triggers ->
   `test_high_quality_holding_is_hold_when_no_explicit_rule_triggers`.
4. Lower-ranked holding not reduced solely due to rank ->
   `test_lower_rank_holding_not_reduced_solely_due_to_rank`,
   `test_rotation_never_rotates_a_good_holding`.
5. Hard reject still forces SELL/REDUCE -> `test_hard_reject_holding_is_sell`,
   `test_scenario4_hard_reject_never_investable`, `test_technical_cannot_override_eligibility`.
6. Excessive risk contribution still forces REDUCE ->
   `test_excessive_risk_contribution_is_reduce`, `test_scenario2`.
7. Candidate with much better valuation but WEAK fit is not BUY_MORE ->
   `test_candidate_weak_fit_is_watch_and_capped`, `test_rotation_requires_all_gates`.
8. Candidate with better quality/valuation + GOOD fit may be BUY_MORE ->
   `test_excellent_attractive_good_fit_buys_more`, `test_scenario1`.
9. Rotation only when explicit gates all pass ->
   `test_rotation_gates_pass_for_weak_holding_and_superior_candidate`,
   `test_rotation_requires_all_gates`.
10. Small valuation difference does not rotate (hysteresis) ->
    `test_rotation_requires_material_valuation_improvement`,
    `test_hysteresis_small_valuation_difference_never_rotates`.
11. Missing risk remains UNAVAILABLE, never zero risk -> `test_scenario9`,
    `test_candidate_unavailable_risk_is_watch_not_buy`.
12. Technical signal cannot override eligibility ->
    `test_technical_cannot_override_eligibility`.
13. Existing allocation API tests still pass -> all of `test_allocation_api.py`.
14. Frontend build passes (recorded above).
15. Existing valuation/risk/screener behavior unchanged ->
    `test_risk_endpoint_unchanged_and_still_canonical` + existing `test_architecture.py`.

Architecture audit additions assert: the composite weights / `full_opportunity_score`
/ `WEAK_HOLDING_SCORE` / `ROTATION_ADVANTAGE_THRESHOLD` identifiers do not exist
anywhere in the allocation package; decision evidence exposes only separate
dimensions (`business_quality_tier`, `valuation_safety_pp`, `portfolio_fit`,
`technical_confirmation`); rotation uses a documented governance threshold
`VALUATION_SAFETY_REPLACEMENT_DELTA = 10.0` that is explicitly not alpha; and the
new explainable reason codes exist.

## Decisions

1. The composite weighted opportunity score is removed from ALL allocation
   decision paths in V1. Candidate shortlist ordering keeps a transparent
   discovery rank (`discovery_score`) used ONLY to order research candidates;
   it never determines BUY/HOLD/REDUCE/SELL.
2. `VALUATION_SAFETY_REPLACEMENT_DELTA` (default 10 percentage points) is a
   conservative governance hysteresis buffer, documented as a policy choice and
   never described as alpha or as empirically optimal.
3. `MIN_VALUATION_SAFETY` (default 0.0 pp) gates new BUY_MORE candidates.
4. Quality is compared ordinally (tier order), fit is categorical
   (GOOD/MODERATE/WEAK/UNAVAILABLE); neither is converted to a weighted scalar
   for final action logic.
5. Technical confirmation is a secondary evidence flag only: it may downgrade
   BUY_MORE to WATCH or add a reason code; it can never override eligibility.
6. Rotation requires ALL gates to pass; a lower rank alone never reduces a holding.
7. The "excessive" risk-contribution threshold keeps the existing QPort health
   convention `largest RC > max(45%, 1.5 × equal-risk)`.

## Result

Refactor complete and verified.

- `python/portfolio/allocation/opportunity.py`: composite weights and
  `full_opportunity_score` removed; replaced with explicit gates
  (`decide_holding` A–D, `decide_candidate` E, `rotation_gates` F), ordinal
  quality comparison, categorical fit, and a documented governance threshold
  `VALUATION_SAFETY_REPLACEMENT_DELTA`. Technical is a secondary flag only.
- `python/portfolio/allocation/service.py`: rotation coordination now driven by
  `rotation_gates` (no composite score); `opportunity_score` removed from
  candidate assembly.
- `python/portfolio/allocation/models.py`: `opportunity_score` renamed to
  `discovery_score` (research ordering only); `bands` typed to hold separate
  transparent dimensions.
- `python/portfolio/allocation/candidate_service.py`: discovery rank documented
  as research-ordering only.
- `python/portfolio/allocation/reason_codes.py` + frontend `allocationLabels.js`:
  added `VALUATION_SAFETY_INSUFFICIENT`, `VALUATION_SAFETY_IMPROVES`,
  `PORTFOLIO_FIT_IMPROVES`, `PORTFOLIO_FIT_WEAK`.
- Tests updated/added (91 allocation tests); architecture audit extended.
- Documentation corrected: `docs/tasks/README.md` duplicate TASK-095 row removed;
  prior test-count claims reconciled (see correction audit below).

Success criterion met: V1 allocation decisions are now a deterministic sequence
of gates, not the output of an unvalidated weighted factor score. When evidence
does not clearly justify moving capital, the output is HOLD / KEEP_CASH.

Status is `verified` for this correction scope.

## Correction audit (prior V1 verification)

Reconciliation of `TASK-20260906-095` evidence:

- The prior task's Validation Evidence reported "75 allocation tests" (7 files)
  and "84 passed" for allocation + `test_architecture.py`, and "443 passed"
  for the full backend suite. Re-measured in this task (with the refactor in
  place): **91** allocation tests, **101** allocation + architecture, and
  **460 passed** full suite. The prior figures were captured at earlier points
  in the V1 session and do not match the final measured command output; this
  task records the authoritative re-measured numbers.
- The base commit used for the prior pre-existing-failure reproduction was
  `abde669` (HEAD at the time). This task re-confirms the identical 15 failures
  also reproduce on `5380a78` (pushed V1 HEAD before this refactor). The 15
  failures therefore pre-date both the V1 work and this correction.
- `docs/tasks/README.md` contained a duplicate `TASK-20260906-095` row
  (one `verified`, one `ready`); the duplicate `ready` row was removed in this
  task.