# QPORT — BUFFETT CORE + THORP OVERLAY
## IMPLEMENTATION PLAN

version: 1.0
status: proposed
depends_on: SYSTEM_PLAN.md
target_repo: lap14tclc2/shannon_allocation

---

# 0. EXECUTION CONTRACT

This document defines HOW to implement the system described in `SYSTEM_PLAN.md`.

Rules:
1. Read relevant spec sections before mutation.
2. Create a Zettelkasten task before coding.
3. No silent scope expansion.
4. Any architecture deviation requires ADR.
5. No task can be `completed` without verification evidence.
6. Existing valuation and risk engines are canonical; reuse before adding new logic.
7. No numerical expected alpha or Kelly before Research + OOS gates pass.
8. Preserve DB-first production behavior and multi-portfolio isolation.
9. All public actions must be deterministic and explainable.
10. `HOLD` / `NO_ACTION_REQUIRED` are valid successful outputs.

Task state lifecycle:

`draft -> ready -> in-progress -> verified -> completed`

---

# 1. PROPOSED FILE / MODULE STRUCTURE

Backend:

```text
python/portfolio/
  allocation/
    __init__.py
    models.py
    eligibility.py
    opportunity.py
    candidate_service.py
    sizing.py
    service.py
    reason_codes.py

  research/
    __init__.py
    benchmark.py
    pit.py
    factors.py
    snapshots.py
    outcomes.py
    validation.py
    walk_forward.py

  risk.py                  # existing canonical risk engine
  screener.py              # existing candidate discovery
  value_engine/            # existing canonical valuation engine
```

API:

```text
app/main.py
```

Frontend:

```text
frontend/src/pages/AllocationPage.jsx
frontend/src/allocation-page.css
frontend/src/lib/api.js
frontend/src/lib/store.js
frontend/src/entry-vercel.jsx
frontend/src/components/AppNav.jsx
```

Tests:

```text
tests/
  unit/
    test_allocation_eligibility.py
    test_allocation_opportunity.py
    test_allocation_sizing.py
    test_allocation_reason_codes.py
    test_research_pit.py
    test_research_factors.py
    test_research_benchmark.py

  integration/
    test_allocation_service.py
    test_screener_to_allocation.py
    test_allocation_multi_portfolio.py
    test_research_snapshot_pipeline.py

  architecture/
    test_allocation_boundaries.py
```

---

# 2. DOMAIN CONTRACTS

## 2.1 EligibilityResult

```python
@dataclass(frozen=True)
class EligibilityResult:
    symbol: str
    status: Literal["INVESTABLE", "WATCHLIST", "INELIGIBLE"]
    hard_rejects: tuple[str, ...]
    quality_tier: str | None
    valuation_status: str | None
    valuation_confidence: str | None
    valuation_safety: float | None
    reason_codes: tuple[str, ...]
```

## 2.2 PortfolioFitResult

```python
@dataclass(frozen=True)
class PortfolioFitResult:
    symbol: str
    current_weight: float
    proposed_weight: float
    portfolio_vol_before: float | None
    portfolio_vol_after: float | None
    risk_contribution_before: float | None
    risk_contribution_after: float | None
    diversification_ratio_before: float | None
    diversification_ratio_after: float | None
    average_correlation_to_portfolio: float | None
    fit: Literal["GOOD", "MODERATE", "WEAK", "UNAVAILABLE"]
```

## 2.3 AllocationDecision

```python
@dataclass(frozen=True)
class AllocationDecision:
    symbol: str
    action: Literal[
        "BUY_MORE", "HOLD", "WATCH", "REDUCE", "SELL", "KEEP_CASH"
    ]
    current_weight: float
    target_min: float | None
    target_mid: float | None
    target_max: float | None
    confidence: Literal["HIGH", "MEDIUM", "LOW"]
    reason_codes: tuple[str, ...]
```

---

# 3. REASON CODE CONTRACT

Do not return opaque prose only.

Canonical reason-code examples:

```text
QUALITY_STRONG
QUALITY_DETERIORATING
HARD_REJECT
VALUATION_ATTRACTIVE
VALUATION_FAIR
VALUATION_EXPENSIVE
VALUATION_CONFIDENCE_LOW
VALUATION_SAFETY_POSITIVE
VALUATION_SAFETY_NEGATIVE
POSITION_CONCENTRATED
RISK_CONTRIBUTION_HIGH
CORRELATION_HIGH
DIVERSIFICATION_IMPROVES
DIVERSIFICATION_WORSENS
NO_SUPERIOR_REPLACEMENT
SUPERIOR_REPLACEMENT_AVAILABLE
LIQUIDITY_INSUFFICIENT
CASH_PREFERRED
TECHNICAL_CONFIRMATION
TECHNICAL_DETERIORATION
DATA_INSUFFICIENT
```

