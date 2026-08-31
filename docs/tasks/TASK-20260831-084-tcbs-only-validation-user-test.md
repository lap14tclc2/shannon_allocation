# TASK-20260831-084: Rewrite user-test for TCBS-only validation gates

**status:** in-progress  
**date:** 2026-08-31  
**priority:** high

## Requirement

Rewrite `docs/user-test.md` so it reflects the current QPort validation architecture and the user's current constraint:

- valuation/validation must work from the financial data already ingested from TCBS/canonical DB;
- do not require web/IR/manual source scanning to resolve every anomaly;
- large numeric movements are detections, not proof of bad data;
- use cross-metric coherence, persistence, regime detection, cycle detection and materiality to decide how data is handled;
- distinguish validation bugs from expected model/data coverage gaps.

## Context

Observed current validation snapshot supplied by the user:

| Reason | Count | Meaning |
| --- | ---: | --- |
| MODEL_VERIFIED | 99 | 72 have public IV/MOS; remaining cases are quality/hard-reject gated |
| ARCHETYPE_UNKNOWN | 173 | securities industry is UNKNOWN; model cannot be routed |
| MODEL_INCOMPLETE | 36 | insufficient 7–10Y full-cycle history |
| MODEL_UNVALUABLE | 12 | owner earnings are negative |
| RNAV / KCN lease | 8 + 5 | specialized project/land/lease inputs are missing |
| MODEL_ESTIMATED | 1 (ACV) | concession end date is unavailable |

No crash is implied by these gates. ACV being `MODEL_ESTIMATED` is a coverage limitation, not a validation failure.

DGC is the canonical regression example: extreme 2017–2018 and 2021–2022 changes must be classified numerically rather than automatically presented as bad source data.

## Acceptance Criteria

- [ ] Remove obsolete guidance that makes external official-document/web verification mandatory for anomaly resolution.
- [ ] Define TCBS/canonical-data-only validation pipeline.
- [ ] Define anomaly classification semantics and normalization handling.
- [ ] Define DGC expected behavior.
- [ ] Define UI semantics: red warning only for unresolved material/incoherent data, not every large change.
- [ ] Document expected gate categories and current snapshot.
- [ ] Clearly distinguish `DATA_STATUS`, `MODEL_STATUS`, `VALUATION_STATUS`, and investment verdict.
- [ ] State that public IV/MOS must only come from the canonical valuation report, not a duplicate screener valuation path.

## Constraints and Invariants

- Never fabricate the cause of a financial jump when TCBS/canonical data does not contain event evidence.
- `DATA_ANOMALY` from a threshold detector is not synonymous with bad data.
- Valid cycle peaks/troughs remain in full-cycle normalization.
- Structural regime breaks split comparable history rather than being blindly excluded.
- Unresolved material incoherence may downgrade confidence or block public IV/MOS.
- Model/data coverage gaps are not crashes and are not automatically bugs.
- Buy & Hold ledger invariants remain unchanged.

## Implementation Tasks

- [x] Read current `docs/user-test.md`.
- [x] Identify obsolete source-first assumptions.
- [ ] Replace with current TCBS-only numeric validation acceptance spec.
- [ ] Re-read updated document for contradictions.
- [ ] Mark task completed with validation evidence.

## Related Notes

- `docs/tasks/TASK-20260831-083-crawl-missing-financial-history.md`
- DGC numeric-validation/full-cycle regression case.

## Validation Evidence

Pending.

## Decisions

- DGC-style numeric validation is the default architecture for every symbol.
- External event-cause verification is optional enrichment, not a prerequisite for numeric validation.
- Specialized inputs unavailable in TCBS remain explicit model-coverage gaps.

## Result

Pending.