Frontend maps these to Vietnamese human explanations.

Business logic must not depend on localized strings.

---

# 4. MILESTONE DAG

```text
T00 Architecture contract
  |
  +--> T01 Allocation domain models
          |
          +--> T02 Buffett eligibility adapter
          |
          +--> T03 Candidate discovery adapter
          |
          +--> T04 Portfolio-fit simulation
                  |
                  +--> T05 Opportunity-cost engine
                          |
                          +--> T06 Allocation service/API
                                  |
                                  +--> T07 Allocation UI
                                  |
                                  +--> T08 Integration + architecture tests

T09 PIT metadata audit/migration
  |
  +--> T10 VNIndex benchmark
  |
  +--> T11 Factor snapshots
          |
          +--> T12 Forward outcomes
                  |
                  +--> T13 Validation / IC / walk-forward
                          |
                          +--> T14 Expected-alpha research
                                  |
                                  +--> T15 Optional adaptive sizing
```

No T14/T15 before T09–T13 are verified.

---

# 5. TASKS

## T00 — Architecture Contract

Goal:
Establish system docs, boundaries, and architecture tests.

Scope:
- `docs/`
- `tests/architecture/`

Acceptance:
- spec is committed;
- no duplicate risk engine;
- allocation module cannot import provider-specific infrastructure directly;
- expected-alpha/kelly are absent from V1.

Verify:
- architecture test;
- grep/import-boundary test.

---

## T01 — Allocation Domain Models

Goal:
Create deterministic internal contracts without business logic.

Scope:
- `python/portfolio/allocation/models.py`
- `reason_codes.py`

Acceptance:
- immutable result models;
- enums validated;
- serialization stable;
- reason codes centralized.

Verify:
- unit tests.

---

## T02 — Buffett Eligibility Adapter

Goal:
Translate existing value-engine outputs into clean portfolio eligibility without double-counting.

Inputs:
- intrinsic value;
- actual MOS;
- required MOS;
- quality tier;
- confidence;
- hard rejects.

Core derived field:

```python
valuation_safety = actual_mos_pct - required_mos_pct
```

Rules:
- any hard reject -> `INELIGIBLE`;
- low data confidence cannot become high-confidence BUY;
- quality and valuation are retained separately;
- no momentum override.

Acceptance:
- known value-engine fixtures map deterministically;
- LOW_QUALITY / hard rejects never become investable accidentally;
- no reuse of broad total score as pure Value factor.

Verify:
- unit tests covering banks, cyclicals, capital-intensive, missing-data cases.

---

## T03 — Screener Candidate Adapter

Goal:
Select 3–5 strongest research candidates from existing screener without declaring them BUY.

Flow:

```text
screener results
 -> liquidity filter
 -> eligibility adapter
 -> remove current holdings if desired
 -> candidate shortlist
```

Output:
`CandidateOpportunity[]`

Acceptance:
- max candidates configurable, default 5;
- no candidate with hard reject;
- no final action yet;
- missing data surfaced.

Verify:
- unit + integration tests.

---

## T04 — Portfolio-Fit Simulation

Goal:
Reuse current canonical `portfolio_risk()` to simulate adding/reducing positions.

Important:
Do NOT duplicate covariance, correlation, ERC, or VaR implementations.

For each proposed weight:
1. clone current portfolio rows;
2. apply hypothetical weight change;
3. call the canonical risk engine;
4. compare before/after.

Compare:
- volatility;
- risk contribution;
- diversification ratio;
- effective positions;
- correlation;
- concentration HHI.

Acceptance:
- no mutation to real portfolio;
- portfolio with high correlated exposure is penalized;
- missing-history case returns `UNAVAILABLE`, not fake zero risk.

Verify:
- deterministic fixtures;
- ACB/MBB high-correlation-style synthetic case;
- low-correlation candidate case.

---

## T05 — Opportunity-Cost Engine

Goal:
Decide whether capital should stay, move, or remain cash.

V1 must NOT use expected alpha.

Create transparent normalized components such as:

```text
business_quality_band
valuation_safety_band
portfolio_fit_band
technical_confirmation_band
```

Do not collapse into an unexplained magical score.

Decision hierarchy:

1. thesis broken / hard reject -> SELL or REDUCE
2. concentration risk breach -> REDUCE
3. attractive current holding + no superior replacement -> HOLD
4. investable candidate + cash available + portfolio fit good -> BUY_MORE / starter
5. candidate materially superior to weak holding -> ROTATION candidate
6. otherwise -> HOLD / KEEP_CASH

Use hysteresis:
- require meaningful margin before rotation;
- prevent small ranking changes from causing trades.

Acceptance:
- lower rank alone never forces sell;
- cash is valid;
- HOLD is common;
- action includes reason codes.

Verify:
- golden portfolio scenarios.

---

## T06 — Allocation Service + API

Proposed endpoints:

```text
GET /api/portfolio/allocation
POST /api/portfolio/allocation/simulate
```

`GET`:
- current holdings;
- portfolio verdict;
- holdings decisions;
- new opportunities;
- risk summary;
- no-action flag.

`POST /simulate`:
- hypothetical position changes;
- before/after risk impact;
- no persistence.

Preserve:
- `X-QPort-Portfolio-Id`;
- auth;
- multi-portfolio isolation;
- DB-first behavior.

No crawler/network fetch should be required in production request path if DB data exists.

Acceptance:
- portfolio scope respected;
- response stable;
- no transaction executed.

Verify:
- integration tests with two portfolio IDs.

---

## T07 — Allocation UI

Route:
`/allocation`

Navigation label:
`Phân bổ vốn`

Sections:
1. Portfolio Verdict
2. Current Holdings
3. New Opportunities
4. Proposed Rotation / No Action
5. Risk Before vs After
6. Evidence/Confidence
7. Create Transaction Draft

UX:
- concise;
- long-term;
- no trading-terminal feel;
- 3–5 opportunities max;
- `NO ACTION REQUIRED` must be visually prominent.

Actions:
- `Xem định giá` -> `/valuation`
- `Xem rủi ro` -> `/risk`
- `Xem screener` -> `/screener`
- `Create transaction draft` -> prefill existing transaction flow

No auto execution.

Verify:
- frontend build;
- mobile responsive;
- hide-values support;
- empty/missing-data state.

---

## T08 — V1 Audit Gate

Required tests:
- domain unit tests;
- API integration;
- multi-portfolio isolation;
- no duplicate risk math;
- hard-reject precedence;
- no fake expected alpha;
- no Kelly;
- no auto trade;
- frontend build.

Final status:
`PASS | PASS_WITH_NOTES | PARTIAL | BLOCKED | FAIL`

Only PASS/PASS_WITH_NOTES can merge.

---

# 6. PIT RESEARCH FOUNDATION

## T09 — Fundamental Availability Metadata

Audit current finance schema first.

Do not duplicate tables blindly.

Required canonical fields:

```text
period_end
published_at
known_at
received_at
available_from
availability_source
availability_confidence
```

Preferred:
`available_from = verified published_at`

Fallback:
documented conservative lag.

Critical query:

```sql
WHERE available_from <= :as_of_date
```

Acceptance:
- a report cannot appear in a snapshot before available_from;
- tests cover quarter/annual examples;
- restatements versioned correctly.

---

## T10 — VNIndex Benchmark

Create canonical benchmark service:

```python
benchmark.history("VNINDEX", start, end)
```

Verify provider semantics empirically before production.

Persist benchmark prices in existing market/research storage where appropriate.

Research outputs:
- benchmark return;
- stock excess return;
- relative strength;
- future excess-return labels.

Acceptance:
- aligned trading dates;
- missing-day policy explicit;
- corporate-action policy irrelevant to index but documented.

---

## T11 — Factor Snapshots

Persist historical feature snapshots rather than recomputing ad hoc.

Schema concept:

```text
snapshot_date
symbol
value_factor
quality_factor
momentum_3m
momentum_6m
momentum_12m
reversal_1m
liquidity
universe_membership
data_hash
```

Value and Quality must use only PIT-safe facts.

Acceptance:
- rerun produces identical values for same source hash;
- snapshot records provenance.

---

## T12 — Forward Outcomes

For horizon H:

```text
forward_stock_return_H
forward_vnindex_return_H
forward_excess_return_H
```

Recommended research horizons:
- 1M;
- 3M;
- 6M;
- 12M.

No same-period leakage.

Acceptance:
- date alignment;
- end-of-series missing outcomes remain missing;
- delisted/security-unavailable behavior documented.

---

## T13 — Factor Validation

For each factor:
- Rank IC;
- IC mean/std;
- positive IC ratio;
- quantile returns;
- top-minus-bottom spread;
- turnover;
- after-cost spread;
- regime breakdown.

Walk-forward only.

Example:

```text
train: rolling 5Y
test: next 1Y
```

Also keep a final sealed OOS period.

No parameter tuning using sealed OOS.

Acceptance:
- report generated from stored snapshots/outcomes;
- factor can be marked:
  `VALIDATED | WEAK | UNSTABLE | REJECTED`.

---

# 7. EXPECTED ALPHA — LOCKED UNTIL T13

## T14 — Calibration

Only execute if at least one factor family is validated.

Target:

```text
E[future_excess_return | factor state]
```

Do not infer expected alpha from MOS directly.

Calibration should prefer:
- bucket/quantile mapping;
- regularized simple models;
- interpretable uncertainty.

Avoid complex ML initially.

Required output:
- point estimate;
- confidence interval or uncertainty band;
- calibration sample size;
- OOS status.

If unreliable:
`expected_alpha = null`

---

# 8. OPTIONAL ADAPTIVE SIZING

## T15 — Fractional Kelly Research

Locked by default.

Prerequisites:
- validated expected alpha;
- reliable variance/covariance;
- OOS calibration;
- stable costs.

Research only:
- 0.10 Kelly;
- 0.25 Kelly;
- compare vs fixed bands.

Hard caps remain active.

Never default to full Kelly.

---

# 9. GOLDEN TEST SCENARIOS

Minimum scenarios:

1. Excellent business, attractive valuation, low portfolio correlation -> BUY_MORE
2. Excellent business, fair valuation, already high risk contribution -> HOLD
3. Weak business, huge MOS -> INELIGIBLE / WATCH, not BUY
4. High momentum + accounting hard reject -> INELIGIBLE
5. Weak holding + strong uncorrelated candidate + meaningful advantage -> REDUCE/ROTATE
6. Weak holding + no superior candidate -> HOLD or REDUCE_TO_CASH
7. Correlated bank candidate added to bank-heavy portfolio -> WATCH / capped weight
8. No eligible candidate -> KEEP_CASH
9. Missing risk history -> no fake portfolio-fit claim
10. Multi-portfolio A/B return different results with strict isolation
11. PIT historical test: Q2 report unavailable before publication
12. Sealed OOS cannot be touched by calibration

---

# 10. OBSERVABILITY

Allocation evaluation log:

```text
portfolio_id
evaluation_id
as_of
holdings_count
candidate_count
data_quality
risk_status
valuation_status
action_counts
no_action_required
reason_codes
```

Do not log secrets.

Research:
- snapshot count;
- PIT exclusions;
- stale facts;
- benchmark coverage;
- factor coverage;
- IC;
- turnover;
- OOS result.

---

# 11. PERFORMANCE / CACHE

Allocation page should not crawl external providers on every open.

Preferred:

```text
DB snapshots
 -> Redux/local cache
 -> API refresh when stale/user requests refresh
```

Cache invalidation:
- holdings changed;
- new transaction;
- new price snapshot;
- new valuation snapshot;
- new financial baseline;
- portfolio risk snapshot materially changed.

---

# 12. MIGRATION STRATEGY

Do not rewrite existing pages.

Migration sequence:

1. add allocation backend in isolation;
2. expose read-only API;
3. add `/allocation`;
4. verify against existing `/valuation`, `/risk`, `/screener`;
5. add transaction-draft integration;
6. only then simplify homepage/nav if desired.

Rollback:
- disable `/allocation` route;
- existing pages remain functional.

---

# 13. REQUIRED ADRs

Create ADR if any of these choices change:

- new research schema vs reuse `qport_finance`;
- allocation weight defaults;
- sector taxonomy;
- published_at fallback lag policy;
- benchmark provider;
- transaction-cost model;
- expected-alpha calibration model;
- Kelly activation.

---

# 14. DEFINITION OF DONE — V1

V1 is DONE only if:

- `/allocation` works for current portfolio;
- screener supplies new candidates;
- existing valuation engine is reused;
- existing risk engine is reused;
- portfolio-fit simulation is deterministic;
- multi-portfolio isolation verified;
- missing data degrades safely;
- HOLD/CASH behavior tested;
- no fake expected alpha;
- no Kelly;
- no auto-trade;
- backend tests pass;
- frontend build passes;
- architecture audit PASS.

---

# 15. DEFINITION OF DONE — RESEARCH READY

Research-ready only if:

- VNIndex benchmark verified;
- PIT fundamentals implemented;
- historical factor snapshots reproducible;
- forward outcomes stored;
- IC/quantile validation exists;
- walk-forward exists;
- sealed OOS exists;
- cost-adjusted results reported.

Only after this state may QPort claim a factor has historical edge.

---

# 16. FINAL IMPLEMENTATION RULE

The desired end state is not “more recommendations”.

The desired end state is:

> Fewer, higher-confidence portfolio changes with explicit evidence,
> while preserving good businesses and allowing compounding to work.

If the system cannot prove that moving capital is materially better than doing nothing,
the correct action is:

`HOLD / KEEP_CASH`.
